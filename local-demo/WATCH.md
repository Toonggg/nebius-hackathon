# Watching the local simulations

The agent runs SUMO headless. `watch` replays any catalogue experiment in `sumo-gui`, using
the same network, trips, seed and SUMO options as the measured run (`runner.sim_args`). What
you see is the run behind the numbers in `runs/latest/report.md`.

All commands run from `local-demo/`. The examples below use the Paris scenario (`scenario.json`):
street names, edge IDs and experiment IDs change with the scenario.

## One-time setup (macOS)

`sumo-gui` comes with the `eclipse-sumo` pip package, but it's an X11 app:

```bash
brew install --cask xquartz     # then log out and back in
```

Without XQuartz, `watch` exits with `unable to open display`. On Linux with a desktop, no setup
is needed.

## Reading the view

- **Colours:** cars are coloured by their current speed. SUMO's default *by speed* scale blends
  smoothly between these points:
  - Red: 0 km/h (stopped).
  - Orange: ~15 km/h.
  - Yellow: 30 km/h.
  - Green: 55 km/h.
  - Cyan, blue, magenta: 80, 120, 150 km/h. These are rare here: only ~200 m of road
    allows more than 50 km/h.

  Almost every street in the box is limited to 20–30 km/h, so traffic that is moving freely
  shows as orange to yellow, not green. Queues show up as red strings.
- **Clock:** the clock is simulated seconds.
  - 0–300 s: warm-up (the network fills up).
  - 300–3,900 s: the measured design hour.
  - Up to 5,100 s: cool-down while trips finish.
- **Speed:** `--delay` sets the milliseconds per simulated second (default 20; `0` = as fast as
  possible). You can also change it live with the *Delay* box in the toolbar.
- **Finding a street:** use *Locate → Edges* and type an edge ID. The IDs used below:

| Street | Role | Edge ID |
|---|---|---|
| Quai de l'Hôtel de Ville (eastbound) | the closed segment | `521338709#1` |
| Rue François Miron | filter site F1 | `511451176#0` |
| Rue de Brosse | filter site F2 | `64972827#0` |

`watch` prints the IDs of whatever the scenario closes. They hold for the committed
`data/net.net.xml.gz`; rebuilding the network from fresh OSM data can change them.

## Examples

### 1. Baseline: normal traffic

```bash
.venv/bin/python -m crashtest_demo watch quays:BASE.M0.DN
```

Traffic flows along both directions of Quai de l'Hôtel de Ville. The Marais side streets stay
quiet; Rue de Brosse carries only ~16 cars/h.

### 2. The policy: spillover into the Marais

```bash
.venv/bin/python -m crashtest_demo watch quays:FC.M0.DN
```

Eastbound cars can't use the closed segment. Instead they turn north up **Rue de Brosse**,
east along **Rue François Miron**, and back south via **Rue de Fourcy** and Rue des Nonnains
d'Hyères to the quay. Brosse, Miron and Fourcy go from ~15–50 to ~185–215 cars/h. Nothing locks up (no teleports), which matches the report: the policy works for the
quay and moves the problem onto residential streets.

### 3. Baseline and policy side by side

Run each in its own terminal (or background the first) and arrange the two windows next to
each other:

```bash
.venv/bin/python -m crashtest_demo watch quays:BASE.M0.DN &
.venv/bin/python -m crashtest_demo watch quays:FC.M0.DN
```

Both use seed 1, so the same cars set off at the same times. Only the network differs.

### 4. A "fix" that gridlocks: the closure point on Rue François Miron

```bash
.venv/bin/python -m crashtest_demo watch quays:FC.F1.DN
```

With the detour filtered too, eastbound through traffic has no local route left.
- **Where:** queues build on Quai de l'Hôtel de Ville west of the closure, then back up onto
  Quai de la Mégisserie and Pont de l'Archevêché.
- **When:** cars stop within the first minute; the first are removed as jammed ("teleported")
  at ~340 s.
- **How bad:** about 170 teleports over the run.

`quays:FC.F2.DN` (filter on Rue de Brosse) looks almost the same.

### 5. The policy at high demand: slow-building gridlock

```bash
.venv/bin/python -m crashtest_demo watch quays:FC.M0.DH --delay 0
```

The detour copes at first, then the eastern Marais locks up: Rue du Fauconnier, Rue des Jardins
Saint-Paul, Rue de l'Avé Maria and Rue des Nonnains d'Hyères. The first teleports come at
~1,850 s. Run at full speed until ~1,500 s, then raise the delay to watch it form. Example 7
shows how to pause there automatically.

### 6. Same experiment, different seed

```bash
.venv/bin/python -m crashtest_demo watch quays:FC.M0.DN --seed 3
```

The report averages seeds 1–3. Comparing seeds shows how much of a pattern is the policy and
how much is random demand.

### 7. Run `sumo-gui` yourself

`--print` prints the full command instead of launching it. Use it to add your own SUMO options
or to run the GUI elsewhere:

```bash
.venv/bin/python -m crashtest_demo watch quays:FC.M0.DN --print
# then run the printed command with extra options, e.g. append
#   --breakpoints 1500     pause at 1,500 s (handy for example 5)
```

The scenario network and trips it points to live in `work/nets/` and `work/demand/`. `watch`
creates them first if they're missing.

## Every experiment you can watch

```bash
.venv/bin/python -m crashtest_demo catalogue
```

Any ID it lists works with `watch`.
