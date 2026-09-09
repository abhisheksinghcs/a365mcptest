"""Tiny MCP smoke-test client (stdlib only). Usage: python test_client.py http://localhost:8000/mcp demo-secret-123"""
import json, sys, urllib.request, urllib.error

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
key = sys.argv[2] if len(sys.argv) > 2 else "demo-secret-123"
_id = 0


def rpc(method, params=None, notify=False, api_key=key):
    global _id
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if not notify:
        _id += 1
        body["id"] = _id
    req = urllib.request.Request(url, json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                                          "X-API-Key": api_key, "MCP-Protocol-Version": "2025-06-18"})
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


print("no key       ->", rpc("tools/list", api_key="wrong")[0])
print("initialize   ->", rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                          "clientInfo": {"name": "smoke", "version": "0"}})[1]["result"]["serverInfo"])
print("initialized  ->", rpc("notifications/initialized", notify=True)[0])
print("tools/list   ->", [t["name"] for t in rpc("tools/list")[1]["result"]["tools"]])
print("search       ->", rpc("tools/call", {"name": "search_knowledge_base", "arguments": {"query": "vpn"}})[1]["result"]["content"][0]["text"])
print("create       ->", rpc("tools/call", {"name": "create_support_ticket", "arguments": {"title": "Demo", "description": "from client", "priority": "High"}})[1]["result"]["content"][0]["text"])
print("get          ->", rpc("tools/call", {"name": "get_support_ticket", "arguments": {"ticket_id": "zava-1004"}})[1]["result"]["content"][0]["text"])
print("bad tool     ->", rpc("tools/call", {"name": "nope", "arguments": {}})[1]["error"]["message"])
