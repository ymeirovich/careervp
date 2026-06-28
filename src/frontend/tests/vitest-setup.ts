// matchMedia is not implemented in jsdom — provide a default stub so components
// that use window.matchMedia don't throw. Individual tests can override via vi.stubGlobal.
if (typeof window !== 'undefined' && typeof window.matchMedia === 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

// Provide required env vars so api/client.ts initialises without throwing
process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID = 'us-east-1_testpool';
process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID = 'testclientid';
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:3000';

if (
  typeof localStorage === 'undefined'
  || typeof localStorage.clear !== 'function'
  || typeof localStorage.getItem !== 'function'
  || typeof localStorage.setItem !== 'function'
) {
  const values = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(values.keys())[index] ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };

  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
  });
}
