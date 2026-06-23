"""Breaking Change Analyzer.

Standalone, stateless class that diffs two APISurface snapshots and emits
typed BreakingChange records.

Design:
  - Pure function — no I/O, no service injection.
  - Compares by (file_path, qualified_name) identity.
  - Detects: removed exports, signature arity changes, visibility reduction.
  - Renamed symbols are detected as a best-effort heuristic: a symbol removed
    from one location AND added with the same name in a different location is
    flagged as RENAMED rather than REMOVED + ADDED.
  - No LLM. No guessing. If a change cannot be typed with confidence, it is
    omitted rather than mis-classified.

Reused by:
  APISurfaceService      — for build-time snapshot comparison
  PR Intelligence        — via APISurfaceService.diff() on PR changed files
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from models.api_surface import (
    APISurface,
    BreakingChange,
    BreakingChangeKind,
    ClassifiedSymbol,
    Visibility,
)


class BreakingChangeAnalyzer:
    """Diffs two APISurface snapshots and returns BreakingChange records."""

    @staticmethod
    def diff(
        before: APISurface,
        after: APISurface,
    ) -> List[BreakingChange]:
        """Compare before and after API surfaces and return breaking changes.

        Only PUBLIC symbols are considered for breaking change analysis —
        internal/private changes are not breaking by definition.

        Args:
            before: The baseline API surface (e.g. main branch).
            after:  The proposed API surface (e.g. PR branch or snapshot).

        Returns:
            Sorted list of BreakingChange records (high severity first).
        """
        # Build identity maps: (file_path, qualified) → ClassifiedSymbol
        before_map = BreakingChangeAnalyzer._public_map(before)
        after_map  = BreakingChangeAnalyzer._public_map(after)

        before_keys = set(before_map.keys())
        after_keys  = set(after_map.keys())

        removed_keys = before_keys - after_keys
        added_keys   = after_keys  - before_keys
        shared_keys  = before_keys & after_keys

        changes: List[BreakingChange] = []

        # ── 1. Detect renames (removed + added same name, different path) ─
        removed_by_name: Dict[str, List[Tuple]] = {}
        for key in removed_keys:
            sym = before_map[key]
            removed_by_name.setdefault(sym.name, []).append((key, sym))

        added_by_name: Dict[str, List[Tuple]] = {}
        for key in added_keys:
            sym = after_map[key]
            added_by_name.setdefault(sym.name, []).append((key, sym))

        rename_accounted_removed: set = set()
        rename_accounted_added: set = set()

        for name, removed_items in removed_by_name.items():
            if name in added_by_name:
                # Same name exists in after at a different location → likely rename
                for (r_key, r_sym) in removed_items:
                    for (a_key, a_sym) in added_by_name[name]:
                        if r_key != a_key:  # different (file, qualified)
                            changes.append(BreakingChange(
                                kind=BreakingChangeKind.RENAMED_EXPORT,
                                symbol_name=name,
                                file_path=r_sym.file_path,
                                severity="medium",
                                description=(
                                    f"Public symbol '{name}' was moved from "
                                    f"'{r_sym.file_path}' to '{a_sym.file_path}'. "
                                    "Consumers importing from the old path will break."
                                ),
                            ))
                            rename_accounted_removed.add(r_key)
                            rename_accounted_added.add(a_key)

        # ── 2. Removed exports (not accounted for by renames) ──────────
        for key in removed_keys - rename_accounted_removed:
            sym = before_map[key]
            changes.append(BreakingChange(
                kind=BreakingChangeKind.REMOVED_EXPORT,
                symbol_name=sym.name,
                file_path=sym.file_path,
                before_param_count=sym.param_count,
                severity="high",
                description=(
                    f"Public symbol '{sym.qualified}' in '{sym.file_path}' "
                    "was removed. Consumers of this API will break."
                ),
            ))

        # ── 3. Signature changes (param count delta) ───────────────────
        for key in shared_keys:
            b_sym = before_map[key]
            a_sym = after_map[key]

            if b_sym.param_count != a_sym.param_count and b_sym.param_count > 0:
                # Adding optional params is not breaking; removing params is.
                # We cannot determine optionality without type info, so any
                # delta in param count is flagged as potentially breaking.
                changes.append(BreakingChange(
                    kind=BreakingChangeKind.SIGNATURE_CHANGED,
                    symbol_name=b_sym.name,
                    file_path=b_sym.file_path,
                    before_param_count=b_sym.param_count,
                    after_param_count=a_sym.param_count,
                    severity="high",
                    description=(
                        f"Signature of public '{b_sym.qualified}' in "
                        f"'{b_sym.file_path}' changed: "
                        f"{b_sym.param_count} → {a_sym.param_count} parameters. "
                        "Existing call sites may be broken."
                    ),
                ))

        # ── 4. Visibility reduction ────────────────────────────────────
        # A symbol that was PUBLIC in before but is now INTERNAL or PRIVATE
        # Use all symbols, not just public_map
        before_all = {(s.file_path, s.qualified): s for s in before.symbols}
        after_all  = {(s.file_path, s.qualified): s for s in after.symbols}

        for key, b_sym in before_all.items():
            if b_sym.visibility != Visibility.PUBLIC:
                continue
            a_sym = after_all.get(key)
            if a_sym and a_sym.visibility in (Visibility.PRIVATE, Visibility.INTERNAL):
                changes.append(BreakingChange(
                    kind=BreakingChangeKind.VISIBILITY_REDUCED,
                    symbol_name=b_sym.name,
                    file_path=b_sym.file_path,
                    severity="high",
                    description=(
                        f"'{b_sym.qualified}' in '{b_sym.file_path}' was PUBLIC "
                        f"but is now {a_sym.visibility.value.upper()}. "
                        "External consumers will lose access."
                    ),
                ))

        # Sort: high severity first, then by symbol name
        severity_order = {"high": 0, "medium": 1, "low": 2}
        changes.sort(key=lambda c: (severity_order.get(c.severity, 9), c.symbol_name))

        return changes

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _public_map(
        surface: APISurface,
    ) -> Dict[Tuple[str, str], ClassifiedSymbol]:
        """Build a (file_path, qualified) → ClassifiedSymbol dict for PUBLIC symbols."""
        return {
            (s.file_path, s.qualified): s
            for s in surface.symbols
            if s.visibility == Visibility.PUBLIC
        }

    @staticmethod
    def diff_file_symbols(
        before_symbols: List[ClassifiedSymbol],
        after_symbols: List[ClassifiedSymbol],
    ) -> List[BreakingChange]:
        """Diff two lists of classified symbols for a single file.

        Convenience wrapper used by PR Intelligence to check per-file changes.
        """
        # Wrap in minimal APISurface containers
        before_surface = APISurface(repo="pr_before", generated_at="", symbols=before_symbols)
        after_surface  = APISurface(repo="pr_after",  generated_at="", symbols=after_symbols)
        return BreakingChangeAnalyzer.diff(before_surface, after_surface)
