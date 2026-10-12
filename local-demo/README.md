# Local demo: City Policy Crash-Test on one Paris quay

A minimal, fully local slice of [PLAN.md](../PLAN.md). The agent loop runs end to end
(research → hypotheses → baseline → policy test → mitigation → robustness → report) on a
real OpenStreetMap network around Hôtel de Ville. Two pieces are swapped for local stand-ins:

| PLAN.md | This demo |
|---|---|
| Tavily research | 4 canned evidence cards in `data/evidence.json` |
| Nemotron (Ultra / Super) planner on Token Factory | `StateMachinePlanner`: a deterministic state machine |
| Oracle / Sandbox / Local SUMO runners | `LocalRunner` only: SUMO subprocesses writing under `local-demo/work/` |
| Calibrated demand (routeSampler + Paris sensors) | Seeded random trips biased to the network fringe |
| Lovable UI | Console timeline + `report.md` + PNG maps |

Every simulation input and output stays inside `local-demo/`. Nothing calls a network service
at run time. The OSM extract is already committed in `data/`.

[NEBIUS.md](NEBIUS.md) explains how to move the planner and the simulations onto Nebius.

## Quickstart

```bash
cd local-demo
uv venv --python 3.12 .venv            # or: python3.12 -m venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m crashtest_demo run
```

A run takes about 10 s on an M-series Mac: 5 experiments plus 3 baselines, 3 seeds each, seeds
in parallel. The very first run in a new environment takes ~45 s of one-off setup. Results are cached in `work/results/`, so the next run is instant; pass
`--fresh` to re-simulate. Output goes to `runs/latest/`:

- `report.md`: the Policy Failure Report (verdict, numbers, maps, hypotheses, assumptions)
- `run.json`: the event stream (the same shape the UI timeline and replay files would use) plus the experiment results
- `maps/*.png`: change in cars/h per street segment vs. baseline

Other commands:

```bash
.venv/bin/python -m crashtest_demo catalogue            # the 15 experiments the agent may pick from
.venv/bin/python -m crashtest_demo sim quays:FC.M0.DH    # run one experiment (3 seeds) and print metrics
.venv/bin/python -m crashtest_demo watch quays:FC.M0.DN # watch one experiment live in sumo-gui (WATCH.md)
.venv/bin/python -m crashtest_demo run --budget 4       # tighter experiment budget
.venv/bin/python -m crashtest_demo prepare --rebuild    # rebuild the SUMO net from data/hdv.osm.xml.gz
```

## Watching a simulation live

The agent runs SUMO headless. To watch any experiment in `sumo-gui` with the exact inputs of the
measured run, use `watch`:

```bash
.venv/bin/python -m crashtest_demo watch quays:FC.M0.DN
```

On macOS this needs XQuartz. **[WATCH.md](WATCH.md)** has the setup, how to read the view, and
worked examples: baseline vs policy side by side, a mitigation that gridlocks, and high-demand
gridlock forming.

## The scenario

- **Area:** a ~1.3 × 1.1 km box around Hôtel de Ville (`BBOX` in `crashtest_demo/config.py`): the
  right-bank quays, the southern Marais, and the tips of Île de la Cité and Île Saint-Louis.
- **Policy:** close **Quai de l'Hôtel de Ville to eastbound cars from Rue de Brosse to Pont
  Louis-Philippe**; westbound stays open. This is a scaled-down version of PLAN.md's
  "close the upper quays". In an area this small, closing both directions leaves the
  eastbound through traffic no detour, and SUMO gridlocks at any demand level.
- **Rue de Rivoli** is closed to through cars in every scenario, baseline included. It's
  tagged `motor_vehicle=destination;permit` in OSM and has been bus/taxi/bike-only since 2020.
- **Catalogue** (`crashtest_demo/scenarios.py`): `quays:{policy}.{mitigation}.{demand}`
  - policy `BASE` | `FC` (the closure)
  - mitigation `M0` (none) | `F1` / `F2` (modal filter on the 1st / 2nd ranked detour street) | `F12` (both)
  - demand `DL` / `DN` / `DH` = ×0.85 / ×1.0 / ×1.15 of 1,200 car trips/h. The lower levels are seeded
    subsets of the higher ones, so comparisons stay paired.
- **Mitigation sites are chosen by a rule, not by looking at results**
  (`scenarios.screen_sites`). For every fringe-to-fringe trip whose shortest path uses the
  closed segment, it finds the new shortest path and counts the residential streets added.
  This run picks Rue François Miron (F1) and Rue de Brosse (F2).
