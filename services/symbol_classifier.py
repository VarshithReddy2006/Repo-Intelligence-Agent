"""Symbol Classifier — stateless heuristic classification engine.

Converts a raw Symbol (from the Symbol Index) into a ClassifiedSymbol with:
  - Visibility    (PUBLIC | INTERNAL | PRIVATE | UNKNOWN)
  - ApiKind       (ROUTE | EXPORTED | CLI_ENTRY | PUBLIC_FUNCTION | ...)
  - ApiStatus     (STABLE | DEPRECATED | EXPERIMENTAL | UNKNOWN)
  - confidence    (0.0–1.0)
  - classification_reason (human-readable, mandatory for every classification)

Design:
  - Pure functions / static methods only — no I/O, no service dependencies.
  - All classification rules are explicit if/elif chains — no ML, no LLM.
  - Every rule states its confidence explicitly.
  - When no rule fires with confidence ≥ _MIN_CONFIDENCE, falls back to UNKNOWN.
  - Reuses TreeSitterService parse_file() output (which already extracts the
    'exports' list for JS/TS files) — never re-parses the AST.
  - Python __all__ is extracted via a lightweight regex on file content — no
    additional AST walk required.

Called by:
  APISurfaceService.build() — once per symbol during the classification pass.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from models.api_surface import ApiKind, ApiStatus, ClassifiedSymbol, Visibility
from models.symbol import Symbol

# Minimum confidence to accept a classification (below this → UNKNOWN).
_MIN_CONFIDENCE = 0.6

# ---------------------------------------------------------------------------
# Patterns compiled once at module load
# ---------------------------------------------------------------------------

# Python route decorators: @app.get, @app.post, @router.get, @bp.route, etc.
_PY_ROUTE_DECORATOR = re.compile(
    r"@\w+\.(get|post|put|patch|delete|head|options|route|websocket)\b",
    re.IGNORECASE,
)

# CLI decorators: @click.command, @app.command, @typer.command, @cli.command
_PY_CLI_DECORATOR = re.compile(
    r"@\w+\.(command|group)\b",
    re.IGNORECASE,
)

# Deprecation markers (docstring / comment / decorator)
_DEPRECATED_MARKERS = re.compile(
    r"@deprecated|#\s*deprecated|\.\.[\s\n]+deprecated::|"
    r"DeprecationWarning|FutureWarning|deprecated::\s*\d|"
    r"@Deprecated|@obsolete",
    re.IGNORECASE,
)

# Experimental markers
_EXPERIMENTAL_MARKERS = re.compile(
    r"@experimental|@beta|@alpha|#\s*experimental|"
    r"experimental::|beta feature|alpha feature",
    re.IGNORECASE,
)

# Python __all__ extraction
_PY_ALL_PATTERN = re.compile(
    r"__all__\s*=\s*\[([^\]]*)\]",
    re.DOTALL,
)

# Express route patterns: router.get(, app.post(, etc.
_EXPRESS_ROUTE = re.compile(
    r"\b(router|app|express)\s*\.\s*(get|post|put|patch|delete|use|all)\s*\(",
    re.IGNORECASE,
)

# Private name patterns by language
_PYTHON_PRIVATE_PREFIX = re.compile(r"^__[^_]")          # __name (dunder)
_PYTHON_INTERNAL_PREFIX = re.compile(r"^_[^_]")          # _name (single underscore)


class SymbolClassifier:
    """Stateless heuristic classifier for API surface symbols.

    All methods are static — instantiate for convenience, or call directly.
    """

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    @staticmethod
    def classify(
        symbol: Symbol,
        file_content: str,
        parsed_exports: Optional[List[str]] = None,  # from TreeSitterService output
        all_list: Optional[Set[str]] = None,          # Python __all__ set
        entry_point_files: Optional[Set[str]] = None,
        call_graph_fan_in: int = 0,
    ) -> ClassifiedSymbol:
        """Classify a single symbol and return a ClassifiedSymbol.

        Args:
            symbol:             The raw Symbol from the SymbolIndex.
            file_content:       Raw source text of the file containing the symbol.
            parsed_exports:     List of exported names from TreeSitterService
                                (JS/TS files only; None for Python).
            all_list:           Python __all__ set for this file (if extracted).
            entry_point_files:  Set of file paths that are architecture entry points.
            call_graph_fan_in:  Number of callers from the CallGraph (0 = unknown/unused).

        Returns:
            ClassifiedSymbol with full classification metadata.
        """
        name = symbol.name
        lang = symbol.language
        sym_type = symbol.type
        file_path = symbol.file_path
        parent_class = symbol.parent_class

        # Qualified name
        qualified = f"{parent_class}.{name}" if parent_class else name

        # Gather decorators from file content (lightweight scan)
        decorators = SymbolClassifier._extract_decorators_near_line(
            file_content, symbol.line_number
        )

        # Parameter count (best-effort from function signature in content)
        param_count = SymbolClassifier._estimate_param_count(
            file_content, symbol.line_number, lang
        )

        # Async detection
        is_async = SymbolClassifier._is_async(file_content, symbol.line_number)

        # ── Status classification (deprecation / experimental) ──────────
        status, status_reason = SymbolClassifier._classify_status(
            file_content, symbol.line_number, decorators
        )

        # ── Visibility + ApiKind classification ─────────────────────────
        visibility, api_kind, confidence, reason = SymbolClassifier._classify_visibility(
            symbol=symbol,
            name=name,
            lang=lang,
            sym_type=sym_type,
            file_path=file_path,
            parent_class=parent_class,
            decorators=decorators,
            parsed_exports=parsed_exports,
            all_list=all_list,
            entry_point_files=entry_point_files or set(),
            file_content=file_content,
        )

        # Merge status reason if present
        full_reason = reason
        if status_reason:
            full_reason = f"{reason}; {status_reason}"

        # Orphan detection: public but nobody calls it
        is_orphan = (visibility == Visibility.PUBLIC and call_graph_fan_in == 0
                     and sym_type in ("function", "method", "class"))

        return ClassifiedSymbol(
            name=name,
            qualified=qualified,
            symbol_type=sym_type,
            file_path=file_path,
            line_number=symbol.line_number,
            language=lang,
            parent_class=parent_class,
            visibility=visibility,
            api_kind=api_kind,
            status=status,
            confidence=confidence,
            classification_reason=full_reason,
            param_count=param_count,
            is_async=is_async,
            decorators=decorators,
            fan_in=call_graph_fan_in,
            is_orphan=is_orphan,
        )

    # ------------------------------------------------------------------
    # Visibility + ApiKind
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_visibility(
        symbol: Symbol,
        name: str,
        lang: str,
        sym_type: str,
        file_path: str,
        parent_class: Optional[str],
        decorators: List[str],
        parsed_exports: Optional[List[str]],
        all_list: Optional[Set[str]],
        entry_point_files: Set[str],
        file_content: str,
    ):
        """Return (Visibility, ApiKind, confidence, reason)."""

        # ── 1. Entry-point file ────────────────────────────────────────
        if file_path in entry_point_files:
            return (
                Visibility.PUBLIC,
                ApiKind.MAIN_ENTRY,
                0.95,
                f"Defined in architecture entry point '{file_path}'.",
            )

        # ── 2. Python __main__ / if __name__ == '__main__' ─────────────
        if lang == "python" and name in ("main", "__main__"):
            if "__name__" in file_content and "__main__" in file_content:
                return (
                    Visibility.PUBLIC,
                    ApiKind.MAIN_ENTRY,
                    0.90,
                    "Function defined in a __main__ guard block.",
                )

        # ── 3. HTTP route decorators (Python) ──────────────────────────
        if lang == "python":
            dec_text = " ".join(decorators)
            if _PY_ROUTE_DECORATOR.search(dec_text):
                return (
                    Visibility.PUBLIC,
                    ApiKind.ROUTE,
                    0.95,
                    f"HTTP route decorator detected: {dec_text.strip()[:80]}.",
                )

        # ── 4. Express/Next.js route pattern (JS/TS) ───────────────────
        if lang in ("javascript", "typescript", "tsx"):
            # Check 5 lines around the symbol definition for route patterns
            lines = file_content.splitlines()
            start = max(0, symbol.line_number - 3)
            end = min(len(lines), symbol.line_number + 2)
            snippet = "\n".join(lines[start:end])
            if _EXPRESS_ROUTE.search(snippet):
                return (
                    Visibility.PUBLIC,
                    ApiKind.ROUTE,
                    0.88,
                    "Express/Next.js route pattern detected near definition.",
                )

        # ── 5. CLI decorators (Python) ─────────────────────────────────
        if lang == "python":
            dec_text = " ".join(decorators)
            if _PY_CLI_DECORATOR.search(dec_text):
                return (
                    Visibility.PUBLIC,
                    ApiKind.CLI_ENTRY,
                    0.90,
                    f"CLI command decorator detected: {dec_text.strip()[:80]}.",
                )

        # ── 6. JS/TS explicit export ───────────────────────────────────
        if lang in ("javascript", "typescript", "tsx") and parsed_exports is not None:
            if name in parsed_exports:
                kind = (
                    ApiKind.PUBLIC_CLASS if sym_type == "class"
                    else ApiKind.INTERFACE if sym_type == "interface"
                    else ApiKind.ENUM_TYPE if sym_type == "enum"
                    else ApiKind.EXPORTED
                )
                return (
                    Visibility.PUBLIC,
                    kind,
                    0.95,
                    f"Symbol '{name}' found in file's export list.",
                )

        # ── 7. Python __all__ list ─────────────────────────────────────
        if lang == "python" and all_list is not None:
            if name in all_list:
                kind = ApiKind.PUBLIC_CLASS if sym_type == "class" else ApiKind.PUBLIC_FUNCTION
                return (
                    Visibility.PUBLIC,
                    kind,
                    0.95,
                    f"Symbol '{name}' is listed in __all__.",
                )

        # ── 8. Python private naming conventions ──────────────────────
        if lang == "python":
            if _PYTHON_PRIVATE_PREFIX.match(name):
                return (
                    Visibility.PRIVATE,
                    ApiKind.INTERNAL_HELPER,
                    0.90,
                    f"Name '{name}' uses dunder prefix — Python private by convention.",
                )
            if _PYTHON_INTERNAL_PREFIX.match(name):
                return (
                    Visibility.INTERNAL,
                    ApiKind.INTERNAL_HELPER,
                    0.88,
                    f"Name '{name}' uses single-underscore prefix — Python internal by convention.",
                )

        # ── 9. JS/TS: symbol in a file with no exports → internal ─────
        if lang in ("javascript", "typescript", "tsx"):
            if parsed_exports is not None and len(parsed_exports) == 0:
                return (
                    Visibility.INTERNAL,
                    ApiKind.INTERNAL_HELPER,
                    0.70,
                    "File has no exports; all symbols treated as internal.",
                )

        # ── 10. Directory heuristics ───────────────────────────────────
        norm = file_path.replace("\\", "/").lower()

        # Test / spec files → internal
        if any(d in norm for d in ("/test", "/tests", "/spec", "/specs",
                                    "__test__", ".test.", ".spec.")):
            return (
                Visibility.INTERNAL,
                ApiKind.INTERNAL_HELPER,
                0.85,
                "Defined in a test/spec file — treated as test helper.",
            )

        # Private directories
        if any(d in norm for d in ("/_internal/", "/internal/", "/private/",
                                    "/_private/", "/_helpers/", "/helpers/")):
            return (
                Visibility.PRIVATE,
                ApiKind.INTERNAL_HELPER,
                0.80,
                f"Defined in private/internal directory: {file_path}.",
            )

        # Public API directories
        if any(d in norm for d in ("/api/", "/routes/", "/endpoints/",
                                    "/controllers/", "/views/", "/handlers/")):
            kind = ApiKind.ROUTE if sym_type == "function" else ApiKind.PUBLIC_CLASS
            return (
                Visibility.PUBLIC,
                kind,
                0.75,
                f"Defined in API/routing directory: {file_path}.",
            )

        # ── 11. TypeScript interface / enum → public by default ────────
        if lang in ("typescript", "tsx") and sym_type in ("interface", "enum"):
            return (
                Visibility.PUBLIC,
                ApiKind.INTERFACE if sym_type == "interface" else ApiKind.ENUM_TYPE,
                0.70,
                "TypeScript interfaces and enums are public by default.",
            )

        # ── 12. Python class / function at module level → PUBLIC (inferred) ─
        if lang == "python" and sym_type in ("function", "class") and parent_class is None:
            kind = ApiKind.PUBLIC_CLASS if sym_type == "class" else ApiKind.PUBLIC_FUNCTION
            return (
                Visibility.PUBLIC,
                kind,
                0.65,
                "Top-level Python symbol with no private prefix — inferred public.",
            )

        # ── 13. Methods of public classes ─────────────────────────────
        if sym_type == "method" and parent_class:
            return (
                Visibility.INTERNAL,
                ApiKind.PUBLIC_METHOD,
                0.60,
                f"Method of class '{parent_class}'; classified as internal unless class is exported.",
            )

        # ── 14. Fallback → UNKNOWN ─────────────────────────────────────
        return (
            Visibility.UNKNOWN,
            ApiKind.UNKNOWN,
            0.0,
            "Could not determine visibility with sufficient confidence.",
        )

    # ------------------------------------------------------------------
    # Status (deprecation / experimental)
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_status(
        file_content: str,
        line_number: int,
        decorators: List[str],
    ):
        """Return (ApiStatus, reason_string)."""
        # Scan 10 lines before and 5 after the definition for markers
        lines = file_content.splitlines()
        start = max(0, line_number - 10)
        end = min(len(lines), line_number + 5)
        snippet = "\n".join(lines[start:end])
        dec_text = " ".join(decorators)

        if _DEPRECATED_MARKERS.search(snippet) or _DEPRECATED_MARKERS.search(dec_text):
            return (ApiStatus.DEPRECATED, "Deprecation marker detected near definition.")

        if _EXPERIMENTAL_MARKERS.search(snippet) or _EXPERIMENTAL_MARKERS.search(dec_text):
            return (ApiStatus.EXPERIMENTAL, "Experimental marker detected near definition.")

        return (ApiStatus.STABLE, "")

    # ------------------------------------------------------------------
    # Decorator extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_decorators_near_line(file_content: str, line_number: int) -> List[str]:
        """Return decorator strings in the 5 lines immediately before the definition."""
        lines = file_content.splitlines()
        start = max(0, line_number - 6)
        end = line_number - 1
        decorators = []
        for line in lines[start:end]:
            stripped = line.strip()
            if stripped.startswith("@"):
                decorators.append(stripped)
        return decorators

    # ------------------------------------------------------------------
    # Parameter count estimation
    # ------------------------------------------------------------------

    _PY_PARAM_RE = re.compile(r"def\s+\w+\s*\(([^)]*)\)", re.DOTALL)
    _JS_PARAM_RE = re.compile(
        r"(?:function\s+\w+\s*\(([^)]*)\)|"
        r"(?:async\s+)?(?:\w+\s*)?\(([^)]*)\)\s*=>)",
        re.DOTALL,
    )

    @classmethod
    def _estimate_param_count(cls, file_content: str, line_number: int, lang: str) -> int:
        """Count formal parameters in the function definition on or near line_number."""
        lines = file_content.splitlines()
        # Look at 3 lines starting from the definition
        start = max(0, line_number - 1)
        snippet = "\n".join(lines[start: start + 3])

        pattern = cls._PY_PARAM_RE if lang == "python" else cls._JS_PARAM_RE
        m = pattern.search(snippet)
        if not m:
            return 0

        param_str = m.group(1) or (m.group(2) if m.lastindex and m.lastindex >= 2 else "")
        if not param_str or not param_str.strip():
            return 0

        # Remove type annotations and defaults, count commas
        raw = re.sub(r"=[^,)]+", "", param_str)   # remove defaults
        raw = re.sub(r":\s*[^,)]+", "", raw)       # remove type hints
        params = [p.strip() for p in raw.split(",")
                  if p.strip() and p.strip() not in ("self", "cls", "*", "**")]
        return len(params)

    # ------------------------------------------------------------------
    # Async detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_async(file_content: str, line_number: int) -> bool:
        lines = file_content.splitlines()
        if line_number < 1 or line_number > len(lines):
            return False
        line = lines[line_number - 1]
        return bool(re.match(r"\s*async\s+(def|function)\s+", line))

    # ------------------------------------------------------------------
    # Python __all__ extraction (file-level, called once per file)
    # ------------------------------------------------------------------

    @staticmethod
    def extract_python_all(file_content: str) -> Optional[Set[str]]:
        """Extract names from Python __all__ = [...]. Returns None if absent."""
        m = _PY_ALL_PATTERN.search(file_content)
        if not m:
            return None
        raw = m.group(1)
        # Strip quotes, commas
        names = re.findall(r"""['"]([^'"]+)['"]""", raw)
        return set(names)  # empty set is valid — __all__ = [] means nothing is exported
