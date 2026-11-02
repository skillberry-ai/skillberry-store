#!/usr/bin/env bash
# The night-out-planner demo (design §9) end to end against UNMODIFIED rossoctl,
# on one machine, without Docker or Kind:
#
#   kwok control plane (a real kube-apiserver, no kubelets) <- rossoctl backend (main, from source)
#   weather-tool + reservation-tool (rossoctl/examples, run as local processes)
#   skillberry-store (from source) with the rossoctl-tools plugin
#
# rossoctl creates real Deployments, Services and skill ConfigMaps. There is no
# kubelet, so "the agent" is played by generic_agent's own MCP client
# (langchain-mcp-adapters MultiServerMCPClient) configured from the Deployment
# rossoctl created: its MCP_URLS and the skill fetched as the init container does.
#
# Required env: ROSSOCTL_REPO (a rossoctl checkout at main), EXAMPLES_REPO
# (rossoctl/examples), KUBECONFIG (a kwok cluster with the AgentRuntime CRD).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STORE_REPO=${STORE_REPO:-$(cd "$HERE/../../../.." && pwd)}
ROSSOCTL_REPO=${ROSSOCTL_REPO:?set ROSSOCTL_REPO to a rossoctl checkout (main)}
EXAMPLES_REPO=${EXAMPLES_REPO:?set EXAMPLES_REPO to a rossoctl/examples checkout}
: "${KUBECONFIG:?set KUBECONFIG to a kwok cluster}"
INSTRUCTIONS=${INSTRUCTIONS:-$STORE_REPO/docs/demos/rossoctl-night-out-planner/instructions.md}
WORK=${WORK:-/tmp/rossoctl-tools-demo}
LOGS=$WORK/logs
STORE_PORT=${STORE_PORT:-8000}
BACKEND_PORT=${BACKEND_PORT:-8010}
WEATHER_PORT=${WEATHER_PORT:-18001}
RESERVATION_PORT=${RESERVATION_PORT:-18002}
rm -rf "$WORK"; mkdir -p "$LOGS"

log() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
wait_http() { for _ in $(seq 1 180); do curl -fsS -o /dev/null "$1" 2>/dev/null && return 0; sleep 1; done; echo "timeout: $1"; return 1; }
wait_tcp() { for _ in $(seq 1 120); do (exec 3<>/dev/tcp/127.0.0.1/"$1") 2>/dev/null && return 0; sleep 1; done; echo "timeout: port $1"; return 1; }
for p in $STORE_PORT $BACKEND_PORT $WEATHER_PORT $RESERVATION_PORT; do
  if (exec 3<>/dev/tcp/127.0.0.1/"$p") 2>/dev/null; then echo "port $p is in use"; exit 1; fi
done

