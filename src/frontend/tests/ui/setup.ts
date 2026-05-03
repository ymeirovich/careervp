/**
 * Test setup for Canvas App.jsx UI tests.
 *
 * This file must run BEFORE any test imports App.jsx because the Canvas app
 * initializes Firebase at module load time using global variables.
 *
 * Loaded via vitest.config.ts setupFiles for the tests/ui/** glob.
 */

import { vi } from 'vitest';
import '@testing-library/jest-dom';

declare global {
  var __firebase_config: string;
  var __app_id: string;
  var __initial_auth_token: string | undefined;
}

// ---------------------------------------------------------------------------
// Firebase globals — must be set before App.jsx module is imported
// ---------------------------------------------------------------------------
globalThis.__firebase_config = JSON.stringify({
  apiKey: 'test-api-key',
  authDomain: 'test-project.firebaseapp.com',
  projectId: 'test-project',
  storageBucket: 'test-project.appspot.com',
  messagingSenderId: '123456789',
  appId: '1:123456789:web:abcdef',
});

globalThis.__app_id = 'test-app-id';
globalThis.__initial_auth_token = undefined;

// ---------------------------------------------------------------------------
// Firebase module mocks
// ---------------------------------------------------------------------------
vi.mock('firebase/app', () => ({
  initializeApp: vi.fn(() => ({ name: '[DEFAULT]' })),
  getApp: vi.fn(() => ({ name: '[DEFAULT]' })),
  getApps: vi.fn(() => []),
}));

vi.mock('firebase/auth', () => ({
  getAuth: vi.fn(() => ({})),
  signInWithCustomToken: vi.fn(() => Promise.resolve({ user: mockUser() })),
  signInAnonymously: vi.fn(() => Promise.resolve({ user: mockUser() })),
  onAuthStateChanged: vi.fn((auth, callback) => {
    callback(mockUser());
    return vi.fn(); // unsubscribe
  }),
  signOut: vi.fn(() => Promise.resolve()),
}));

vi.mock('firebase/firestore', () => ({
  getFirestore: vi.fn(() => ({})),
  collection: vi.fn(),
  doc: vi.fn(),
  addDoc: vi.fn(() => Promise.resolve({ id: 'mock-doc-id' })),
  setDoc: vi.fn(() => Promise.resolve()),
  updateDoc: vi.fn(() => Promise.resolve()),
  deleteDoc: vi.fn(() => Promise.resolve()),
  getDoc: vi.fn(() => Promise.resolve({ exists: () => true, data: () => ({}) })),
  getDocs: vi.fn(() => Promise.resolve({ docs: [], forEach: vi.fn() })),
  onSnapshot: vi.fn((_ref, callback) => {
    callback({ docs: [], forEach: vi.fn() });
    return vi.fn(); // unsubscribe
  }),
  query: vi.fn((...args) => args[0]),
  where: vi.fn(),
  orderBy: vi.fn(),
  limit: vi.fn(),
  serverTimestamp: vi.fn(() => new Date().toISOString()),
  Timestamp: {
    now: vi.fn(() => ({ toDate: () => new Date() })),
    fromDate: vi.fn((date: Date) => ({ toDate: () => date })),
  },
}));

// ---------------------------------------------------------------------------
// Navigator clipboard mock
// ---------------------------------------------------------------------------
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: vi.fn(() => Promise.resolve()),
    readText: vi.fn(() => Promise.resolve('')),
  },
  writable: true,
  configurable: true,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function mockUser() {
  return {
    uid: 'test-user-uid',
    email: 'test@example.com',
    displayName: 'Test User',
    isAnonymous: false,
  };
}

export { mockUser };