- **Constraints** (`crashtest_demo/metrics.py`, defaults from PLAN.md §7):
  - G1: the target segment loses ≥ 70% of its traffic.
  - C1: a residential street rises by > 30% **and** > 100 veh/h.
  - C2: network delay rises by > 10% **and** > 20 veh·h.
  - C3: gridlock (teleports ≥ max(10, 0.5% of inserted), or ≥ 2% of trips unfinished).
  - A violation is *robust* if it appears in ≥ 2 of 3 seeds.

## The state machine (stand-in for the LLM)

`crashtest_demo/agent.py` splits the work exactly as PLAN.md §8 does:

- **`StateMachinePlanner`** makes the judgement calls an LLM would make: writing hypotheses
  (Nemotron Ultra's job) and choosing the next step (Nemotron Super's job). It returns a
  `Decision(action, experiment_id, next_phase, hypothesis_ids, rationale)`. That's the same
  JSON shape the LLM would be asked for.
- **`Agent`** enforces the rules no planner can override:
  - allowed phase transitions
  - experiment IDs must be untested catalogue entries
  - the budget
  - the deterministic verdicts: constraint checks, hypothesis status, mitigation verification

```
RESEARCH → HYPOTHESES → BASELINE → POLICY_TEST ─┬─ robust spillover ─→ MITIGATION ─┐
                                                └─ none ────────────────────────────┴→ ROBUSTNESS → REPORT
```

| Phase | What the state machine decides |
|---|---|
| POLICY_TEST | Run `FC.M0.DN`. If any residential street has a robust C1 violation, go to MITIGATION; otherwise ROBUSTNESS |
| MITIGATION | Try the filter whose site is the worst-hit street first, then the other. Try `F12` only if the single filters merely pushed traffic onto each other (no gridlock). Leave once one is **verified** (target spillover gone, G1 still met, no new major/critical violation) or nothing is left |
| ROBUSTNESS | Re-test the verified mitigation (or the bare policy) at high demand (adverse corner), then low demand |
| REPORT | Stop |

Baselines are run automatically when an experiment needs them and don't count against the budget.

## What the current run finds

From `runs/latest/report.md` (3 seeds; numbers are means):

- **The policy meets its goal:** eastbound traffic on the closed segment drops from 171 to 0 cars/h.
- **But it pushes through traffic into the Marais (robust in 3/3 seeds):**
  - Rue de Brosse: 16 → 186 cars/h.
  - Rue François Miron: 44 → 213.
  - Rue de Fourcy: 48 → 217.
- **Both modal filters remove that spillover but gridlock the area**, because eastbound traffic
  has no other local route. Each filter causes 136–165 teleports and raises delay from 31 to 140 veh·h,
  so both are rejected: the "whack-a-mole" failure PLAN.md describes.
- **At high demand the policy alone also tips into gridlock** (critical).
- **Verdict:** fails. No mitigation in the catalogue was verified within budget. A real study
  would look at diverting traffic further upstream, beyond this box.

Treat these as results of a toy model, not predictions (see limitations).

## Limitations (on purpose)

- **Tiny area:** detours outside the box are invisible, which overstates local spillover.
- **Demand is not calibrated:** 1,200 random trips/h is about half of what the sensor counts in PLAN.md
  §7 imply. The box can't carry more once the quay is cut.
- **Only private cars are simulated:** no taxis, buses, bikes or pedestrians. No evaporation and no mode shift.
- **Evidence cards are hand-written paraphrases, not verbatim quotes:** treat them as placeholders
  until Tavily replaces them.
- **No routing-assumption dimension and no seeds 4–5 confirmation step** (PLAN.md has both).

## Files

```
local-demo/
  crashtest_demo/
    config.py      paths, bbox, policy target, seeds
    network.py     Overpass download → netconvert → streets.json (street → edges, class, residential)
    scenarios.py   catalogue, netconvert patches per scenario, rule-based mitigation-site screening
    demand.py      seeded randomTrips, thinned per demand level
    runner.py      SimRunner protocol + LocalRunner (SUMO subprocess, cached per experiment + seed)
    metrics.py     paired deltas, constraints G1/C1/C2/C3, robustness across seeds
    agent.py       Planner protocol, StateMachinePlanner, Agent loop, events
    report.py      Policy Failure Report (markdown)
    plot.py        Δ-volume map PNG
    __main__.py    CLI
  data/            hdv.osm.xml.gz (OSM roads), net.net.xml.gz, streets.json, sites.json, evidence.json
  work/            SUMO scratch: scenario nets, trips, raw outputs (gitignored, safe to delete)
  runs/            agent outputs
```

Refreshing the OSM extract (`network.fetch_osm(force=True)`) uses the public Overpass API,
which is often overloaded (HTTP 504). The committed `data/hdv.osm.xml.gz` avoids that dependency.

Data © OpenStreetMap contributors (ODbL). Simulation: [Eclipse SUMO](https://eclipse.dev/sumo/) 1.28.
