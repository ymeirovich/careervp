import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { useAuth } from "../../contexts/AuthContext";

vi.mock("amazon-cognito-identity-js", () => {
  const mockSession = {
    isValid: vi.fn().mockReturnValue(true),
    getIdToken: vi.fn().mockReturnValue({
      getJwtToken: vi.fn().mockReturnValue("mock-id-token"),
    }),
  };

  const mockUser = {
    signOut: vi.fn(),
    getSession: vi.fn((cb: Function) => cb(null, mockSession)),
    changePassword: vi.fn((old: string, next: string, cb: Function) => cb(null, "SUCCESS")),
    resendConfirmationCode: vi.fn((cb: Function) => cb(null, {})),
  };

  return {
    CognitoUserPool: vi.fn().mockImplementation(() => ({
      getCurrentUser: vi.fn().mockReturnValue(mockUser),
      signUp: vi.fn((email: string, password: string, attrs: any[], _, cb: Function) =>
        cb(null, { user: mockUser })
      ),
    })),
    CognitoUser: vi.fn().mockImplementation(() => mockUser),
    AuthenticationDetails: vi.fn(),
    CognitoUserAttribute: vi.fn(),
  };
});

describe("AuthContext — signIn", () => {
  it("sets user and idToken on successful sign-in", async () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }: { children: React.ReactNode }) =>
        React.createElement(require("../../contexts/AuthContext").AuthProvider, null, children),
    });

    await act(async () => {
      await result.current.signIn("user@example.com", "Password1!");
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.idToken).toBe("mock-id-token");
  });

  it("sets error state on NotAuthorizedException", async () => {
    vi.mocked(require("amazon-cognito-identity-js").CognitoUser).mockImplementationOnce(
      () => ({
        authenticateUser: vi.fn((_, handlers: any) =>
          handlers.onFailure({ code: "NotAuthorizedException", message: "Incorrect username or password." })
        ),
      })
    );

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }: { children: React.ReactNode }) =>
        React.createElement(require("../../contexts/AuthContext").AuthProvider, null, children),
    });

    await expect(
      act(async () => result.current.signIn("user@example.com", "wrongpassword"))
    ).rejects.toThrow();

    expect(result.current.isAuthenticated).toBe(false);
  });
});

describe("AuthContext — signOut", () => {
  it("clears user and idToken after sign-out", async () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }: { children: React.ReactNode }) =>
        React.createElement(require("../../contexts/AuthContext").AuthProvider, null, children),
    });

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
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }: { children: React.ReactNode }) =>
        React.createElement(require("../../contexts/AuthContext").AuthProvider, null, children),
    });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.idToken).toBe("mock-id-token");
  });
});

describe("AuthContext — 401 handling", () => {
  it("attempts token refresh on 401 and returns fresh token", async () => {
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }: { children: React.ReactNode }) =>
        React.createElement(require("../../contexts/AuthContext").AuthProvider, null, children),
    });

    const freshToken = await result.current.refreshSession();
    expect(typeof freshToken).toBe("string");
    expect(freshToken.length).toBeGreaterThan(0);
  });
});
