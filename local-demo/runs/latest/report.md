# Policy Failure Report (local demo)

**Policy:** Quai de l'Hôtel de Ville from Rue de Brosse to Pont Louis-Philippe closed to eastbound cars (westbound stays open).

**Verdict:** FAILS (spillover on Rue de Brosse, spillover on Rue François Miron, spillover on Rue de Fourcy). No mitigation in the catalogue was verified within budget.

Planner: `state-machine` (stand-in for Nemotron) · Runner: `local` SUMO · Budget: 5/6 experiments · Seeds per experiment: 3

## What we found

### `quays:FC.M0.DN`: Quai de l'Hôtel de Ville from Rue de Brosse to Pont Louis-Philippe closed to eastbound cars, normal demand

- Goal G1 (target segment −70%): met (171 → 0 cars/h)
- Delay: 31 → 50 veh·h; teleports 0; unfinished trips 0
- ⚠️ major: **Rue de Brosse**: 16 → 186 cars/h (+171, +341%; +159…+192 across seeds)
- ⚠️ major: **Rue François Miron**: 44 → 213 cars/h (+169, +339%; +158…+190 across seeds)
- ⚠️ major: **Rue de Fourcy**: 48 → 217 cars/h (+169, +333%; +157…+186 across seeds)

![quays:FC.M0.DN](maps/quays_FC_M0_DN.png)

### `quays:FC.F2.DN`: Quai de l'Hôtel de Ville from Rue de Brosse to Pont Louis-Philippe closed to eastbound cars, modal filter on Rue de Brosse, normal demand

- Goal G1 (target segment −70%): met (171 → 0 cars/h)
- Delay: 31 → 140 veh·h; teleports 136; unfinished trips 100
- ⚠️ critical: **Gridlock**: 136 teleports on average (jammed vehicles SUMO had to remove)
- ⚠️ major: **Network delay**: 31 → 140 veh·h (+344%)

![quays:FC.F2.DN](maps/quays_FC_F2_DN.png)

### `quays:FC.F1.DN`: Quai de l'Hôtel de Ville from Rue de Brosse to Pont Louis-Philippe closed to eastbound cars, modal filter on Rue François Miron, normal demand

- Goal G1 (target segment −70%): met (171 → 0 cars/h)
- Delay: 31 → 140 veh·h; teleports 165; unfinished trips 97
- ⚠️ critical: **Gridlock**: 165 teleports on average (jammed vehicles SUMO had to remove)
- ⚠️ major: **Network delay**: 31 → 140 veh·h (+345%)

![quays:FC.F1.DN](maps/quays_FC_F1_DN.png)

### `quays:FC.M0.DH`: Quai de l'Hôtel de Ville from Rue de Brosse to Pont Louis-Philippe closed to eastbound cars, high demand

- Goal G1 (target segment −70%): met (196 → 0 cars/h)
- Delay: 38 → 123 veh·h; teleports 31; unfinished trips 84
- ⚠️ critical: **Gridlock**: 31 teleports on average (jammed vehicles SUMO had to remove)
- ⚠️ major: **Rue de Brosse**: 18 → 212 cars/h (+194, +388%; +183…+216 across seeds)
- ⚠️ major: **Rue François Miron**: 49 → 235 cars/h (+185, +360%; +175…+197 across seeds)
- ⚠️ major: **Rue de Fourcy**: 54 → 228 cars/h (+174, +323%; +162…+181 across seeds)
- ⚠️ major: **Network delay**: 38 → 123 veh·h (+223%)

### `quays:FC.M0.DL`: Quai de l'Hôtel de Ville from Rue de Brosse to Pont Louis-Philippe closed to eastbound cars, low demand

