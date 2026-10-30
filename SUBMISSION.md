# SimTraffick: submission text

Fill in the two blanks marked ✏️ before submitting.

## Project name
SimTraffick: City Policy Crash-Test

## Tagline
An AI agent that crash-tests city traffic policies in simulation, so planners find spillover before the bollards go in.

## Track
Best Apps and Agents

## Links
- **Working demo:** https://city-policy-crash-test.lovable.app/
- **Code:** https://github.com/Toonggg/nebius-hackathon (MIT licence)
- **Demo video:** ✏️ YouTube link

## What we built
SimTraffick tests a proposed traffic policy, for example closing a street to cars, by running it through
a traffic simulator before it is built. An agent powered by NVIDIA Nemotron forms hypotheses from
evidence. It then chooses which simulations to run and adapts to each result. It reports whether the
policy works, where traffic goes instead, and whether any fix holds. Our demo case closes Quai de
l'Hôtel de Ville in Paris to eastbound cars.

## Why
Road closures and car-free zones often succeed on the target street but push traffic onto
residential side streets. Simulators can reveal this, but someone has to decide what to test, read the
output, and check fixes. SimTraffick automates that loop, and shows its evidence and its uncertainty.

## How it works
1. **Nemotron 3 Ultra** turns evidence cards into testable hypotheses.
2. **Nemotron 3 Super** picks the next experiment from a fixed catalogue: the policy, modal filters on
   the most-used detour streets, and low/normal/high demand. A JSON schema allows only valid, untested choices.
3. **SUMO** simulates each experiment with 3 random seeds on the real OpenStreetMap network, inside a
   **Nebius Token Factory Sandbox**.
4. **Python** checks the goal, residential spillover, network delay and gridlock. Every number in
   the report comes from SUMO, never from the LLM.
5. The loop repeats within a budget of 6 experiments. The web app (Lovable) shows the agent's timeline,
   maps of where traffic moved, and the verdict, live or as a recorded run.

**Result for Paris:** the closure meets its goal (171 → 0 cars/h), but traffic on three residential
streets in the Marais rises several-fold, e.g. Rue de Brosse 16 → 186 cars/h. Every modal-filter
fix gridlocks the area. Verdict: fails as proposed. A full run takes under 2 minutes in the cloud
(about 40 s in our latest run), using 9 Nemotron calls and about 26k tokens.

**One-file configuration:** the whole case (area, street, demand, thresholds, evidence) is in
`scenario.json`. Changing it rebuilds the road network automatically, in the cloud.

## How we used NVIDIA models and Nebius
- **Nemotron 3 Ultra** (`nvidia/Nemotron-3-Ultra-550b-a55b`): one reasoning-heavy call per run, for hypotheses.
- **Nemotron 3 Super** (`nvidia/nemotron-3-super-120b-a12b`): about 8 fast decision calls per run with
  structured JSON output; also the judge in our minimal example.
- **Token Factory inference:** the OpenAI-compatible API, called from inside the sandbox.
- **Token Factory Sandboxes:** SUMO plus the whole agent loop run per run in an isolated microVM, from an
  image built once. The web app's live mode starts the same run through an edge function.
- **Where Token Factory helped:** Sandboxes replaced the always-on VM we first planned, giving pay-per-run
  simulation with results identical to local runs. Because one key covers inference and Sandboxes, a whole
  run is a single API call.

## Feedback on Nebius Token Factory and NVIDIA models
- **Nemotron structured output was reliable.** Super and Ultra followed our JSON schemas on every call in
  our runs, and the rule-based fallback never triggered. Super calls mostly took 2–6 s, with occasional
  outliers (11 s, once 44 s).
- **Sandboxes fit the workload.** One microVM per run, simple REST endpoints, and an `llms.txt` docs index
  made it quick to integrate with the standard library only.
- **Activation was hard to see.** Before Sandboxes was enabled, `/whoami` returned 200 with every permission
  `false`, and a made-up project ID got the same answer. A clear "not activated for this project" message
  would help.
- **Trial end and billing were confusing.** After the trial ended, every model returned
  `402 exhausted your budget`. It took us a while to work out that the fix was in the console's billing
  settings, and whether credits belong to the organisation or the project. No API reports the balance.
- **Slim images need extra libraries for SUMO.** `python:3.12-slim` lacks libraries the SUMO wheel's
  binaries need even headless (`libexpat1`, `libatomic1`, X11, `libGL`). A doc note on common native
  dependencies would save time.

## Pre-existing work
None. This is a new project, built during the submission period (first commit 11 October 2026).

## Builders & Brews city
✏️ City attended, or "none"
