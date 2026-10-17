# Build: City Policy Crash-Test demo app

Paste this into Lovable after adding the files from this folder to the project.

---

Build a single-page demo app for **City Policy Crash-Test**: an AI agent that crash-tests a city
traffic policy in simulation before it reaches the street. Tagline: *"Does your policy fix the
street, or just move the traffic elsewhere?"*

**Use the existing files; don't rewrite them:**
- `src/lib/crashtest.ts`: data types and the three functions the UI needs (`loadRecordedRun`,
  `replayRun`, `startLiveRun`) plus `mapSrc` for map images. Read its comments for the event types.
- `supabase/functions/crashtest-run/index.ts`: the edge function for live runs. Deploy it and add
  the secrets `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` (ask me for the values; never put them in code).
- `public/demo/latest.json`: a recorded real run (the `Bundle` type).

**Scenario-agnostic:** the case under test (city, street, policy, evidence) changes from time to time.
Never hard-code a city or street name. Take all such text from `bundle.scenario` (type `Scenario`).
Load the recorded run on page load, so the header can show the scenario before any run starts.

**Page layout**
1. **Header:** name, tagline, and the policy under test from `bundle.scenario`: `policy_label`, plus
   `city` and `area_name` as a subtitle (e.g. "Paris · Hôtel de Ville and the southern Marais").
2. **Two buttons:** "Run live crash test" (`startLiveRun`) and "Watch recorded run" (`replayRun` on
   `loadRecordedRun()`, speed 2). If a live run fails to start, show a small notice ("Live runs
   are unavailable right now, showing a recorded run") and fall back to the recorded run. Show a
   running state with elapsed seconds; a live run takes about 1 minute.
3. **Agent timeline** (left/main column), built from the events as they arrive:
   - a step header per `phase_started` (Research, Hypotheses, Baseline, Policy test, Mitigation,
     Robustness, Report);
   - evidence cards (`evidence_found`): claim + source;
   - hypotheses (`hypothesis_created`) with a status pill updated by `hypothesis_updated`
     (open / supported ✓ / refuted ✗);
   - agent decisions (`decision`): the rationale in a quote style, with a model badge taken from the
     preceding `llm_call` event (e.g. "Nemotron 3 Super · 2.4 s · 2,143 tokens"). If
     `fallback_used` appears, badge it "rule-based fallback";
   - simulations (`experiment_selected` → `simulation_finished`): experiment label, "3 SUMO seeds";
   - warnings (`violation_detected`): street, base → value cars/h, severity colour
     (minor yellow, major orange, critical red);
   - mitigation verdicts (`mitigation_verified` / `mitigation_rejected`).
4. **Results** (right column, or below on mobile), shown when the run finishes:
   - **Verdict banner** from `bundle.run.verdict` (red if it starts with "FAILS").
   - **Experiment cards** for each entry in `bundle.run.experiments`: label, goal G1 met or not
     (`target_volume` base → value cars/h), delay base → value veh·h, robust violations, and the map
     image (`mapSrc(bundle, id)`) if it has one. Caption the maps: "Change in cars/h per street vs
     baseline. Red = more traffic."
   - **Hypotheses table** from `bundle.run.hypotheses`.
   - **Full report** in a collapsible section: render `bundle.report_md` as markdown (react-markdown
     + remark-gfm). Replace image links `maps/<file>.png` with the matching `mapSrc`.
5. **Footer:** "Reasoning: NVIDIA Nemotron 3 on Nebius Token Factory · Simulation: Eclipse SUMO ·
   Map data © OpenStreetMap contributors". Add a short "How it works" strip: Research → Hypotheses
   (Nemotron Ultra) → Experiments chosen by Nemotron Super → SUMO simulates → Python checks every
   number → Report. Note: "The AI picks experiments; every number comes from the simulator."

**Style:** clean and serious, like a planning tool: white background, slate text, one accent colour
(teal), red/orange/yellow only for warnings. shadcn/ui components. Timeline entries animate in as
they arrive.
