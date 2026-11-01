import { request, setAuthToken, removeAuthToken } from "./api";
import { User, AuthToken } from "@/types";

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  role?: "admin" | "engineer" | "viewer";
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authService = {
  async register(payload: RegisterPayload): Promise<User> {
    return request<User>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async login(payload: LoginPayload): Promise<AuthToken> {
    const token = await request<AuthToken>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setAuthToken(token.access_token);
    return token;
  },

  async getMe(): Promise<User> {
    return request<User>("/api/v1/auth/me", {
      method: "GET",
    });
  },

  logout(): void {
    removeAuthToken();
  },
};

