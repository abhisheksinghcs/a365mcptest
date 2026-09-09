# Agent 365 BYO MCP – demo server

A deliberately small remote MCP server you can register with **Microsoft Agent 365** to showcase the
Bring-Your-Own MCP flow (developer registers → admin approves in M365 admin center → agent in Copilot
Studio / VS Code invokes it → Defender advanced hunting shows the calls).

It exposes three tools over a fake in-memory "Zava IT support" dataset:

| Tool | What it does | Why it's in the demo |
|---|---|---|
| `search_knowledge_base` | Full-text search over 4 KB articles | Read-only tool, easy to prompt ("how do I reset VPN?") |
| `get_support_ticket` | Look up `ZAVA-1001..1003` | Shows parameters + not-found handling |
| `create_support_ticket` | Creates a new ticket | A **write** action – nice for the governance / audit story |

Auth is an API key in the `X-API-Key` header → registered as Agent 365 auth type **APIKey (Header)**.

## Files

| File | Purpose |
|---|---|
| `server.py` | Recommended flavour – FastMCP (official `mcp` Python SDK), Streamable HTTP, stateless JSON |
| `server_stdlib.py` | Same tools, **zero dependencies** – hand-rolled JSON-RPC so you can see the wire protocol |
| `demo_data.py` | Fake KB + tickets shared by both |
| `test_client.py` | Stdlib smoke-test client (initialize → tools/list → tools/call) |
| `a365-register.json` | Ready-to-edit registration file for `a365 develop-mcp register-external-mcp-server -f` |
| `Dockerfile`, `requirements.txt` | For Azure Container Apps / App Service |

## 1. Run locally

```bash
# FastMCP flavour
pip install -r requirements.txt
MCP_API_KEY=demo-secret-123 python server.py            # http://localhost:8000/mcp

# or, with no installs at all
MCP_API_KEY=demo-secret-123 python server_stdlib.py

# smoke test
python test_client.py http://localhost:8000/mcp demo-secret-123
```

Set a real secret in `MCP_API_KEY` for anything beyond localhost.

## 2. Make it publicly reachable

Agent 365 requires a **public HTTPS endpoint**. Two easy options:

**Quick (minutes):** a Dev Tunnel in front of your laptop
```bash
devtunnel host -p 8000 --allow-anonymous
# → https://<id>.devtunnels.ms/mcp
```
(`ngrok http 8000` works the same way.)

**Slightly more durable:** Azure Container Apps
```bash
az group create -n rg-a365-mcp-demo -l eastus
az containerapp up -n zava-mcp-demo -g rg-a365-mcp-demo -l eastus \
  --source . --ingress external --target-port 8000 \
  --env-vars MCP_API_KEY=<your-secret>
# → https://zava-mcp-demo.<region>.azurecontainerapps.io/mcp
```

Verify from outside: `python test_client.py https://<host>/mcp <your-secret>`

## 3. Register with Agent 365

Prereqs from the docs: Agent 365 CLI **≥ 1.1.165-preview**, and the Agent 365 service principal
(appId `ea9ffc3e-8a23-4a7d-836d-234d7c7565c1`) provisioned in the tenant.

Edit `serverUrl` in `a365-register.json`, then:

```bash
a365 develop-mcp register-external-mcp-server -f a365-register.json
```

Equivalent one-liner:
```bash
a365 develop-mcp register-external-mcp-server \
  --server-name "ext_ZavaSupportDemo" \
  --server-url  "https://<host>/mcp" \
  --publisher   "Contoso Demo" \
  --description "Demo MCP server: Zava IT support KB and tickets" \
  --auth-type APIKey --api-key-location Header --api-key-name X-API-Key \
  --tools "search_knowledge_base,get_support_ticket,create_support_ticket"
```

Optional – score your tool descriptions before registering:
```bash
a365 develop-mcp evaluate --server-url http://localhost:8000/mcp --eval-engine none
```

## 4. Approve as admin

M365 admin center → **Agents > Tools > Requests** → select `ext_ZavaSupportDemo` → **Approve** → grant
the Entra consent when prompted. Requires AI admin or Global admin. Allow up to ~30 min to appear in
Copilot Studio environments.

## 5. Use it

Copilot Studio → new agent → **Tools > MCP Server** → pick `ext_ZavaSupportDemo`. First invocation
prompts for a one-time connection – paste the API key. Then try:

* "How do I reset my Zava VPN?" → `search_knowledge_base`
* "What's the status of ticket ZAVA-1001?" → `get_support_ticket`
* "Open a high-priority ticket: my laptop won't boot" → `create_support_ticket`

## 6. Show the governance story

* **Block/unblock** the server in the Registry tab and re-run a prompt – the gateway enforces it at runtime.
* Defender XDR advanced hunting:
  ```kusto
  CloudAppEvents
  | where ActionType == "ExecuteToolByGateway"
  | where RawEventData contains "create_support_ticket"
  ```

## Notes / preview caveats
* Republishing a new version of a registered server and deleting a BYO server aren't supported yet –
  get your tool names/descriptions right first, or register under a new `serverName`.
* Supported clients today: Copilot Studio, VS Code, Claude Code, GitHub Copilot CLI (not Foundry or M365 declarative agents).
* The stdlib server answers with plain JSON (no SSE stream) and has no `GET /mcp` – that's within spec for
  Streamable HTTP and fine for the gateway, but not something to copy into production.
* Wrapping GitHub etc.: you don't need to. Point Agent 365 at the vendor's remote MCP endpoint directly with
  auth type `ExternalOAuth` and their OAuth app – the BYO flow is "remote server + auth type", not "your code".
