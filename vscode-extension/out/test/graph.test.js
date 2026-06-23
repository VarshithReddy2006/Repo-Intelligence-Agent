"use strict";
/**
 * Unit tests for graph rendering utilities.
 *
 * Tests the node layout, hit-testing math, and zoom/pan coordinate
 * transformations that are used inside the graph webviews.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const assert = __importStar(require("assert"));
function layoutNodes(rawNodes) {
    const cols = Math.ceil(Math.sqrt(rawNodes.length));
    return rawNodes.map((n, i) => {
        if (n.position && typeof n.position.x === 'number') {
            return { ...n, x: n.position.x, y: n.position.y };
        }
        const col = i % cols;
        const row = Math.floor(i / cols);
        return { ...n, x: 80 + col * 150, y: 60 + row * 100 };
    });
}
// ---------------------------------------------------------------------------
// Pan/zoom coordinate transforms
// ---------------------------------------------------------------------------
function screenToWorld(sx, sy, canvasLeft, canvasTop, offsetX, offsetY, scale) {
    return [(sx - canvasLeft - offsetX) / scale, (sy - canvasTop - offsetY) / scale];
}
// ---------------------------------------------------------------------------
// Hit-test (circle intersection)
// ---------------------------------------------------------------------------
function hitTest(nodes, wx, wy, nodeRadius = 18) {
    for (let i = nodes.length - 1; i >= 0; i--) {
        const n = nodes[i];
        const dx = wx - n.x;
        const dy = wy - n.y;
        if (dx * dx + dy * dy <= nodeRadius * nodeRadius * 1.5) {
            return n;
        }
    }
    return null;
}
// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('layoutNodes', () => {
    it('returns same count of nodes', () => {
        const raw = [
            { id: 'a', data: { label: 'a' } },
            { id: 'b', data: { label: 'b' } },
            { id: 'c', data: { label: 'c' } },
        ];
        const laid = layoutNodes(raw);
        assert.strictEqual(laid.length, 3);
    });
    it('uses provided position when available', () => {
        const raw = [
            { id: 'a', position: { x: 200, y: 300 } },
        ];
        const laid = layoutNodes(raw);
        assert.strictEqual(laid[0].x, 200);
        assert.strictEqual(laid[0].y, 300);
    });
    it('falls back to grid layout when no position provided', () => {
        const raw = [
            { id: 'a' },
            { id: 'b' },
            { id: 'c' },
            { id: 'd' },
        ];
        const laid = layoutNodes(raw);
        // All nodes should have numeric coordinates
        for (const n of laid) {
            assert.ok(typeof n.x === 'number');
            assert.ok(typeof n.y === 'number');
            assert.ok(n.x >= 0);
            assert.ok(n.y >= 0);
        }
    });
    it('handles empty input', () => {
        assert.deepStrictEqual(layoutNodes([]), []);
    });
    it('handles single node without position', () => {
        const laid = layoutNodes([{ id: 'solo' }]);
        assert.strictEqual(laid.length, 1);
        assert.ok(typeof laid[0].x === 'number');
    });
    it('arranges nodes in a grid pattern', () => {
        const raw = Array.from({ length: 9 }, (_, i) => ({ id: String(i) }));
        const laid = layoutNodes(raw);
        // 9 nodes → 3x3 grid, node at index 0 should be at col=0,row=0
        assert.strictEqual(laid[0].x, 80);
        assert.strictEqual(laid[0].y, 60);
        // node at index 3 → col=0, row=1
        assert.strictEqual(laid[3].y, 160);
    });
});
describe('screenToWorld', () => {
    it('converts screen coords to world coords at default scale', () => {
        const [wx, wy] = screenToWorld(100, 200, 0, 0, 0, 0, 1);
        assert.strictEqual(wx, 100);
        assert.strictEqual(wy, 200);
    });
    it('accounts for canvas offset', () => {
        const [wx, wy] = screenToWorld(150, 250, 50, 50, 0, 0, 1);
        assert.strictEqual(wx, 100);
        assert.strictEqual(wy, 200);
    });
    it('accounts for pan offset', () => {
        const [wx, wy] = screenToWorld(100, 100, 0, 0, -50, -50, 1);
        assert.strictEqual(wx, 150);
        assert.strictEqual(wy, 150);
    });
    it('accounts for zoom scale', () => {
        const [wx, wy] = screenToWorld(200, 200, 0, 0, 0, 0, 2);
        assert.strictEqual(wx, 100);
        assert.strictEqual(wy, 100);
    });
    it('zoom < 1 spreads world coords', () => {
        const [wx, wy] = screenToWorld(100, 100, 0, 0, 0, 0, 0.5);
        assert.strictEqual(wx, 200);
        assert.strictEqual(wy, 200);
    });
});
describe('hitTest', () => {
    const nodes = [
        { id: 'a', x: 100, y: 100 },
        { id: 'b', x: 300, y: 200 },
    ];
    it('returns node when click is inside its circle', () => {
        const hit = hitTest(nodes, 100, 100); // exactly on center
        assert.ok(hit !== null);
        assert.strictEqual(hit?.id, 'a');
    });
    it('returns node when click is within radius', () => {
        const hit = hitTest(nodes, 110, 110); // near center of 'a'
        assert.ok(hit !== null);
    });
    it('returns null when click misses all nodes', () => {
        const hit = hitTest(nodes, 500, 500);
        assert.strictEqual(hit, null);
    });
    it('returns last node in array when overlapping (z-order)', () => {
        const overlapping = [
            { id: 'first', x: 100, y: 100 },
            { id: 'second', x: 100, y: 100 }, // same position
        ];
        const hit = hitTest(overlapping, 100, 100);
        // Should return 'second' because we iterate in reverse
        assert.strictEqual(hit?.id, 'second');
    });
    it('handles empty node array', () => {
        assert.strictEqual(hitTest([], 100, 100), null);
    });
});
//# sourceMappingURL=graph.test.js.map