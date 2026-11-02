# Demo: one skill, two rossoctl tools, one agent ("night-out-planner")

This guide shows how to prepare and run the demo of
[docs/design/rossoctl-skills.md](../design/rossoctl-skills.md) (revision 8):

- you compose a skill in skillberry-store from two tools that already run in rossoctl, `weather-tool` and `reservation-tool`;
- the store generates the rossoctl agent that uses the skill **and** both tools;
- you deploy that agent with stock rossoctl.

**rossoctl is not changed.** You need rossoctl `main` and a store image built with the `rossoctl-tools` plugin. The agent is the stock `generic_agent` example. It reads the skill, and it connects to the tools over MCP through the `MCP_URLS` the store puts in the recipe.

Two ways to run it:

| | [A. Kind cluster](#a-kind-cluster) | [B. One machine, no containers](#b-one-machine-no-containers) |
|---|---|---|
| Needs | Docker or Podman, Kind, Helm, `kubectl`, an LLM endpoint | Python 3.11, `uv`, `curl`, `kubectl`, Helm |
| Shows | Everything, including a live chat | Every step except the chat. The agent's side is played by `generic_agent`'s own MCP client. |
| Time | About 30 minutes | About 5 minutes |

---

## What you will see

1. **Import.** The store's plugin reads both tools from rossoctl's backend. It creates six store tools (`get_weather`, `search_restaurants`, `check_availability`, `place_reservation`, `cancel_reservation`, `list_reservations`) and the skill `night-out-planner`.
2. **Store-side test.** Executing `search_restaurants` in the store returns *Trattoria di Mare*. The store called rossoctl's `/invoke`; it never connected to the tool.
3. **The recipe.** For `team1`, the store reports both tools ready. It produces an agent-create request with `skills: ["night-out-planner"]` and `MCP_URLS` pointing at both tools' Services.
4. **Deploy.** rossoctl creates the agent. Its existing skill fetch puts the skill in the pod, and `generic_agent` puts the skill in its prompt and connects to both tools.
5. **Chat.** "Plan dinner for 4 in Boston tomorrow at 7pm, Italian." The agent:
   - checks the weather;
   - finds Trattoria di Mare;
   - checks the slot, offering the nearest free one if it is taken;
   - asks for your details and a confirmation;
   - books, and returns a confirmation code.
6. **Portability.** For `team2`, which has no reservation tool, the recipe says `missing: ["reservation-tool"]` before anything is created. After you deploy the tool there, the same skill works.

---

## Prepare (both ways)

```bash
mkdir -p ~/demo && cd ~/demo
git clone -b rossoctl-skills https://github.com/erezh16/skillberry-store.git
git clone https://github.com/rossoctl/rossoctl.git                 # main, unmodified
git clone https://github.com/rossoctl/examples.git rossoctl-examples
```

The skill's instructions are in [`rossoctl-night-out-planner/instructions.md`](rossoctl-night-out-planner/instructions.md).

---

## A. Kind cluster

### A.1 A store image with the plugin

```bash
cd ~/demo/skillberry-store
python3 -m venv .venv && source .venv/bin/activate
make docker-build-full                        # all plugins; tagged :<version>-full and :latest-full
docker images | grep skillberry-store         # note the repository name
docker tag <repository>:latest-full skillberry-store:rossoctl-tools
```

### A.2 Install rossoctl with the store configured for the plugin

Write `~/demo/store-values.yaml`. It uses existing chart keys only:

```yaml
skillberryStore:
  image: {repository: skillberry-store, tag: rossoctl-tools, pullPolicy: IfNotPresent}
  extraEnv:
    - {name: ROSSOCTL_BACKEND_URL, value: "http://rossoctl-backend.rossoctl-system.svc.cluster.local:8000"}
    - {name: EXECUTE_PYTHON_LOCALLY, value: "true"}
    - {name: ROSSOCTL_ALLOWED_NAMESPACES, value: "team1,team2"}
    # Only if UI auth is on (--with-spire / --with-all): reuse the existing API client.
    - {name: ROSSOCTL_CLIENT_ID,      valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: CLIENT_ID}}}
    - {name: ROSSOCTL_CLIENT_SECRET,  valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: CLIENT_SECRET}}}
    - {name: ROSSOCTL_TOKEN_ENDPOINT, valueFrom: {secretKeyRef: {name: rossoctl-api-oauth-secret, key: TOKEN_ENDPOINT}}}
  autosync: {allowedTags: "rossoctl-approved"}
apiOAuthSecret: {enabled: true}
```

Without UI auth, drop the three `ROSSOCTL_CLIENT_*`/`TOKEN_*` entries and `apiOAuthSecret`.

```bash
cd ~/demo/rossoctl
kind create cluster --name rossoctl
kind load docker-image skillberry-store:rossoctl-tools --name rossoctl
scripts/kind/setup-rossoctl.sh --skip-cluster --with-skills --with-examples \
  --rossoctl-values ~/demo/store-values.yaml
```

- `--with-skills` deploys the store and turns on skill autosync.
- `--with-examples` deploys `weather-tool` in `team1`.

**Add the reservation tool:** in the console, **Tools → Import Tool → Reservation Tool**, namespace `team1`. Or apply the manifest in the plugin:

```bash
kubectl apply -n team1 -f ~/demo/skillberry-store/plugins/skillberry-plugin-rossoctl-tools/deploy/reservation-tool.yaml
kubectl -n team1 get deploy weather-tool reservation-tool
```

Reach the store API:

```bash
kubectl -n rossoctl-system port-forward svc/skillberry-store 8000:8000 &
STORE=http://localhost:8000
curl -s $STORE/plugins/ | jq '.[] | select(.slug=="rossoctl-tools") | .status'      # "Ready"
```

### A.3 Run the demo

**1. Import** the tools and compose the skill:

```bash
jq -n --rawfile instr ~/demo/skillberry-store/docs/demos/rossoctl-night-out-planner/instructions.md '{
  namespace: "team1",
  tools: [{name: "weather-tool", read_only: ["get_weather"]},
          {name: "reservation-tool", read_only: ["search_restaurants","check_availability","list_reservations"]}],
  skill: {name: "night-out-planner",
          description: "Plan and book a restaurant evening in a city, taking current weather into account.",
          instructions: $instr, tags: ["rossoctl-approved"]}}' |
curl -s -X POST $STORE/plugins/rossoctl-tools/import -H 'content-type: application/json' -d @- | jq '{tools: [.tools[].name], errors}'
```

**2. Store-side test:**

```bash
curl -s -X POST $STORE/tools/search_restaurants/execute -H 'content-type: application/json' \
  -d '{"city":"Boston","cuisine":"Italian"}' | jq -r '."return value"' | jq '.[].name'
```

**3. The recipe** for `team1`:

```bash
curl -s -X POST $STORE/plugins/rossoctl-tools/recipe -H 'content-type: application/json' \
  -d '{"skill":"night-out-planner","namespace":"team1","agent":{"name":"night-out"}}' > recipe.json
jq '{ok, missing, preflight: [.preflight[] | {tool, ready, port}], env: .request.envVars}' recipe.json
```

**4. Deploy.** Wait about 30 s for autosync, until **Skills** in the console lists `night-out-planner`. Then add your model settings and send the request.

Using the API:

```bash
jq '.request.envVars += [{"name":"LLM_API_BASE","value":"<url>"},{"name":"LLM_MODEL","value":"<model>"},
                        {"name":"LLM_API_KEY","valueFrom":{"secretKeyRef":{"name":"openai-secret","key":"apikey"}}}] | .request' \
  recipe.json > agent.json
curl -s -X POST http://rossoctl-ui.localtest.me:8080/api/v1/agents -H 'content-type: application/json' \
  -H "Authorization: Bearer $TOKEN" -d @agent.json | jq .message
```

Or with the CLI: `jq -r .cli recipe.json` prints the `rossoctl agents import` command. Fill in the `LLM_*` placeholders.

Check what rossoctl created:

```bash
kubectl -n team1 get deploy night-out -o json | jq -r '.spec.template.spec.containers[0].env[] | select(.name|test("MCP_|SKILL_")) | "\(.name)=\(.value)"'
kubectl -n team1 logs deploy/night-out | grep -i -E "skill|MCP tool"
```

**5. Chat.** In the console, open the `night-out` agent's chat:

> Plan dinner for 4 in Boston tomorrow at 7pm, Italian, mid-range.

Then: *"Book the first option at 7:30 for Ada Lovelace, 555-0100, ada@example.com."* The agent asks for confirmation, then books. Then: *"What reservations do I have?"*

**6. Portability:**

```bash
curl -s -X POST $STORE/plugins/rossoctl-tools/recipe -H 'content-type: application/json' \
  -d '{"skill":"night-out-planner","namespace":"team2"}' | jq '{ok, missing}'   # missing: ["reservation-tool"]
kubectl apply -n team2 -f ~/demo/skillberry-store/plugins/skillberry-plugin-rossoctl-tools/deploy/reservation-tool.yaml
# deploy the weather tool there too (console preset); the recipe for team2 then reports ok: true
```

---

## B. One machine, no containers

This runs the real code on one machine:
- rossoctl `main` and the store, both from source;
- the two example tools as local processes;
- a [kwok](https://kwok.sigs.k8s.io/) control plane, which gives a real Kubernetes API server without kubelets.

rossoctl creates real Deployments, Services and skill ConfigMaps. With no kubelet there is no agent pod. The script fetches the skill as the init container does, and connects to the tools with `generic_agent`'s own MCP client (`langchain-mcp-adapters`), configured from the `MCP_URLS` in the Deployment rossoctl created.

### B.1 One-time setup

```bash
cd ~/demo
(cd skillberry-store && python3 -m venv .venv && source .venv/bin/activate \
   && make install-requirements ODEPS=test SKIPOPT=1 \
   && uv pip install -e "plugins/skillberry-plugin-rossoctl-tools[dev]")
(cd rossoctl/rossoctl/backend && uv sync --frozen --extra dev)
(cd rossoctl-examples/mcp/weather_tool && uv sync --frozen)
(cd rossoctl-examples/mcp/reservation_tool && uv sync --frozen)
curl -fsSL -o kwokctl https://github.com/kubernetes-sigs/kwok/releases/download/v0.7.0/kwokctl-linux-amd64 && chmod +x kwokctl
KWOK_WORKDIR=$PWD/kwok ./kwokctl create cluster --name demo --runtime binary
KWOK_WORKDIR=$PWD/kwok ./kwokctl get kubeconfig --name demo > kubeconfig
(cd rossoctl/charts/rossoctl && helm dependency build . >/dev/null && tar xzf charts/operator-chart-*.tgz -C /tmp)
KUBECONFIG=$PWD/kubeconfig kubectl apply -f /tmp/operator-chart/crds/
```

Ports used:

| Port | Used by |
|---|---|
| 8000 | the store |
| 8010 | the rossoctl backend |
| 18001 | weather-tool |
| 18002 | reservation-tool |
| 8080 | a small router for rossoctl's off-cluster tool address `<tool>.localtest.me:8080` |

### B.2 Run

```bash
cd ~/demo/skillberry-store
ROSSOCTL_REPO=~/demo/rossoctl EXAMPLES_REPO=~/demo/rossoctl-examples KUBECONFIG=~/demo/kubeconfig \
  plugins/skillberry-plugin-rossoctl-tools/tests/cluster/run-local-demo.sh
```

The output of a run is in [`sample-output.txt`](rossoctl-night-out-planner/sample-output.txt). Step 11 confirms the rossoctl checkout has no changes. Before running it again, run `kubectl delete ns team1 team2`.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `/plugins/rossoctl-tools/*` returns 404 | The plugin isn't active. `GET /plugins/` shows its status. Set `ROSSOCTL_BACKEND_URL`, and use an image with the plugin. |
| Import returns 403 | No valid credential. Set `ROSSOCTL_CLIENT_*` (§A.2), or run rossoctl without UI auth. |
| Import returns 502 for a tool | The backend can't reach the tool's MCP server. Check that the tool pod is Ready. |
| Store-side Execute fails with "unreachable … svc.cluster.local" | The store runs code in Docker mode. Set `EXECUTE_PYTHON_LOCALLY=true`. |
| The recipe says `missing` | The tool isn't deployed in that namespace. Deploy it, or use another namespace. |
| The agent ignores the tools | Check `MCP_URLS` on the Deployment, and that the image is `generic_agent`. Single-`MCP_URL` agents need `agent.mode: gateway` and the tools registered with the MCP Gateway. |
