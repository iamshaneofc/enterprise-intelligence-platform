/**
 * Centralized API Client with JWT authorization, error normalization, and 401 interceptors.
 *
 * SECURITY NOTE: JWT access tokens are currently stored in localStorage. This exposes tokens
 * to XSS attacks if any JavaScript injection vulnerability exists in the frontend.
 *
 * MIGRATION PATH (requires backend changes, separate phase):
 * 1. Backend must set HttpOnly, Secure, SameSite=Strict cookies on login/register
 * 2. Backend must clear cookies on logout
 * 3. Backend must implement CSRF token validation for state-changing requests
 * 4. Frontend must remove localStorage token storage and rely on cookie-based auth
 * 5. Frontend must attach CSRF token to non-GET requests
 * 6. CORS must be configured with allowCredentials=true and explicit origins (see backend fix)
 *
 * Do NOT change token storage to cookies without completing all backend steps above,
 * or authentication will break.
 */

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!rawBaseUrl && !import.meta.env.DEV) {
  console.warn(
    "VITE_API_BASE_URL is not set. Defaulting to relative origin. In production (e.g. Vercel), set VITE_API_BASE_URL to your backend API URL."
  );
}

const API_BASE_URL = (rawBaseUrl || "").replace(/\/+$/, "");

export class APIError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.data = data;
  }
}

let onUnauthorizedCallback: (() => void) | null = null;

export const setOnUnauthorized = (callback: () => void) => {
  onUnauthorizedCallback = callback;
};

export const getAuthToken = (): string | null => {
  try {
    return localStorage.getItem("eip_access_token");
  } catch {
    return null;
  }
};

export const setAuthToken = (token: string): void => {
  try {
    localStorage.setItem("eip_access_token", token);
  } catch (err) {
    console.error("Failed to persist auth token:", err);
  }
};

export const removeAuthToken = (): void => {
  try {
    localStorage.removeItem("eip_access_token");
  } catch (err) {
    console.error("Failed to remove auth token:", err);
  }
};

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // If body is NOT FormData, set JSON content-type
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;

  if (options.params) {
    const query = new URLSearchParams();
    Object.entries(options.params).forEach(([key, val]) => {
      if (val !== undefined) query.append(key, String(val));
    });
    const queryString = query.toString();
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString;
    }
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      removeAuthToken();
      if (onUnauthorizedCallback) {
        onUnauthorizedCallback();
      }
      throw new APIError("Authentication expired. Please log in again.", 401);
    }

    if (response.status === 204) {
      return {} as T;
    }

    const contentType = response.headers.get("content-type");
    const isJson = contentType && contentType.includes("application/json");
    const responseData = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const errorMsg =
        responseData?.detail ||
        responseData?.message ||
        `Request failed with status ${response.status}`;
      throw new APIError(errorMsg, response.status, responseData);
    }

    return responseData as T;
  } catch (error: any) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(
      error?.message || "Network request failed. Is the backend server running?",
      0,
      error
    );
  }
}

