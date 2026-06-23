"""Model Context Protocol (MCP) Stdio Server.

Exposes the Repo Intelligence Agent's analysis engines (symbols, call graphs, 
dependency graphs, dead code, PR analysis, and retrieval) as standard MCP tools.
"""

import json
import os
import sys
import traceback
import logging
from typing import Dict, Any, List

# Redirect all root logging to stderr. Stdout MUST be preserved exclusively for JSON-RPC.
logger = logging.getLogger()
for handler in list(logger.handlers):
    logger.removeHandler(handler)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(logging.Formatter("[MCP Log] %(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(stderr_handler)
logger.setLevel(logging.INFO)

# Expose tools definition list
TOOLS = [
    {
        "name": "list_repositories",
        "description": "Lists all repositories currently analyzed and persisted in the system.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "get_repository_summary",
        "description": "Retrieves the parsed tech stack, dependency declarations, and high-level structure of a repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Owner/organization name"},
                "repo": {"type": "string", "description": "Repository name"}
            },
            "required": ["owner", "repo"]
        }
    },
    {
        "name": "get_file_symbols",
        "description": "Returns all classes, functions, and methods defined inside a specific source file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "file_path": {"type": "string", "description": "Relative file path (e.g. core/cache.py)"}
            },
            "required": ["owner", "repo", "file_path"]
        }
    },
    {
        "name": "get_symbol_definition",
        "description": "Looks up the definition location and signature of a specific symbol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "symbol_name": {"type": "string", "description": "Name of the class, function, or method"}
            },
            "required": ["owner", "repo", "symbol_name"]
        }
    },
    {
        "name": "get_symbol_references",
        "description": "Returns all file occurrences and usages of a specific symbol in the repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "symbol_name": {"type": "string", "description": "Name of the symbol"}
            },
            "required": ["owner", "repo", "symbol_name"]
        }
    },
    {
        "name": "get_call_graph",
        "description": "Retrieves call graph statistics and relations for a repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"}
            },
            "required": ["owner", "repo"]
        }
    },
    {
        "name": "get_dead_code",
        "description": "Retrieves orphaned modules and unreachable code paths in the repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"}
            },
            "required": ["owner", "repo"]
        }
    },
    {
        "name": "query_codebase",
        "description": "Runs a context-grounded natural language search query over the repository files (RAG chat).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "owner": {"type": "string", "description": "Repository owner"},
                "repo": {"type": "string", "description": "Repository name"},
                "query": {"type": "string", "description": "Question or query text about the code"}
            },
            "required": ["owner", "repo", "query"]
        }
    }
]


def send_response(response: Dict[str, Any]) -> None:
    """Helper to dump response JSON to standard output."""
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def run_mcp_server() -> None:
    """Main loop reading JSON-RPC requests from stdin and responding to stdout."""
    logger.info("Initializing Repo Intelligence MCP Server...")

    # Lazy-load back-end singletons on start
    from backend.dependencies import (
        ANALYSIS_STORE,
        symbol_service,
        call_graph_service,
        dead_code_service,
        retrieval_service
    )

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line.strip())
            req_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            # 1. Initialization handshake
            if method == "initialize":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "repo-intelligence-mcp",
                            "version": "1.0.0"
                        }
                    }
                })

            # 2. List tools
            elif method == "tools/list":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": TOOLS
                    }
                })

            # 3. Call tool
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                result_content = []
                try:
                    tool_result = execute_tool(
                        tool_name, arguments, ANALYSIS_STORE, symbol_service,
                        call_graph_service, dead_code_service, retrieval_service
                    )
                    result_content.append({
                        "type": "text",
                        "text": json.dumps(tool_result, indent=2)
                    })
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": result_content
                        }
                    })
                except Exception as tool_err:
                    logger.error(f"Tool {tool_name} failed: {tool_err}")
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32603,
                            "message": f"Tool execution failed: {str(tool_err)}",
                            "data": traceback.format_exc()
                        }
                    })

            # 4. Unknown/unsupported JSON-RPC method
            else:
                if req_id is not None:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method {method} not found."
                        }
                    })
        except Exception as exc:
            logger.error(f"Error handling MCP request: {exc}")
            # If request could not be parsed, send generic error
            send_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                    "data": str(exc)
                }
            })


def execute_tool(
    name: str,
    args: Dict[str, Any],
    store: Dict[str, Any],
    symbols: Any,
    call_graph: Any,
    dead_code: Any,
    retrieval: Any
) -> Any:
    """Invokes the corresponding backend service and returns serializable data."""
    if name == "list_repositories":
        return list(store.keys())

    owner = args.get("owner", "").strip()
    repo = args.get("repo", "").strip()
    repo_name = f"{owner}/{repo}"

    if name == "get_repository_summary":
        if repo_name not in store:
            raise ValueError(f"Repository '{repo_name}' is not indexed. Analyze it first.")
        entry = store[repo_name]
        return {
            "analysis": entry["analysis"].model_dump() if hasattr(entry["analysis"], "model_dump") else entry["analysis"],
            "architecture": entry["architecture"].model_dump() if hasattr(entry["architecture"], "model_dump") else entry["architecture"]
        }

    elif name == "get_file_symbols":
        file_path = args.get("file_path", "").strip()
        res = symbols.get_file_symbols(repo_name, file_path)
        if res is None:
            raise ValueError(f"No symbol index found for file '{file_path}' in repo '{repo_name}'.")
        return [s.model_dump() for s in res]

    elif name == "get_symbol_definition":
        sym_name = args.get("symbol_name", "").strip()
        res = symbols.get_definition(repo_name, sym_name)
        if res is None:
            raise ValueError(f"Symbol '{sym_name}' not found in repo '{repo_name}'.")
        return res.model_dump()

    elif name == "get_symbol_references":
        sym_name = args.get("symbol_name", "").strip()
        res = symbols.get_references(repo_name, sym_name)
        return [s.model_dump() for s in res]

    elif name == "get_call_graph":
        res = call_graph.get_graph_summary(repo_name)
        if res is None:
            raise ValueError(f"No call graph indexed for '{repo_name}'.")
        return res.model_dump()

    elif name == "get_dead_code":
        # Check if repo metadata exists
        if repo_name not in store:
            raise ValueError(f"Repository '{repo_name}' is not indexed.")
        local_path = store[repo_name]["analysis"].metadata.get("local_path", "")
        # Run dead code sweep
        from services.dead_code_service import DeadCodeService
        dc_service = DeadCodeService()
        from backend.dependencies import github_service, graph_service, architecture_service
        dc_service.github_service = github_service
        dc_service.graph_service = graph_service
        dc_service.architecture_service = architecture_service
        
        # Build graphs if not existing
        res = dc_service.analyze(repo_name)
        return res.model_dump()

    elif name == "query_codebase":
        query = args.get("query", "").strip()
        # Perform retrieval Q&A
        res = retrieval.retrieve_and_evaluate(repo_name, query)
        return {
            "answer": res.get("answer", ""),
            "sources": [s.model_dump() if hasattr(s, "model_dump") else s for s in res.get("sources", [])],
            "confidence": res.get("confidence", 0.0),
            "verified": res.get("verified", False)
        }

    else:
        raise ValueError(f"Tool {name} is not supported.")
