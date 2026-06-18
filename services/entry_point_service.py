"""Entry Point Detection Service.

Identifies the primary entry points of a repository based on filename
conventions, framework-specific patterns, and structural heuristics.

Supported detection targets (Phase 1):
  Python   : main.py, __main__.py, FastAPI app, Flask app
  Node.js  : index.js, server.js, app.js
  React    : main.tsx, App.tsx
  Next.js  : app/ directory, pages/ directory

The service is designed so that new patterns can be added by extending the
`_PATTERNS` registry without touching the core detection logic.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pattern registry
# ---------------------------------------------------------------------------
# Each entry is a dict with:
#   name           – human-readable pattern name
#   condition      – callable(file_path, parsed_file|None) → bool
#   priority       – lower number = higher priority in the output list
# ---------------------------------------------------------------------------

_NEXT_DIR_PATTERNS = {"app", "pages"}

# Directories whose files should NOT be considered framework entry points even
# if they import FastAPI/Flask.  Tutorial and test files all import the
# framework but are not the application root.
_FRAMEWORK_INIT_EXCLUDED_PREFIXES = (
    "tests/",
    "test/",
    "docs/",
    "docs_src/",
    "examples/",
    "example/",
    "scripts/",
    "benchmarks/",
)


def _is_python_framework_init(file_path: str, parsed: Optional[Dict]) -> bool:
    """True if the file is a Python application entry point that instantiates
    FastAPI or Flask — NOT merely a file that imports those frameworks.

    Detection strategy (in priority order):
      1. Skip files in test/docs/example directories — they import the
         framework but are not the application root.
      2. Check if the file imports fastapi or flask AND defines at least one
         function or variable that strongly suggests it is the app module
         (e.g. the file contains no class definitions suggesting it is a
         library module, OR it is named app.py / server.py / wsgi.py /
         asgi.py at any depth).
      3. Fallback: only flag files that import fastapi/flask AND reside
         in the top two directory levels of the repository (avoid deeply
         nested tutorial fragments).
    """
    if not parsed:
        return False

    lang = parsed.get("language", "")
    if lang != "python":
        return False

    fp_lower = file_path.replace("\\", "/").lower()

    # Rule 1 — exclude known non-entry directories
    for prefix in _FRAMEWORK_INIT_EXCLUDED_PREFIXES:
        if fp_lower.startswith(prefix):
            return False

    imports_lower = [i.lower() for i in parsed.get("imports", [])]
    has_framework = "fastapi" in imports_lower or "flask" in imports_lower
    if not has_framework:
        return False

    # Rule 2 — application-suggestive filename at any depth
    basename = os.path.basename(fp_lower)
    _APP_NAMES = {"app.py", "application.py", "server.py", "wsgi.py", "asgi.py", "run.py"}
    if basename in _APP_NAMES:
        return True

    # Rule 3 — file is in the top two levels of the repo tree
    parts = fp_lower.split("/")
    if len(parts) <= 2:  # e.g. "api.py" or "backend/api.py"
        return True

    return False


_PATTERNS: List[Dict] = [
    # Python: explicit entry point filenames
    {
        "name": "python_main",
        "condition": lambda fp, _p: os.path.basename(fp) == "main.py",
        "priority": 1,
    },
    {
        "name": "python_dunder_main",
        "condition": lambda fp, _p: os.path.basename(fp) == "__main__.py",
        "priority": 2,
    },
    # Python: framework initialisation files
    {
        "name": "python_framework_init",
        "condition": _is_python_framework_init,
        "priority": 3,
    },
    # JavaScript/TypeScript: conventional entry points
    {
        "name": "js_index",
        "condition": lambda fp, _p: os.path.basename(fp) == "index.js",
        "priority": 4,
    },
    {
        "name": "js_server",
        "condition": lambda fp, _p: os.path.basename(fp) == "server.js",
        "priority": 4,
    },
    {
        "name": "js_app",
        "condition": lambda fp, _p: os.path.basename(fp) == "app.js",
        "priority": 5,
    },
    # React: common entry points
    {
        "name": "react_main_tsx",
        "condition": lambda fp, _p: os.path.basename(fp) == "main.tsx",
        "priority": 4,
    },
    {
        "name": "react_app_tsx",
        "condition": lambda fp, _p: os.path.basename(fp) == "App.tsx",
        "priority": 5,
    },
    {
        "name": "react_main_ts",
        "condition": lambda fp, _p: os.path.basename(fp) == "main.ts",
        "priority": 4,
    },
]


class EntryPointService:
    """Detects entry points in a repository using file patterns and heuristics."""

    def detect(
        self,
        file_paths: List[str],
        parsed_files: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Detect entry points across the full file list.

        Args:
            file_paths: All file paths in the repository (relative).
            parsed_files: Optional parsed metadata from TreeSitterService.
                          Used to apply content-aware heuristics (e.g.
                          detecting FastAPI instantiation).

        Returns:
            A dictionary with:
                entry_points  – list of detected entry point paths (sorted by
                                priority, deduplicated)
                next_js       – True if Next.js app/ or pages/ dirs detected
                patterns_hit  – list of pattern names that fired
        """
        parsed_map: Dict[str, Dict] = {}
        if parsed_files:
            for pf in parsed_files:
                parsed_map[pf["file_path"]] = pf

        hits: List[Dict] = []
        seen: set = set()

        for fp in file_paths:
            parsed = parsed_map.get(fp)
            for pattern in _PATTERNS:
                try:
                    if pattern["condition"](fp, parsed):
                        if fp not in seen:
                            hits.append({
                                "path": fp,
                                "priority": pattern["priority"],
                                "pattern": pattern["name"],
                            })
                            seen.add(fp)
                except Exception as exc:
                    logger.debug("Pattern %s raised for %s: %s", pattern["name"], fp, exc)

        # Deduplicate and sort by priority then path
        hits.sort(key=lambda h: (h["priority"], h["path"]))

        entry_points = [h["path"] for h in hits]
        patterns_hit = list({h["pattern"] for h in hits})

        # Next.js detection: presence of app/ or pages/ at repo root level
        next_js = self._detect_nextjs(file_paths)

        return {
            "entry_points": entry_points,
            "next_js": next_js,
            "patterns_hit": patterns_hit,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_nextjs(file_paths: List[str]) -> bool:
        """Return True if Next.js directory structure is detected."""
        for fp in file_paths:
            parts = fp.split("/")
            if parts and parts[0] in _NEXT_DIR_PATTERNS:
                return True
        return False
