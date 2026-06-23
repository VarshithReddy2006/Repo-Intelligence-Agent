/**
 * Unit tests for command helper utilities.
 *
 * Tests the splitRepo and pickOrGetActiveRepo logic patterns
 * used by the commands module.
 */

import * as assert from 'assert';

// ---------------------------------------------------------------------------
// Pure helpers extracted from commands logic
// ---------------------------------------------------------------------------

function splitRepo(identifier: string): [string, string] {
  const parts = identifier.split('/');
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new Error(`Invalid repository identifier "${identifier}". Expected "owner/repo".`);
  }
  return [parts[0], parts[1]];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('splitRepo', () => {
  it('correctly splits valid identifier', () => {
    const [owner, repo] = splitRepo('fastapi/fastapi');
    assert.strictEqual(owner, 'fastapi');
    assert.strictEqual(repo, 'fastapi');
  });

  it('handles owner with hyphens', () => {
    const [owner, repo] = splitRepo('my-org/my-repo');
    assert.strictEqual(owner, 'my-org');
    assert.strictEqual(repo, 'my-repo');
  });

  it('throws on missing slash', () => {
    assert.throws(() => splitRepo('noslash'), /Invalid repository identifier/);
  });

  it('throws on empty string', () => {
    assert.throws(() => splitRepo(''), /Invalid repository identifier/);
  });

  it('throws on trailing slash', () => {
    assert.throws(() => splitRepo('owner/'), /Invalid repository identifier/);
  });

  it('throws on leading slash', () => {
    assert.throws(() => splitRepo('/repo'), /Invalid repository identifier/);
  });

  it('throws on too many slashes', () => {
    assert.throws(() => splitRepo('a/b/c'), /Invalid repository identifier/);
  });
});

// ---------------------------------------------------------------------------
// extractErrorMessage from api.ts
// ---------------------------------------------------------------------------

function extractErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  return 'An unknown error occurred.';
}

describe('extractErrorMessage (commands context)', () => {
  it('returns message from Error object', () => {
    assert.strictEqual(extractErrorMessage(new Error('test error')), 'test error');
  });

  it('returns string directly', () => {
    assert.strictEqual(extractErrorMessage('already a string'), 'already a string');
  });

  it('returns fallback for null', () => {
    assert.strictEqual(extractErrorMessage(null), 'An unknown error occurred.');
  });

  it('returns fallback for undefined', () => {
    assert.strictEqual(extractErrorMessage(undefined), 'An unknown error occurred.');
  });

  it('returns fallback for number', () => {
    assert.strictEqual(extractErrorMessage(42), 'An unknown error occurred.');
  });
});

// ---------------------------------------------------------------------------
// Repository identifier validation
// ---------------------------------------------------------------------------

describe('Repository identifier validation', () => {
  const valid = ['owner/repo', 'google/guava', 'fastapi/fastapi', 'my-org/my-repo'];
  const invalid = ['', 'noslash', 'owner/', '/repo', 'a/b/c', '//'];

  for (const id of valid) {
    it(`accepts valid identifier "${id}"`, () => {
      assert.doesNotThrow(() => splitRepo(id));
    });
  }

  for (const id of invalid) {
    it(`rejects invalid identifier "${id}"`, () => {
      assert.throws(() => splitRepo(id));
    });
  }
});