- Goal G1 (target segment −70%): met (149 → 0 cars/h)
- Delay: 27 → 31 veh·h; teleports 0; unfinished trips 0
- ⚠️ minor: **Rue François Miron**: 38 → 187 cars/h (+149, +298%; +140…+165 across seeds)
- ⚠️ minor: **Rue de Brosse**: 12 → 161 cars/h (+149, +298%; +141…+164 across seeds)
- ⚠️ minor: **Rue de Fourcy**: 42 → 190 cars/h (+148, +296%; +140…+161 across seeds)

## Mitigations tried

| Mitigation | Verdict | Still violated | New violations |
|---|---|---|---|
| modal filter on Rue de Brosse | ❌ rejected | — | C3, C2 |
| modal filter on Rue François Miron | ❌ rejected | — | C3, C2 |

## Hypotheses

| ID | Hypothesis | Settled by | Evidence | Status |
|---|---|---|---|---|
| H1 | Closing Quai de l'Hôtel de Ville from Rue de Brosse to Pont Louis-Philippe to eastbound cars removes at least 70% of the car traffic on that segment. | `quays:FC.M0.DN` | — | supported |
| H2 | Displaced through traffic spills onto Rue François Miron, the street most shortest detours use. | `quays:FC.M0.DN` | E2, E3, E4 | supported |
| H3 | Displaced through traffic spills onto Rue de Brosse. | `quays:FC.M0.DN` | E2, E3, E4 | supported |
| H4 | Total delay in the area grows past the network-delay limit, i.e. traffic does not simply evaporate. | `quays:FC.M0.DN` | E1 | refuted |
| H5 | At high demand the closure tips the area into gridlock. | `quays:FC.M0.DH` | E2 | supported |
| H6 | A modal filter on Rue François Miron removes its spillover without creating a new failure elsewhere. | `quays:FC.F1.DN` | E3 | refuted |

## Evidence (canned; no Tavily call in the local demo)

- **[E1]** When road capacity is removed, part of the traffic does not reappear elsewhere ('traffic evaporation'), but the share varies widely from case to case. — _Cairns, Hass-Klau & Goodwin, 'Traffic Impact of Highway Capacity Reductions: Assessment of the Evidence' (Landor, 1998)_
- **[E2]** After the lower quays closed, monitoring reported traffic shifting onto nearby parallel routes, including the upper quays, alongside a debate about how much traffic evaporated. — _Evaluations of the 2016 closure of the Voie Georges-Pompidou (Paris right-bank lower quays)_
- **[E3]** The effect of filtering streets on surrounding roads differs from site to site, so displacement onto other streets has to be checked locally rather than assumed away. — _Evaluations of London Low Traffic Neighbourhoods (e.g. Goodman et al., 2021)_
- **[E4]** Residential streets have a limited 'environmental capacity': beyond a certain traffic level, living conditions degrade even if the street can physically carry more vehicles. — _Buchanan, 'Traffic in Towns' (HMSO, 1963)_

## Assumptions and limitations

- Study area is a ~1.3 × 1.1 km box around Hôtel de Ville (bbox (2.346, 48.8515, 2.364, 48.861)); detours outside it are invisible to the model, which overstates local spillover.
- Demand is synthetic: 1200 random car trips/h at normal demand (×0.85 / ×1.15 for low / high), biased to the network fringe. It is **not** calibrated to the Paris sensor counts (PLAN.md §7 does that with routeSampler).
- Rue de Rivoli is closed to through cars in every scenario (OSM: `motor_vehicle=destination;permit`). Buses, taxis, bikes and pedestrians are not simulated.
- Half of the drivers re-route every 2 minutes; nobody changes mode or time of travel, and no traffic evaporates (E1 suggests some would).
- A street's volume is its busiest link. A violation is *robust* if it appears in at least 2 of 3 seeds.
- Untested catalogue entries (7): `quays:FC.F1.DL`, `quays:FC.F1.DH`, `quays:FC.F2.DL`, `quays:FC.F2.DH`, `quays:FC.F12.DL`, `quays:FC.F12.DN`, `quays:FC.F12.DH`.

Data: © OpenStreetMap contributors (ODbL). Simulation: Eclipse SUMO.
