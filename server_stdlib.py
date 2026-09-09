"""
Zero-dependency version of the same demo MCP server (Python standard library only).

Implements just enough of MCP Streamable HTTP (JSON-RPC 2.0 over POST /mcp) to be
registered with Agent 365 and invoked by Copilot Studio / VS Code. Useful when you
want to SEE the raw protocol, or can't pip-install anything on the host.

    MCP_API_KEY=demo-secret-123 python server_stdlib.py     # http://localhost:8000/mcp
"""
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from demo_data import KB, TICKETS, next_ticket_id

API_KEY = os.environ.get("MCP_API_KEY", "demo-secret-123")
PROTOCOL_VERSION = "2025-06-18"

TOOLS = [
    {"name": "search_knowledge_base",
     "description": "Search the Zava internal knowledge base. Returns matching articles with id, title and summary.",
     "inputSchema": {"type": "object", "required": ["query"],
                     "properties": {"query": {"type": "string", "description": "Search text"},
                                    "max_results": {"type": "integer", "default": 3}}}},
    {"name": "get_support_ticket",
     "description": "Get a Zava support ticket by id (for example ZAVA-1001). Returns status, priority, owner and summary.",
     "inputSchema": {"type": "object", "required": ["ticket_id"],
                     "properties": {"ticket_id": {"type": "string", "description": "Ticket id such as ZAVA-1001"}}}},
    {"name": "create_support_ticket",
     "description": "Create a new Zava support ticket. priority must be Low, Medium or High. Returns the new ticket id.",
     "inputSchema": {"type": "object", "required": ["title", "description"],
                     "properties": {"title": {"type": "string"}, "description": {"type": "string"},
                                    "priority": {"type": "string", "enum": ["Low", "Medium", "High"], "default": "Medium"}}}},
]


def call_tool(name, args):
    if name == "search_knowledge_base":
        q = args["query"].lower()
        hits = [a for a in KB if q in a["title"].lower() or q in a["body"].lower() or any(q in t for t in a["tags"])]
        return [{"id": a["id"], "title": a["title"], "summary": a["body"][:160]} for a in hits[: args.get("max_results", 3)]]
    if name == "get_support_ticket":
        tid = args["ticket_id"].upper()
        return {"id": tid, **TICKETS[tid]} if tid in TICKETS else {"error": f"Ticket {tid} not found"}
    if name == "create_support_ticket":
        pr = args.get("priority", "Medium")
        if pr not in ("Low", "Medium", "High"):
            return {"error": "priority must be Low, Medium or High"}
        tid = next_ticket_id()
        TICKETS[tid] = {"title": args["title"], "description": args["description"], "priority": pr,
                        "status": "Open", "owner": "unassigned"}
        return {"id": tid, "status": "Open", "message": "Ticket created"}
    raise KeyError(name)


def handle_rpc(msg):
    """Return a JSON-RPC response dict, or None for notifications."""
    method, rid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}},
                  "serverInfo": {"name": "Zava Support MCP (demo, stdlib)", "version": "0.1.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        try:
            out = call_tool(params["name"], params.get("arguments") or {})
            result = {"content": [{"type": "text", "text": json.dumps(out)}],
                      "structuredContent": out if isinstance(out, dict) else {"items": out},
                      "isError": isinstance(out, dict) and "error" in out}
        except KeyError as e:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32602, "message": f"Unknown tool {e}"}}
    elif method and method.startswith("notifications/"):
        return None
    else:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": rid, "result": result}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/healthz":
            return self._send(200, {"ok": True})
        self._send(405, {"error": "Use POST for MCP requests"})   # no server-initiated SSE stream in this demo

    def do_POST(self):
        if not self.path.startswith("/mcp"):
            return self._send(404, {"error": "not found"})
        if self.headers.get("X-API-Key") != API_KEY:
            return self._send(401, {"error": "invalid or missing X-API-Key"})
        length = int(self.headers.get("Content-Length", 0))
        try:
            msg = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
        print(f"--> {msg.get('method')} {json.dumps(msg.get('params') or {})[:120]}", flush=True)
        if isinstance(msg, list):                       # JSON-RPC batch
            replies = [r for r in (handle_rpc(m) for m in msg) if r]
            return self._send(200, replies) if replies else self._send(202)
        reply = handle_rpc(msg)
        return self._send(200, reply) if reply else self._send(202)

    def log_message(self, *_):  # quiet default access log
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Zava demo MCP server listening on http://0.0.0.0:{port}/mcp  (X-API-Key required)", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
