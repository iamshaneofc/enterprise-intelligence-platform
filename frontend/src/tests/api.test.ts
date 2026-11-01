import { describe, it, expect, beforeEach } from "vitest";
import { getAuthToken, setAuthToken, removeAuthToken, APIError } from "../services/api";

// Simple in-memory localStorage polyfill for Node test environment
const mockStorage: Record<string, string> = {};
global.localStorage = {
  getItem: (key: string) => mockStorage[key] || null,
  setItem: (key: string, val: string) => { mockStorage[key] = String(val); },
  removeItem: (key: string) => { delete mockStorage[key]; },
  clear: () => { Object.keys(mockStorage).forEach((k) => delete mockStorage[k]); },
  key: (i: number) => Object.keys(mockStorage)[i] || null,
  length: 0,
};

describe("API Client & Token Management", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and retrieves the JWT token correctly", () => {
    expect(getAuthToken()).toBeNull();
    setAuthToken("test-jwt-token-12345");
    expect(getAuthToken()).toBe("test-jwt-token-12345");
  });

  it("removes the JWT token on logout", () => {
    setAuthToken("token-to-remove");
    removeAuthToken();
    expect(getAuthToken()).toBeNull();
  });

  it("creates structured APIError instances with HTTP status", () => {
    const err = new APIError("Entity not found", 404, { detail: "Document missing" });
    expect(err.message).toBe("Entity not found");
    expect(err.status).toBe(404);
    expect(err.data).toEqual({ detail: "Document missing" });
    expect(err.name).toBe("APIError");
  });
});