set -m   # each service in its own process group, so cleanup stops grandchildren too
PIDS=""
cleanup() { for p in $PIDS; do kill -- -"$p" 2>/dev/null || kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT
STORE=http://127.0.0.1:$STORE_PORT
BACKEND=http://127.0.0.1:$BACKEND_PORT

# ----------------------------------------------------------------------------
log "1. Tools: weather-tool and reservation-tool, deployed as rossoctl tools"
(cd "$EXAMPLES_REPO/mcp/weather_tool" && PORT=$WEATHER_PORT HOST=127.0.0.1 OTEL_SDK_DISABLED=true \
   exec uv run --frozen weather_tool.py >"$LOGS/weather.log" 2>&1) & PIDS="$PIDS $!"
(cd "$EXAMPLES_REPO/mcp/reservation_tool" && PORT=$RESERVATION_PORT HOST=127.0.0.1 \
   exec uv run --frozen reservation_tool.py >"$LOGS/reservation.log" 2>&1) & PIDS="$PIDS $!"
wait_tcp $WEATHER_PORT; wait_tcp $RESERVATION_PORT

# A fake node that kwok manages, so pods schedule and become Ready.
kubectl apply -f - >/dev/null <<'NODE'
apiVersion: v1
kind: Node
metadata:
  name: kwok-node-0
  annotations: {kwok.x-k8s.io/node: fake}
  labels: {type: kwok, kubernetes.io/hostname: kwok-node-0}
NODE
for ns in team1 team2 rossoctl-system; do kubectl create ns $ns --dry-run=client -o yaml | kubectl apply -f - >/dev/null; done
kubectl label ns team1 team2 rossoctl-enabled=true --overwrite >/dev/null
# The objects 72-deploy-weather-tool.sh / the console preset create: a
# Deployment, the <tool>-mcp Service and an AgentRuntime. The Service port is
# the local port of the stand-in process.
deploy_tool() {  # ns name port
  kubectl apply -f - >/dev/null <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $2
  namespace: $1
  labels: {rossoctl.io/type: tool, protocol.rossoctl.io/mcp: "", rossoctl.io/transport: streamable_http, app.kubernetes.io/name: $2}
spec:
  replicas: 1
  selector: {matchLabels: {app.kubernetes.io/name: $2}}
  template:
    metadata: {labels: {rossoctl.io/type: tool, app.kubernetes.io/name: $2}}
    spec: {containers: [{name: mcp, image: ghcr.io/rossoctl/examples/${2//-/_}:latest}]}
---
apiVersion: v1
kind: Service
metadata:
  name: $2-mcp
  namespace: $1
  labels: {rossoctl.io/type: tool, app.kubernetes.io/name: $2}
spec:
  selector: {app.kubernetes.io/name: $2}
  ports: [{name: http, port: $3, targetPort: $3}]
---
apiVersion: agent.rossoctl.dev/v1alpha1
kind: AgentRuntime
metadata: {name: $2, namespace: $1}
spec: {type: tool, targetRef: {apiVersion: apps/v1, kind: Deployment, name: $2}}
EOF
}
deploy_tool team1 weather-tool $WEATHER_PORT
deploy_tool team1 reservation-tool $RESERVATION_PORT
deploy_tool team2 weather-tool $WEATHER_PORT          # team2: no reservation tool
kubectl -n team1 wait --for=condition=Available deploy/weather-tool deploy/reservation-tool --timeout=90s >/dev/null
echo "team1: weather-tool, reservation-tool (Available); team2: weather-tool only"

# ----------------------------------------------------------------------------
log "2. rossoctl backend from main ($(git -C "$ROSSOCTL_REPO" log -1 --format='%h %s' | cut -c1-60)), unmodified"
if [[ -n "$(git -C "$ROSSOCTL_REPO" status --porcelain -- rossoctl/backend)" ]]; then echo "rossoctl backend has local changes"; exit 1; fi
# Off cluster, rossoctl reaches tools at http://<tool>.<domain>:8080; route that to the tools.
python3 - >"$LOGS/gateway.log" 2>&1 <<PY &
import asyncio
ROUTES = {"weather-tool": $WEATHER_PORT, "reservation-tool": $RESERVATION_PORT}
async def handle(reader, writer):
    head = await reader.readuntil(b"\r\n\r\n")
    host = next((l.split(b":", 1)[1].strip().split(b":")[0].decode() for l in head.split(b"\r\n") if l.lower().startswith(b"host:")), "")
    port = ROUTES.get(host.split(".")[0])
    if not port:
        writer.write(b"HTTP/1.1 404 Not Found\r\ncontent-length: 0\r\n\r\n"); await writer.drain(); writer.close(); return
    ur, uw = await asyncio.open_connection("127.0.0.1", port)
    uw.write(head)
    async def pipe(r, w):
        try:
            while (d := await r.read(65536)):
                w.write(d); await w.drain()
        finally:
            w.close()
    await asyncio.gather(pipe(reader, uw), pipe(ur, writer), return_exceptions=True)
async def main():
    async with await asyncio.start_server(handle, "127.0.0.1", 8080) as s:
        await s.serve_forever()
asyncio.run(main())
PY
PIDS="$PIDS $!"
wait_tcp 8080
(cd "$ROSSOCTL_REPO/rossoctl/backend" && \
  ROSSOCTL_FEATURE_FLAG_SKILLS=true ROSSOCTL_FEATURE_FLAG_EXTERNAL_SKILLS=true ENABLE_AUTH=false \
  DOMAIN_NAME=localtest.me SKILL_AUTOSYNC_INTERVAL=5 SKILL_REGISTRY_ALLOWED_HOSTS=127.0.0.1,localhost \
  exec uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT >"$LOGS/backend.log" 2>&1) & PIDS="$PIDS $!"
wait_http "$BACKEND/api/v1/config/features"
curl -s "$BACKEND/api/v1/config/features" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("rossoctl features:", {k: d.get(k) for k in ("skills", "externalSkills")})'

# ----------------------------------------------------------------------------
log "3. skillberry-store with the rossoctl-tools plugin (local execution mode)"
echo '{"disabled": [], "owners": {}}' > "$WORK/plugins.json"
(cd "$STORE_REPO" && source .venv/bin/activate && \
  SBS_BASE_DIR="$WORK/sbs" SKILLBERRY_PLUGIN_CONFIG="$WORK/plugins.json" SBS_PORT=$STORE_PORT \
  ROSSOCTL_BACKEND_URL="$BACKEND" ROSSOCTL_ALLOWED_NAMESPACES=team1,team2 EXECUTE_PYTHON_LOCALLY=true \
  PROMETHEUS_METRICS_PORT=0 SBS_ACCESS_CONTROL_CONFIG="$STORE_REPO/access_control_config.yaml.disabled" \
  SBS_CLI_DOWNLOAD=off exec python -m skillberry_store.main >"$LOGS/store.log" 2>&1) & PIDS="$PIDS $!"
wait_http "$STORE/health/ready"
curl -s "$STORE/plugins/" | python3 -c 'import json,sys; [print("plugin", p["slug"], "-", p["status"]) for p in json.load(sys.stdin) if p["slug"] == "rossoctl-tools"]'
kubectl apply -f - >/dev/null <<EOF
apiVersion: v1
kind: ConfigMap
metadata: {name: rossoctl-skill-autosync-config, namespace: rossoctl-system}
data: {enabled: "true", registry-type: skillberry, registry-url: "$STORE", sync-interval: "5", allowed-tags: "rossoctl-approved"}
EOF

# ----------------------------------------------------------------------------
log "4. Import the tools and compose the skill"
python3 - "$STORE" "$INSTRUCTIONS" <<'PY'
import json, sys, urllib.request
store, instr = sys.argv[1], open(sys.argv[2]).read()
body = {"namespace": "team1",
        "tools": [{"name": "weather-tool", "read_only": ["get_weather"]},
                  {"name": "reservation-tool", "read_only": ["search_restaurants", "check_availability", "list_reservations"]}],
        "skill": {"name": "night-out-planner",
                  "description": "Plan and book a restaurant evening in a city, taking current weather into account.",
                  "instructions": instr, "tags": ["rossoctl-approved"]}}
req = urllib.request.Request(f"{store}/plugins/rossoctl-tools/import", json.dumps(body).encode(), {"content-type": "application/json"})
out = json.load(urllib.request.urlopen(req, timeout=120))
print("tools:", [t["name"] for t in out["tools"]], "| errors:", out["errors"])
PY

log "5. Store-side test: the proxy code tool runs in the store and calls rossoctl /invoke"
curl -s -X POST "$STORE/tools/search_restaurants/execute" -H 'content-type: application/json' \
  -d '{"city":"Boston","cuisine":"Italian"}' | python3 -c 'import json,sys; r=json.load(sys.stdin); print("search_restaurants ->", [x["name"] for x in json.loads(r["return value"])])'
echo "rossoctl /invoke calls: $(grep -c 'POST /api/v1/tools/team1/reservation-tool/invoke' "$LOGS/backend.log")"

log "6. The deployment recipe for team1 (skill + MCP_URLS)"
curl -s -X POST "$STORE/plugins/rossoctl-tools/recipe" -H 'content-type: application/json' \
  -d '{"skill":"night-out-planner","namespace":"team1","agent":{"name":"night-out"}}' > "$WORK/recipe-team1.json"
python3 - "$WORK/recipe-team1.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print("ok:", r["ok"], "| missing:", r["missing"])
for c in r["preflight"]:
    print(f"  {c['tool']}: present={c['present']} ready={c['ready']} port={c['port']}")
print("request.skills:", r["request"]["skills"])
for e in r["request"]["envVars"]:
    print(f"  {e['name']}={e['value']}")
PY

log "7. rossoctl autosync creates the skill in team1"
for _ in $(seq 1 60); do kubectl -n team1 get cm night-out-planner >/dev/null 2>&1 && break; sleep 2; done
kubectl -n team1 get cm night-out-planner -o jsonpath='{.metadata.labels.rossoctl\.io/source}{" "}{.metadata.annotations.rossoctl\.io/registry-skill-name}{"\n"}'

log "8. Create the agent in rossoctl with the recipe (+ the user's model settings)"
python3 - "$WORK/recipe-team1.json" "$BACKEND" <<'PY'
import json, sys, urllib.request
r = json.load(open(sys.argv[1]))
req = r["request"]
req["envVars"] += [{"name": "LLM_API_BASE", "value": "http://llm.example/v1"},
                   {"name": "LLM_MODEL", "value": "demo"}, {"name": "LLM_API_KEY", "value": "dummy"}]
req["authBridgeEnabled"] = False   # no SPIRE/Keycloak in this harness
out = json.load(urllib.request.urlopen(urllib.request.Request(
    f"{sys.argv[2]}/api/v1/agents", json.dumps(req).encode(), {"content-type": "application/json"}), timeout=60))
print("rossoctl:", out["message"])
PY
kubectl -n team1 get deploy night-out -o json | python3 -c '
import json,sys
d=json.load(sys.stdin); spec=d["spec"]["template"]["spec"]
env={e["name"]: e.get("value") for e in spec["containers"][0]["env"]}
print("  image:", spec["containers"][0]["image"])
print("  MCP_URLS:", env.get("MCP_URLS"))
print("  SKILL_FOLDERS:", env.get("SKILL_FOLDERS"))
print("  init containers:", [c["name"] for c in spec.get("initContainers", [])])
print("  annotation rossoctl.io/skills:", d["metadata"]["annotations"].get("rossoctl.io/skills"))'

log "9. The agent: fetch the skill like the init container, connect to MCP_URLS like generic_agent"
POD=$WORK/agent-pod; mkdir -p "$POD/app/skills/night-out-planner"
curl -fsSL -o "$POD/skill.zip" "$STORE/skills/night-out-planner/export-anthropic"
python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$POD/skill.zip" "$POD/x"
cp -r "$POD/x/night-out-planner/." "$POD/app/skills/night-out-planner/"
ls "$POD/app/skills/night-out-planner"
(cd "$STORE_REPO" && source .venv/bin/activate && python - "$WORK/recipe-team1.json" "$POD/app/skills/night-out-planner" $WEATHER_PORT $RESERVATION_PORT) <<'PY'
import asyncio, json, sys
from langchain_mcp_adapters.client import MultiServerMCPClient
recipe, skill_dir, wport, rport = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
env = {e["name"]: e["value"] for e in json.load(open(recipe))["request"]["envVars"]}
local = {"weather-tool": wport, "reservation-tool": rport}
# The pod resolves <tool>-mcp.team1.svc.cluster.local; on this host, map to the tool process.
urls = []
for u in env["MCP_URLS"].split(","):
    tool = u.split("//", 1)[1].split("-mcp.", 1)[0]
    urls.append(f"http://127.0.0.1:{local[tool]}/mcp")
skill_md = open(f"{skill_dir}/SKILL.md").read()
print("SKILL.md Tools section present:", "## Tools" in skill_md, "| mentions MCP tools:", "`place_reservation`" in skill_md)
client = MultiServerMCPClient({f"mcp{i}": {"url": u, "transport": env["MCP_TRANSPORT"], "timeout": 60} for i, u in enumerate(urls, 1)})
def text(result):
    # langchain-mcp-adapters returns a string, or a list of content blocks.
    if isinstance(result, str):
        return result
    if isinstance(result, (list, tuple)):
        return "".join(b.get("text", "") if isinstance(b, dict) else getattr(b, "text", str(b)) for b in result)
    return str(result)
async def call(tool, args):
    return json.loads(text(await tool.ainvoke(args)))
async def go():
    tools = {t.name: t for t in await client.get_tools()}
    print("MCP tools the agent sees:", sorted(tools))
    found = await call(tools["search_restaurants"], {"city": "Boston", "cuisine": "Italian"})
    print("search_restaurants ->", [r["name"] for r in found])
    slots = await call(tools["check_availability"], {"restaurant_id": found[0]["id"], "date_time": "2026-10-28T19:00:00", "party_size": 4})
    print("19:00 available:", [s["available"] for s in slots if s["time"].endswith("19:00:00")],
          "| free dinner:", [s["time"][11:16] for s in slots if s["available"] and s["time"][11:13] >= "17"])
    booking = await call(tools["place_reservation"], {"restaurant_id": found[0]["id"], "date_time": "2026-10-28T19:30:00",
        "party_size": 4, "name": "Ada Lovelace", "phone": "555-0100", "email": "ada@example.com"})
    print("place_reservation -> confirmation", booking["confirmation_code"], "status", booking["status"])
    weather = text(await tools["get_weather"].ainvoke({"city": "Boston"}))
    print("get_weather ->", weather[:120])
asyncio.run(go())
PY

log "10. Portability: the recipe for team2 reports what is missing before anything is created"
curl -s -X POST "$STORE/plugins/rossoctl-tools/recipe" -H 'content-type: application/json' \
  -d '{"skill":"night-out-planner","namespace":"team2"}' | python3 -c 'import json,sys; r=json.load(sys.stdin); print("team2 ok:", r["ok"], "| missing:", r["missing"], "| MCP_URLS:", [e["value"] for e in r["request"]["envVars"] if e["name"]=="MCP_URLS"])'
deploy_tool team2 reservation-tool $RESERVATION_PORT
kubectl -n team2 wait --for=condition=Available deploy/reservation-tool --timeout=90s >/dev/null
curl -s -X POST "$STORE/plugins/rossoctl-tools/recipe" -H 'content-type: application/json' \
  -d '{"skill":"night-out-planner","namespace":"team2"}' | python3 -c 'import json,sys; r=json.load(sys.stdin); print("after deploying it: team2 ok:", r["ok"], "| missing:", r["missing"])'

log "11. rossoctl is unmodified"
git -C "$ROSSOCTL_REPO" status --porcelain | wc -l | sed 's/^/  changed files in the rossoctl checkout: /'

log "Demo complete. Logs: $LOGS"
