import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { useAuth, AuthProvider } from "../../contexts/AuthContext";
import { CognitoUser } from "amazon-cognito-identity-js";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));

vi.mock("amazon-cognito-identity-js", () => {
  const mockSession = {
    isValid: vi.fn().mockReturnValue(true),
    getIdToken: vi.fn().mockReturnValue({
      getJwtToken: vi.fn().mockReturnValue("mock-id-token"),
    }),
  };

  const mockUser = {
    signOut: vi.fn(),
    getSession: vi.fn(function(cb: Function) { cb(null, mockSession); }),
    authenticateUser: vi.fn(function(_authDetails: unknown, handlers: { onSuccess: Function; onFailure: Function }) {
      handlers.onSuccess(mockSession);
    }),
    changePassword: vi.fn(function(_old: string, _next: string, cb: Function) { cb(null, "SUCCESS"); }),
    resendConfirmationCode: vi.fn(function(cb: Function) { cb(null, {}); }),
  };

  return {
    CognitoUserPool: vi.fn().mockImplementation(function() {
      return {
        getCurrentUser: vi.fn().mockReturnValue(mockUser),
        signUp: vi.fn(function(_email: string, _password: string, _attrs: unknown[], _: unknown, cb: Function) {
          cb(null, { user: mockUser });
        }),
      };
    }),
    CognitoUser: vi.fn().mockImplementation(function() {
      return mockUser;
    }),
    AuthenticationDetails: vi.fn().mockImplementation(function() { return {}; }),
    CognitoUserAttribute: vi.fn().mockImplementation(function() { return {}; }),
  };
});

const wrapper = ({ children }: { children: React.ReactNode }) =>
  React.createElement(AuthProvider, null, children);

describe("AuthContext — signIn", () => {
  it("sets user and idToken on successful sign-in", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signIn("user@example.com", "Password1!");
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.idToken).toBe("mock-id-token");
  });

  it("sets error state on NotAuthorizedException", async () => {
    vi.mocked(CognitoUser).mockImplementationOnce(function() {
      return {
        authenticateUser: vi.fn(function(_: unknown, handlers: { onSuccess: Function; onFailure: Function }) {
          handlers.onFailure({ code: "NotAuthorizedException", message: "Incorrect username or password." });
        }),
      } as unknown as CognitoUser;
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await expect(
      act(async () => result.current.signIn("user@example.com", "wrongpassword"))
    ).rejects.toThrow();

    expect(result.current.isAuthenticated).toBe(false);
  });
});

describe("AuthContext — signOut", () => {
  it("clears user and idToken after sign-out", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signIn("user@example.com", "Password1!");
    });

    expect(result.current.isAuthenticated).toBe(true);

    await act(async () => {
      await result.current.signOut();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.idToken).toBeNull();
  });
});

describe("AuthContext — session hydration on mount", () => {
  it("hydrates from existing Cognito session on mount", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.idToken).toBe("mock-id-token");
  });
});

describe("AuthContext — 401 handling", () => {
  it("attempts token refresh on 401 and returns fresh token", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    const freshToken = await result.current.refreshSession();
    expect(typeof freshToken).toBe("string");
    expect(freshToken.length).toBeGreaterThan(0);
  });
});
