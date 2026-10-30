# SimTraffick: City Policy Crash-Test

**Does your traffic policy fix the street, or just move the traffic elsewhere?**

SimTraffick is an AI agent that crash-tests a city traffic policy in simulation before it reaches the
street. **NVIDIA Nemotron** on **Nebius Token Factory** forms hypotheses and chooses experiments.
**SUMO** simulates every car on the real OpenStreetMap network, inside **Token Factory Sandboxes**.
Python checks every number and writes a Policy Failure Report.

- **Live demo:** https://city-policy-crash-test.lovable.app/ (choose *Recorded sample*, or *Live agent* for a real run)
- **Demo video:** _add YouTube link_
- **Track:** Best Apps and Agents · **Licence:** [MIT](LICENSE)

## Why

Cities close roads, add bus lanes and create car-free zones. Many of these succeed on the street
they target, but push traffic onto nearby residential streets. Traffic simulators can show this,
but someone still has to decide what to test, read the results, and check whether a fix holds.
SimTraffick does that loop automatically, and states its verdict and its uncertainty openly.

## How it works

```
scenario.json ─► Nemotron 3 Ultra: hypotheses from evidence
                      │
                      ▼
          ┌─► Nemotron 3 Super picks the next experiment (JSON schema: only valid, untested IDs)
          │           │
          │           ▼
          │   SUMO simulates it, 3 random seeds      ← Token Factory Sandbox
          │           │
          │           ▼
          └── Python measures: goal met? spillover? delay? gridlock?
                      │  (repeats within a budget of 6 experiments)
                      ▼
              Policy Failure Report + maps ─► web app (Lovable)
```

1. **Hypotheses:** Nemotron 3 Ultra turns evidence cards into testable claims, e.g. "traffic will spill
   onto Rue de Brosse".
2. **Experiments:** Nemotron 3 Super picks from a fixed catalogue: the policy, modal filters on the most-used
   detour streets, and low/normal/high demand. It sees only text summaries of what it has measured so far.
3. **Checks (Python, not the LLM):** G1 the target street gets quieter; C1 a residential street gains
   +30% and +100 cars/h; C2 network delay +10%; C3 gridlock. A problem counts only if it holds in at least
   2 of 3 seeds. A fix is verified only if it removes the spillover without causing a new problem.
4. **Report:** every number comes from SUMO. The LLM chooses what to test and never supplies a figure.

**Guardrails:** each LLM call gets a JSON schema built from the current state, and Python re-checks every
choice. An invalid or failed call falls back to a rule-based planner, and the run records it.

## Result: Paris, Quai de l'Hôtel de Ville

Policy: close the quay to eastbound cars between Rue de Brosse and Pont Louis-Philippe.

- **Goal met:** the closed stretch drops from 171 to 0 cars/h.
- **But traffic moves into the Marais** (all 3 seeds): Rue de Brosse 16 → 186, Rue François Miron 44 → 213,
  Rue de Fourcy 48 → 217 cars/h.
- **Every fix fails:** filters on one detour street, the other, or both remove the spillover but gridlock the area.
- **Verdict: fails as proposed.** A full cloud run takes under 2 minutes (about 40 s in the latest run): 9 Nemotron
  calls, ~26k tokens.

This is a deliberately small model (a ~1.3 × 1.1 km area, synthetic demand, cars only), not a forecast.

## Run it

Needs Python 3 and a Nebius Token Factory API key with Sandboxes access. No local SUMO is required.

```bash
git clone https://github.com/Toonggg/nebius-hackathon && cd nebius-hackathon/local-demo
cp .env.example .env          # fill in NEBIUS_API_KEY and NEBIUS_PROJECT_ID
python3 cloud_crashtest.py    # full agent run, all in the cloud (first run builds the SUMO image, ~1 min)
python3 cloud_minimal.py      # 150-line example: SUMO + a Nemotron judge in one sandbox call, ~10 s
```

Results land in `local-demo/runs/latest/` (`report.md`, `run.json`, maps). `python3 crashtest.py` does the same
with the code built into the sandbox image (the image the web app's live mode uses), and `--sumo local`
runs SUMO on your machine instead (setup in [local-demo/README.md](local-demo/README.md)).
`--planner rules` runs without the LLM.

**Change the case:** edit [`local-demo/scenario.json`](local-demo/scenario.json): the area, the street and
direction, always-closed streets, demand, thresholds, and evidence. Then run again; the road network is
rebuilt automatically. [human.md](local-demo/human.md) explains this for people, and
[AGENTS.md](local-demo/AGENTS.md) step by step for coding agents.

## Nebius and NVIDIA usage

| What | Where |
|---|---|
| **Nemotron 3 Ultra** (`nvidia/Nemotron-3-Ultra-550b-a55b`) | Hypotheses: one reasoning-heavy call per run (`crashtest_demo/nemotron.py`) |
| **Nemotron 3 Super** (`nvidia/nemotron-3-super-120b-a12b`) | Every next-experiment decision, ~8 fast calls per run, with structured JSON output; also the judge in `cloud_minimal.py` |
| **Token Factory inference** | OpenAI-compatible API, called with the standard library only (`crashtest_demo/llm.py`) |
| **Token Factory Sandboxes** | SUMO and the whole agent loop run in an isolated microVM per run. The image is built once and tagged by a content hash; each run uploads the code and scenario. The web app's *Live agent* mode starts the same sandbox run through a Lovable Cloud edge function |

**How Token Factory helped:**
- **Sandboxes replaced a server.** We first planned an always-on VM. Sandboxes gave us pay-per-run SUMO
  with the same API key, and cloud results are identical to local runs.
- **One API for both.** Inference and Sandboxes use the same key, so the LLM is called from inside the
  sandbox and a whole run is a single API call.
- **Plug-in models.** The OpenAI-compatible API and JSON-schema output let Nemotron replace the
  rule-based planner without changing the agent loop.

## Repository

```
local-demo/
  scenario.json        the case (one file)
  cloud_crashtest.py   full run, cloud only        crashtest.py   full run, sandbox or local
  cloud_minimal.py     minimal cloud example
  crashtest_demo/      engine: agent loop, Nemotron planner, SUMO runner, checks, report, maps
  lovable/             web app files: data layer, edge function, recorded run, build prompt
  data/                OpenStreetMap extract and SUMO network for the scenario
  GUIDE.md             how to read a run
PLAN.md                the original design document
```

## Limitations

- A small study area: detours outside it are invisible, which overstates local spillover.
- Demand is synthetic, not calibrated to Paris traffic counts. Only cars are simulated.
- The evidence cards are hand-written placeholders; live research (e.g. Tavily) is not wired in yet.
- One policy type: closing one stretch of one street in one direction, with modal filters as fixes.

## Credits

Map data © OpenStreetMap contributors (ODbL). Simulation: [Eclipse SUMO](https://eclipse.dev/sumo/) 1.28.
Models: NVIDIA Nemotron on Nebius Token Factory. Web app built with Lovable. MIT licence.
