# How to read the crash test

This guide uses the current scenario ([scenario.json](scenario.json)), Paris, as its example.

## The question

Paris closes **Quai de l'Hôtel de Ville to eastbound cars** (Rue de Brosse → Pont Louis-Philippe).
The quay gets quieter, but where does that traffic go? If it cuts through small residential streets
in the Marais, the policy hasn't solved the problem, just moved it. The crash test finds that out
in simulation before the bollards go in.

## Who does what

| Step | Done by | Output |
|---|---|---|
| Read the evidence (cards about past road closures) | `scenario.json` for now | evidence cards |
| Write hypotheses ("traffic will spill onto Rue de Brosse") | **Nemotron 3 Ultra** | 3–7 testable claims |
| Choose the next experiment | **Nemotron 3 Super** | one pick from a fixed list, with a reason |
| Simulate it | **SUMO**: every car for one rush hour, 3 random seeds | traffic per street |
| Judge it | **Python**: fixed rules, below | violations, verdicts |
| Write the report | **Python** template | `report.md` |

The AI only chooses *what to test*. Every number comes from SUMO, and every verdict from Python.

## Experiment IDs

`quays:FC.F1.DH` = **policy** . **mitigation** . **demand**

| Part | Values |
|---|---|
| policy | `BASE` today's streets (the baseline) · `FC` the closure |
| mitigation | `M0` none · `F1` modal filter (street closed to through cars) on the detour street most drivers would use (here Rue François Miron) · `F2` same on the second (here Rue de Brosse) · `F12` both |
| demand | `DL` low (−15%) · `DN` normal (1,200 car trips/h) · `DH` high (+15%) |

Each experiment is compared with the baseline at the same demand. The agent may run up to 6
(the budget); baselines don't count.

## The checks

| Code | Meaning | Rule |
|---|---|---|
| **G1** | Goal: did the quay get quieter? | traffic on the closed segment falls ≥ 70% |
| **C1** | Spillover onto a residential street | +30% **and** +100 cars/h |
| **C2** | The whole area got slower | total delay +10% **and** +20 vehicle-hours |
| **C3** | Gridlock | cars stuck long enough that SUMO removes them ("teleports"), or trips can't finish |

A problem only counts if it's **robust**, meaning it shows up in at least 2 of the 3 seeds.
Severity: *minor* (just over the line), *major* (1.5× over), *critical* (gridlock).
A **mitigation is verified** only if it removes the spillover, keeps G1, and causes no new
major or critical problem.

## Reading the output

- **Terminal:** the run as a timeline: `== PHASE ==` headers, `llm` lines (model, seconds, tokens),
  `decision` lines (what Nemotron chose and why), `simulated` lines, and `!` lines for problems found.
- **`runs/latest/report.md`:** verdict first, then each experiment with its numbers and map, the
  mitigations tried, and the hypotheses marked supported or refuted.
- **Maps** (`runs/latest/maps/`): change in cars/h per street vs the baseline. **Red = more
  traffic, blue = less**, thicker = bigger change. Black dashes = the closed segment, grey dots =
  Rue de Rivoli (closed to cars in every scenario). Boxes label the streets with spillover.
  A red "GRIDLOCK" banner means low numbers are jams, not quiet streets.

## What the current run says

1. **The goal is met:** the closed segment drops from 171 to 0 cars/h.
2. **But traffic moves into the Marais** (all 3 seeds): Rue de Brosse 16 → 186, Rue François Miron
   44 → 213, Rue de Fourcy 48 → 217 cars/h. That's 4–12× more traffic on streets meant for residents.
3. **Every fix fails:** filtering one detour street, the other, or both removes the spillover but
   gridlocks the area. In this small box the eastbound traffic has no other way out.
4. **At high demand the policy alone gridlocks too.**

**Verdict: fails as proposed.** A real study would divert traffic further upstream, outside this area.

## How far to trust it

This is a demonstration, not a forecast:
- The area is small (~1.3 × 1.1 km). Detours outside it are invisible, which overstates local spillover.
- Demand is random trips, not calibrated to real Paris traffic counts.
- Only cars are simulated: no buses, bikes or pedestrians, and nobody switches to transit or stays home.
- The evidence cards are hand-written placeholders until live research (Tavily) is added.
