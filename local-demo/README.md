# City Policy Crash-Test: one Paris quay

An AI agent crash-tests a traffic policy before it ships. **Nemotron** (Token Factory) writes
hypotheses and picks each next experiment; **SUMO** simulates it on the real OpenStreetMap network
around Hôtel de Ville; Python checks every number and writes the report.

**Current scenario** ([scenario.json](scenario.json)): close Quai de l'Hôtel de Ville in Paris to eastbound
cars (Rue de Brosse → Pont Louis-Philippe).

**New here?** [GUIDE.md](GUIDE.md) explains how to read a run. [human.md](human.md) shows how to change
the scenario; [AGENTS.md](AGENTS.md) is the same for coding agents.

## Run it

```bash
cp .env.example .env          # then fill in NEBIUS_API_KEY and NEBIUS_PROJECT_ID
python3 crashtest.py          # one full run in the cloud: SUMO in a Sandbox + Nemotron, ~1.5 min
python3 cloud_minimal.py      # minimal cloud example: toy grid, SUMO + Nemotron judge, ~10 s
```

`crashtest.py` builds its Sandboxes image the first time and again after code, data or scenario
changes (a few minutes). `cloud_minimal.py` is a ~150-line, self-contained version of the same mechanism.

Results land in `runs/latest/`: `report.md` (verdict, numbers, maps), `run.json` (event timeline), `maps/*.png`.
Nemotron runs also refresh the web app's recorded run, `lovable/public/demo/latest.json`.

| Option | What it does |
|---|---|
| `--sumo auto` (default) | Token Factory Sandbox if your project has access, otherwise local SUMO |
| `--sumo sandbox` | Whole run inside a Sandbox. Needs only Python 3; the image is built once (a few minutes) |
| `--sumo local` | SUMO on this machine. Needs the venv below |
| `--planner rules` | No LLM: deterministic rule-based planner |
| `--budget N` | Max policy experiments (default 6; baselines are free) |

Local SUMO setup (once):

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
```

## How a run works

1. **Research:** evidence cards from `scenario.json` (canned until Tavily is wired in).
2. **Hypotheses:** Nemotron 3 Ultra turns the evidence into testable claims.
3. **Experiments:** Nemotron 3 Super picks the next one from a fixed 15-entry catalogue
   (policy × modal-filter mitigation × low/normal/high demand), within budget. Each runs in SUMO with 3 seeds.
4. **Checks:** Python flags goal G1 (target traffic −70%) and violations: C1 residential spillover,
   C2 network delay, C3 gridlock. Violations count only if robust (≥2 of 3 seeds).
5. **Report:** templated; every number comes from SUMO, never from the LLM.

Guardrails: the LLM only ever chooses from untested catalogue IDs and allowed phases (JSON schema),
and Python re-validates every choice. Invalid or failed calls fall back to the rule-based planner, and
the run records it (`fallback_used` events, report header).

## Latest result

The policy meets its goal (171 → 0 cars/h on the quay), but pushes traffic into the Marais in all
3 seeds: Rue de Brosse 16 → 186, Rue François Miron 44 → 213, Rue de Fourcy 48 → 217 cars/h.
Both modal filters and their combination remove that spillover but gridlock the area. **Verdict: fails.**
This is a toy model: small area, uncalibrated demand, cars only.

## Change the scenario

Edit [scenario.json](scenario.json) (area, street, direction, demand, thresholds, evidence) and run
`python3 crashtest.py`. It rebuilds the network for the new case automatically. Details: [human.md](human.md).

## Web app (Lovable)

`lovable/` mirrors a Lovable project's root. Copy its contents into the project (same paths):

```
lovable/
  CRASHTEST_PROMPT.md                       paste into Lovable chat: what to build
  src/lib/crashtest.ts                      types + loadRecordedRun / replayRun / startLiveRun
  supabase/functions/crashtest-run/index.ts edge function: live run in a Token Factory Sandbox
  public/demo/latest.json                   a recorded real run (written by crashtest.py)
  AGENTS.md                                 rules for coding agents working on the app
```

1. Connect the Lovable project to GitHub, copy the files in, push. (Or attach them in Lovable chat.)
2. Paste `CRASHTEST_PROMPT.md` into Lovable chat. Add the secrets `NEBIUS_API_KEY` and
   `NEBIUS_PROJECT_ID` in Lovable Cloud when asked, and ask Lovable to deploy the `crashtest-run` function.
3. "Run live" starts a run on the sandbox image tagged `crashtest-sumo:latest`. It already exists;
   `python3 crashtest.py` refreshes it after changes. If a live run fails, the app shows the recorded run.

The app takes every label from the recorded run, so a new scenario only needs a new `latest.json`:
run `python3 crashtest.py`, then copy `public/demo/latest.json` into the Lovable project again.

## Files

```
scenario.json         the case: area, policy, demand, thresholds, evidence cards
crashtest.py          the one script: .env → Sandbox or local run → runs/latest/
cloud_minimal.py      minimal self-contained cloud example (toy grid, SUMO + Nemotron judge)
crashtest_demo/       engine: agent.py (loop + rules), nemotron.py (LLM planner), llm.py (Token Factory),
                      scenarios.py, runner.py (SUMO), metrics.py, report.py, plot.py
lovable/              files for the Lovable web app (see above)
data/                 OSM extract, SUMO network, streets, mitigation sites (built from scenario.json)
GUIDE.md              how to read a run (start here)
human.md / AGENTS.md  how to change the scenario or the demo (for people / for coding agents)
WATCH.md              watch any experiment live in sumo-gui
```

Dev commands: `python -m crashtest_demo {prepare | streets [NAME] | catalogue | sim ID | watch ID | run}` (from the venv).

Data © OpenStreetMap contributors (ODbL). Simulation: [Eclipse SUMO](https://eclipse.dev/sumo/) 1.28.
