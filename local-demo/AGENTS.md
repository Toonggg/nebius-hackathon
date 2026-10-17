# AGENTS.md: City Policy Crash-Test demo

Instructions for coding agents working in `local-demo/`. Humans: see `human.md`.

## What this is

An agent crash-tests one city traffic policy: Nemotron (Token Factory) writes hypotheses and picks
experiments, SUMO simulates them, Python judges the results and writes a report. A Lovable web app
(`lovable/`) shows a recorded run or starts a live one in a Token Factory Sandbox.

## Hard rules

1. **`scenario.json` is the single source of truth for the case** (area, street, policy, closures,
   demand, check thresholds, evidence, labels). Never hard-code a city, street or policy name in
   Python, TypeScript or the UI prompt; read it from the scenario (`config.SCENARIO` in Python,
   `bundle.scenario` in the web app).
2. **Numbers come only from SUMO.** The LLM chooses experiments; it never supplies figures for the
   report or verdicts.
3. **Secrets:** keys live only in `.env` (gitignored) and in Lovable Cloud secrets. Never write a key
   into any other file, command line, log or commit.
4. Don't hand-edit generated files: `data/*` (except via `prepare`), `runs/latest/*`,
   `lovable/public/demo/latest.json`. Regenerate them with the commands below.

## Setup and commands (run in `local-demo/`)

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
python3 crashtest.py                       # full run: Nemotron + SUMO (~30-60 s, ~26k LLM tokens)
python3 crashtest.py --planner rules       # same without the LLM: free, deterministic; use while iterating
.venv/bin/python -m crashtest_demo prepare           # rebuild data/ for scenario.json (crashtest.py does this automatically)
.venv/bin/python -m crashtest_demo streets           # longest streets in the network (name, class)
.venv/bin/python -m crashtest_demo streets "<name>"  # one street's edges and the streets crossing each
.venv/bin/python -m crashtest_demo sim <prefix>:FC.M0.DN   # one experiment, 3 seeds, metrics printed
.venv/bin/python -m crashtest_demo catalogue         # the 15 experiment IDs
```

`crashtest.py` runs SUMO in a Token Factory Sandbox when the project has access (`--sumo sandbox`),
otherwise locally. Every run writes `runs/latest/`; only Nemotron runs also replace the web app's
recorded run `lovable/public/demo/latest.json` (`--planner rules` runs leave it alone).

## Task: change the scenario

Edit only `scenario.json`, then verify. Fields (`_help` keys explain each; they are ignored by code):

| Field | How to choose it |
|---|---|
| `bbox` | `[west, south, east, north]`, ~1-2 km across. Changing it re-downloads roads from OpenStreetMap (Overpass is often busy: rerun on failure). |
| `policy.street`, `policy.from`, `policy.to` | Exact names from `streets` / `streets "<street>"`. `from` and `to` must cross `street`; cars can no longer drive from `from` to `to` along it. |
| `policy.direction` | Label for that from→to direction ("northbound", "towards the river", ...). |
| `always_closed_to_cars` | Exact street names closed to cars in every scenario (bus-only streets), or `[]`. Plus `always_closed_reason`. |
| `residential_road_types` | OSM `highway` types that count as residential. Usually keep the default. |
| `demand.trips_per_hour` | Tune last (see verification). `low` / `high` scale it. |
| `checks` | Thresholds for G1/C1/C2. Keep the defaults unless asked. |
| `id`, `city`, `area_name`, `experiment_prefix` | Labels; `id` and prefix: short, lowercase, `[a-z0-9-]`. |
| `evidence` | 3-6 cards `{id: "E1".., source, claim, tags}` about the policy type and place. Real sources only; paraphrase, and say so in `_evidence_help`. Don't invent numbers. |

Steps:

1. If the area changes: set `bbox`, run `prepare`, then use `streets` to pick the policy street and
   its `from` / `to` cross streets.
2. Set the remaining fields. Run `python3 crashtest.py --planner rules` (no LLM cost).
3. **Verify** (all must hold; otherwise fix and rerun):
   - `prepare` printed `Policy target: ... -> edges [...]` and two mitigation sites F1/F2.
   - The baseline isn't gridlocked: the `simulated <prefix>:BASE...` lines show `teleports 0` (or
     near 0). If not, lower `demand.trips_per_hour`.
   - The policy test (`<prefix>:FC.M0.DN`) shows a real effect: the target segment drops (G1).
     If nothing changes anywhere, raise demand; if everything gridlocks, lower it.
4. Run `python3 crashtest.py` once with Nemotron for the final result.
5. Update the prose that describes the current case (no code does this):
   - `README.md`: the "Policy tested" line and the "Latest result" section.
   - `GUIDE.md`: "The question" and "What the current run says". Take every number from
     `runs/latest/report.md`.
   - `WATCH.md`: its examples name Paris streets and experiments. Update them or mark them as Paris examples.
   - `grep -ri "<old city>\|<old street>" --include=*.md .` should then find nothing stale.
6. Live web runs: once Sandboxes access exists, run `python3 crashtest.py --sumo sandbox`. It rebuilds the
   sandbox image (code/data/scenario changed) and moves the `crashtest-sumo:latest` tag the web app uses.
7. Tell the human to copy `lovable/public/demo/latest.json` into the Lovable project. It's the only
   web-app file that changes with the scenario.

### Errors and fixes

| Message | Fix |
|---|---|
| `No <street> edges between (...)` | `from`/`to` don't both cross `street`, or are in the wrong order for any drivable direction. Check `streets "<street>"`; try swapping them. |
| `Only N residential street(s) carry detours ...` | Too few residential detours for F1/F2: enlarge `bbox` or pick another street. |
| `scenario.json changed since data/ was built` | Run `prepare` (or `crashtest.py`). |
| `All Overpass mirrors failed` | Wait a minute and rerun `prepare`. |
| `Street '<name>' (scenario.json) is not in the network` | Misspelled or outside `bbox`. Copy the exact name from `streets`. |

## Task: change the demo's structure

Only when asked to go beyond a new scenario. Where things live:

| Change | Files |
|---|---|
| New policy type (e.g. close both directions, speed limits, zones) | `scenarios.py` (`Scenario`, `catalogue`, `closed_edges`, `describe`), `scenario.json` schema + `config.py`, rules planner in `agent.py`, prompt/schema in `nemotron.py` |
| New mitigation type | `scenarios.py` (`MITIGATIONS`, `closed_edges`, `screen_sites`), `agent.py` (`_rank_mitigations`), `nemotron.py` (`SYSTEM`, phase guide) |
| New check | `metrics.py` (`_check_seed`, `CONSTRAINTS`), `scenario.json` `checks`, `report.py`, check list in `nemotron.py` |
| Agent loop / phases | `agent.py` (`Phase`, `TRANSITIONS`, `Agent.run`); keep Python as the judge of every verdict |
| LLM models / prompts | `llm.py` (`MODEL_*`, env overrides), `nemotron.py` |
| Report / maps | `report.py`, `plot.py` |
| Run orchestration, sandbox image | `crashtest.py` (`IMAGE_FILES`: everything the sandbox needs) |

Contracts to keep in sync:
- **Bundle** (what a run returns): `crashtest_demo/__main__.py` writes `{scenario, run, report_md,
  maps_png_base64}`; `lovable/src/lib/crashtest.ts` declares it (`Bundle`, `Scenario`, `RunEvent`,
  `EVENT_TYPES`). Change both together. Add new event types to `EVENT_TYPES` and to
  `lovable/CRASHTEST_PROMPT.md` if the UI should show them.
- **`--bundle` protocol:** stdout = one JSON bundle; stderr = one JSON event per line with a `msg`.
  `crashtest.py` and `lovable/supabase/functions/crashtest-run/index.ts` both parse it.
- After any change: `python3 crashtest.py --planner rules` must still finish. For a refactor, compare
  `runs/latest/run.json` before and after: experiments and events (ignoring `t`, `runtime_s`) should
  be identical.

## The `lovable/` directory

It mirrors a Lovable project root and is copied into that project as-is:

| File | Role | Changes when |
|---|---|---|
| `CRASHTEST_PROMPT.md` | One-time build prompt pasted into Lovable | The UI design changes |
| `src/lib/crashtest.ts` | Types + `loadRecordedRun`, `replayRun`, `startLiveRun`, `mapSrc` | The bundle/event contract changes |
| `supabase/functions/crashtest-run/index.ts` | Edge function: spawns and polls a sandbox run | The sandbox command or protocol changes |
| `public/demo/latest.json` | Recorded run (a `Bundle`), written by `crashtest.py` | Every run, including scenario changes |
| `AGENTS.md` | Rules for agents working inside the Lovable project | Rarely |

The UI is scenario-agnostic by design: a new scenario needs only a new `latest.json` (and, for live
runs, a rebuilt sandbox image). Check type safety after editing the TypeScript:
`deno check lovable/supabase/functions/crashtest-run/index.ts`.
