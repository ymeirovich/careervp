import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { useAuth, AuthProvider } from "../../contexts/AuthContext";
import { beginPkceSignIn } from "../../lib/pkce";

vi.mock("../../lib/pkce", () => ({
  beginPkceSignIn: vi.fn().mockResolvedValue(undefined),
  hostedUiLogoutUrl: vi.fn().mockReturnValue(null),
}));

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
  it("starts authorization-code PKCE sign-in", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signIn("user@example.com");
    });

    expect(beginPkceSignIn).toHaveBeenCalledWith("user@example.com");
  });

  it("surfaces a failure to start the PKCE redirect", async () => {
    vi.mocked(beginPkceSignIn).mockRejectedValueOnce(new Error("redirect failed"));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await expect(
      act(async () => result.current.signIn("user@example.com"))
    ).rejects.toThrow("redirect failed");
  });
});

describe("AuthContext — signOut", () => {
  it("clears user and idToken after sign-out", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.signIn("user@example.com");
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
