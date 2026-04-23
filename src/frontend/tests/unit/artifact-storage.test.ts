import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  persistArtifact,
  getArtifact,
  clearArtifact,
  clearAllArtifacts,
} from '../../lib/artifactStorage';

beforeEach(() => {
  localStorage.clear();
});

describe('persistArtifact', () => {
  it('writes to localStorage under namespaced key', () => {
    persistArtifact('job1', 'vpr', 'task-abc');
    expect(localStorage.getItem('cvp:artifacts:job1:vpr')).toBe('task-abc');
  });

  it('does not throw when localStorage is unavailable', () => {
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('QuotaExceededError');
    });
    expect(() => persistArtifact('job1', 'vpr', 'task-abc')).not.toThrow();
    spy.mockRestore();
  });
});

describe('getArtifact', () => {
  it('returns taskId for existing key', () => {
    persistArtifact('job1', 'vpr', 'task-abc');
    expect(getArtifact('job1', 'vpr')).toBe('task-abc');
  });

  it('returns null for unknown key', () => {
    expect(getArtifact('job1', 'vpr')).toBeNull();
  });
});

describe('clearArtifact', () => {
  it('removes the key from localStorage', () => {
    persistArtifact('job1', 'vpr', 'task-abc');
    clearArtifact('job1', 'vpr');
    expect(getArtifact('job1', 'vpr')).toBeNull();
  });
});

describe('clearAllArtifacts', () => {
  it('removes all artifact keys for a given jobId', () => {
    persistArtifact('job1', 'vpr', 'task-1');
    persistArtifact('job1', 'coverLetter', 'task-2');
    persistArtifact('job2', 'vpr', 'task-3');

    clearAllArtifacts('job1');

    expect(getArtifact('job1', 'vpr')).toBeNull();
    expect(getArtifact('job1', 'coverLetter')).toBeNull();
    // job2 should be unaffected
    expect(getArtifact('job2', 'vpr')).toBe('task-3');
  });
});
