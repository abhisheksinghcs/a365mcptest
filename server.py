"""
Agent 365 BYO MCP demo server (FastMCP / Streamable HTTP).

Tools are backed by an in-memory fake "Zava Support" dataset so there are no
external dependencies. Auth = API key in the X-API-Key header, which maps to the
Agent 365 "APIKey (Header)" registration type.

Run locally:
    pip install -r requirements.txt
    MCP_API_KEY=demo-secret-123 python server.py
Endpoint: http://localhost:8000/mcp
"""
import os
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import uvicorn

from demo_data import KB, TICKETS, next_ticket_id

API_KEY = os.environ.get("MCP_API_KEY", "demo-secret-123")

mcp = FastMCP(
    "Zava Support MCP (demo)",
    stateless_http=True,   # no session bookkeeping - simplest for a gateway-fronted demo
    json_response=True,    # plain JSON replies instead of SSE streams
)


@mcp.tool()
def search_knowledge_base(query: str, max_results: int = 3) -> list[dict]:
    """Search the Zava internal knowledge base. Returns matching articles with id, title and summary."""
    q = query.lower()
    hits = [a for a in KB if q in a["title"].lower() or q in a["body"].lower()
            or any(q in t for t in a["tags"])]
    return [{"id": a["id"], "title": a["title"], "summary": a["body"][:160]} for a in hits[:max_results]]


@mcp.tool()
def get_support_ticket(ticket_id: str) -> dict:
    """Get a Zava support ticket by id (for example ZAVA-1001). Returns status, priority, owner and summary."""
    t = TICKETS.get(ticket_id.upper())
    if not t:
        return {"error": f"Ticket {ticket_id} not found"}
    return {"id": ticket_id.upper(), **t}


@mcp.tool()
def create_support_ticket(title: str, description: str, priority: str = "Medium") -> dict:
    """Create a new Zava support ticket. priority must be Low, Medium or High. Returns the new ticket id."""
    if priority not in ("Low", "Medium", "High"):
        return {"error": "priority must be Low, Medium or High"}
    tid = next_ticket_id()
    TICKETS[tid] = {"title": title, "description": description, "priority": priority,
                    "status": "Open", "owner": "unassigned"}
    return {"id": tid, "status": "Open", "message": "Ticket created"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/mcp") and request.headers.get("x-api-key") != API_KEY:
            return JSONResponse({"error": "invalid or missing X-API-Key"}, status_code=401)
        return await call_next(request)


app = mcp.streamable_http_app()          # mounts the MCP endpoint at /mcp
app.add_middleware(ApiKeyMiddleware)


@app.route("/healthz")
async def healthz(_):
    return JSONResponse({"ok": True})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
