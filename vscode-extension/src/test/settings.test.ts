/**
 * Unit tests for settings/configuration defaults and validation.
 */

import * as assert from 'assert';

// ---------------------------------------------------------------------------
// Simulate the configuration schema validation logic
// ---------------------------------------------------------------------------

interface ExtensionConfig {
  backendUrl: string;
  apiToken: string;
  activeRepository: string;
  autoRefresh: boolean;
  requestTimeoutMs: number;
  graphLayout: 'dagre' | 'force' | 'radial';
  theme: 'auto' | 'dark' | 'light';
  'codeLens.enabled': boolean;
  'hover.enabled': boolean;
}

const DEFAULT_CONFIG: ExtensionConfig = {
  backendUrl: 'http://127.0.0.1:8001',
  apiToken: '',
  activeRepository: '',
  autoRefresh: false,
  requestTimeoutMs: 15000,
  graphLayout: 'dagre',
  theme: 'auto',
  'codeLens.enabled': true,
  'hover.enabled': true,
};

function normalizeBackendUrl(url: string): string {
  return url.replace(/\/$/, '');
}

function validateConfig(cfg: Partial<ExtensionConfig>): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];
  if (cfg.backendUrl !== undefined) {
    try {
      new URL(cfg.backendUrl);
    } catch {
      errors.push(`backendUrl "${cfg.backendUrl}" is not a valid URL`);
    }
  }
  if (cfg.requestTimeoutMs !== undefined) {
    if (cfg.requestTimeoutMs < 1000) {
      errors.push('requestTimeoutMs must be at least 1000ms');
    }
    if (cfg.requestTimeoutMs > 120000) {
      errors.push('requestTimeoutMs must be at most 120000ms (2 minutes)');
    }
  }
  if (cfg.graphLayout !== undefined) {
    if (!['dagre', 'force', 'radial'].includes(cfg.graphLayout)) {
      errors.push(`graphLayout "${cfg.graphLayout}" is not a valid layout`);
    }
  }
  if (cfg.theme !== undefined) {
    if (!['auto', 'dark', 'light'].includes(cfg.theme)) {
      errors.push(`theme "${cfg.theme}" is not a valid theme`);
    }
  }
  return { valid: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Default configuration', () => {
  it('has valid default backend URL', () => {
    const result = validateConfig({ backendUrl: DEFAULT_CONFIG.backendUrl });
    assert.ok(result.valid, result.errors.join(', '));
  });

  it('has valid default timeout', () => {
    const result = validateConfig({ requestTimeoutMs: DEFAULT_CONFIG.requestTimeoutMs });
    assert.ok(result.valid, result.errors.join(', '));
  });

  it('has valid default graph layout', () => {
    const result = validateConfig({ graphLayout: DEFAULT_CONFIG.graphLayout });
    assert.ok(result.valid, result.errors.join(', '));
  });

  it('has valid default theme', () => {
    const result = validateConfig({ theme: DEFAULT_CONFIG.theme });
    assert.ok(result.valid, result.errors.join(', '));
  });

  it('autoRefresh defaults to false', () => {
    assert.strictEqual(DEFAULT_CONFIG.autoRefresh, false);
  });

  it('codeLens.enabled defaults to true', () => {
    assert.strictEqual(DEFAULT_CONFIG['codeLens.enabled'], true);
  });

  it('hover.enabled defaults to true', () => {
    assert.strictEqual(DEFAULT_CONFIG['hover.enabled'], true);
  });
});

describe('normalizeBackendUrl', () => {
  it('removes trailing slash', () => {
    assert.strictEqual(normalizeBackendUrl('http://127.0.0.1:8001/'), 'http://127.0.0.1:8001');
  });

  it('leaves URL without trailing slash unchanged', () => {
    assert.strictEqual(normalizeBackendUrl('http://127.0.0.1:8001'), 'http://127.0.0.1:8001');
  });

  it('handles HTTPS URL', () => {
    assert.strictEqual(
      normalizeBackendUrl('https://api.example.com/'),
      'https://api.example.com'
    );
  });
});

describe('Configuration validation', () => {
  it('accepts valid HTTP URL', () => {
    const { valid } = validateConfig({ backendUrl: 'http://localhost:8001' });
    assert.ok(valid);
  });

  it('accepts valid HTTPS URL', () => {
    const { valid } = validateConfig({ backendUrl: 'https://api.example.com' });
    assert.ok(valid);
  });

  it('rejects invalid URL', () => {
    const { valid, errors } = validateConfig({ backendUrl: 'not-a-url' });
    assert.strictEqual(valid, false);
    assert.ok(errors.length > 0);
  });

  it('rejects timeout below 1000ms', () => {
    const { valid, errors } = validateConfig({ requestTimeoutMs: 500 });
    assert.strictEqual(valid, false);
    assert.ok(errors.some((e) => e.includes('1000ms')));
  });

  it('rejects timeout above 120000ms', () => {
    const { valid, errors } = validateConfig({ requestTimeoutMs: 999999 });
    assert.strictEqual(valid, false);
    assert.ok(errors.some((e) => e.includes('120000ms')));
  });

  it('rejects invalid graph layout', () => {
    const { valid, errors } = validateConfig({
      graphLayout: 'invalid' as 'dagre',
    });
    assert.strictEqual(valid, false);
    assert.ok(errors.some((e) => e.includes('graphLayout')));
  });

  it('rejects invalid theme', () => {
    const { valid, errors } = validateConfig({ theme: 'rainbow' as 'auto' });
    assert.strictEqual(valid, false);
    assert.ok(errors.some((e) => e.includes('theme')));
  });

  it('accepts all valid graph layouts', () => {
    for (const layout of ['dagre', 'force', 'radial'] as const) {
      const { valid } = validateConfig({ graphLayout: layout });
      assert.ok(valid, `Layout "${layout}" should be valid`);
    }
  });

  it('accepts all valid themes', () => {
    for (const theme of ['auto', 'dark', 'light'] as const) {
      const { valid } = validateConfig({ theme });
      assert.ok(valid, `Theme "${theme}" should be valid`);
    }
  });
});
