# [Name TBD] — City Policy Crash-Test

> An evidence-driven AI agent that crash-tests city traffic policies in simulation, so planners find unintended consequences (like traffic spilling onto residential streets) **before** the policy reaches the street.

**Hackathon:** Nebius × NVIDIA Global AI Hackathon · **Track:** Best Apps and Agents (+ Best Use of Tavily bonus)
**Deadline:** Fri 30 Oct 2026, 10:00 PT = **18:00 CET** · **Internal deadline:** Thu 29 Oct · **Judging:** 1–15 Dec (demo must stay up until then)

---

## 0. Decisions at a glance

| Topic | Proposal | Status |
|---|---|---|
| Track | **Best Apps and Agents** (encourages Nemotron Ultra/Super/Nano routing and Nebius Serverless) | Proposed |
| Bonus prize | **Best Use of Tavily** (needs runtime Tavily calls; we have them) | Proposed |
| Models | Nemotron 3 **Ultra** (deep reasoning), **Super** (agent loop), **Nano/Lightning** (fast extraction) via **Token Factory** | Confirm IDs on day 1 |
| Research | Tavily search + extract, turned into evidence cards with quotes and URLs | — |
| Simulator | SUMO 1.28 (`pip install eclipse-sumo`) | — |
| Study area | **Paris Centre**: Hôtel de Ville / upper Seine quays / Rivoli / St-Antoine / Le Marais | Proposed |
| Headline demo policy | Close the **upper quays** (Quai de Gesvres → Quai des Célestins, ~850–1,060 veh/h at AM peak) to through traffic | Pick after network build |
| Frontend | **Lovable** (React + Vite + TS + Tailwind + shadcn), published on `*.lovable.app`. Replaces the Streamlit idea from the first draft | — |
| Nebius budget | We have **Token Factory API credits**. Token Factory is our Nebius runtime. Nebius AI Cloud compute (Serverless Endpoints/Jobs) is likely billed separately, so we don't depend on it | Decided |
| Backend | Thin Python **FastAPI** orchestrator in Docker on a **free tier** (Render free web service). It makes live Nemotron + Tavily calls and serves simulation results from the precomputed sweep. Move to a Nebius Serverless Endpoint only if we get AI Cloud credits | Proposed |
| Simulation | The catalogue is finite, so we **precompute every scenario with SUMO** once ("simulation oracle" + benchmark ground truth). The agent still only sees results of experiments it selects, within budget. Sweep runs locally (`LocalRunner`) or in parallel in **Token Factory Sandboxes** (`SandboxRunner`, Beta, ≤ 50 concurrent) | Proposed (request Sandboxes access day 1) |
| Repo | **One public monorepo created by Lovable**: Lovable app at root, Python in `engine/` | Proposed |
| Name | Shortlist in §1, decide with the team | TBD |

---

## 1. Name shortlist

Keep **"City Policy Crash-Test"** as the descriptive subtitle whatever name we pick. Avoid NVIDIA/Nebius trademarks in the name.

| Name | Repo slug | Tagline | Why it works | Caveat |
|---|---|---|---|---|
| **Elsewhere** ⭐ | `elsewhere` | "Does your policy fix the street — or just move the traffic elsewhere?" | Taken straight from our core question; memorable, not jargon | Generic word; slug may need `-city` |
| **Spillover** | `spillover` | "Find the spillover before the bollards go in." | Names the exact failure mode we hunt | Less distinctive |
| **CutThrough** | `cutthrough` | "Catch cut-through traffic before your policy ships." | Transport term for residential short-cuts, plus "cut through the noise" | US term (UK says "rat run") |
| **Premortem** | `policy-premortem` | "A premortem for city policy — backed by simulation, not vibes." | Describes the method: assume it failed, find out why | Not obviously about traffic |
| **Knock-On** | `knock-on` | "Crash-test city policies for knock-on effects." | Everyday phrase for unintended consequences; generalises beyond traffic | British idiom |
| **Rat Run** | `ratrun` | "Find the rat runs before the residents do." | Planners' exact term; playful | UK-centric; "rat" |
| **Waterbed** | `waterbed` | "Push traffic down here — see where it pops up." | The "waterbed effect" is the displacement metaphor | Needs explaining |
| **Proving Ground** | `proving-ground` | "A proving ground for city policy." | Fits the crash-test idea; extends to other policies | Widely used name |

**Recommendation:** **Elsewhere — City Policy Crash-Test**, with Spillover as runner-up. Rename the GitHub repo once we choose; Lovable sync survives a rename.

---

## 2. What to submit → how we satisfy it

Source: the hackathon overview "What to Submit" section and the [Official Rules](https://nebiusglobalaihackathon.devpost.com/rules).

| # | Requirement | Our artifact | Owner | ☐ |
|---|---|---|---|---|
| 1 | **Working project** built with NVIDIA Nemotron / NVIDIA open models on Token Factory or AI Cloud, meeting the track requirements | Every reasoning step is a runtime Token Factory call to Nemotron 3 (Ultra/Super/Nano), which meets the "runtime call to the Token Factory inference API" definition. SUMO sweeps optionally run in Token Factory Sandboxes | All | ☐ |
| 2 | **Category** | Best Apps and Agents | — | ☐ |
| 3 | **Project description** (what, why, how) | `docs/devpost.md`, reused from the README | WS5 | ☐ |
| 4 | **Working demo URL** | `https://<name>.lovable.app`. *Replay* mode always works (static JSON); *Live* mode calls the backend | WS4/WS5 | ☐ |
| 5 | **Demo video** ≤ 3 min, public YouTube, shows the project working and how Token Factory + Nemotron are used | Script in §14; no copyrighted music or third-party logos | WS5 | ☐ |
| 6 | **Public repo** with OSS licence visible in the About section | MIT `LICENSE` at root; repo set to **public** (Lovable repos start private) | WS5 | ☐ |
| 6a | **README** with setup instructions and run guidance | Local run (engine + UI), env vars, Docker, deploy | WS5 | ☐ |
| 6b | README highlights **how we use Nemotron, where Token Factory accelerated us, other Nebius services** | Sections "Models & routing" (Ultra/Super/Nano per step, with token and latency stats), "Token Factory" (inference + Sandboxes), "What we'd use with more credits" (Serverless Endpoints/Jobs) | WS3/WS5 | ☐ |
| 7 | **Feedback** on Token Factory, AI Cloud, NVIDIA tools | Running log in `docs/feedback.md` (also eligible for Most Valuable Feedback, $100 × 10) | All | ☐ |
| 8 | Pre-existing project explanation | N/A: new project started in Oct 2026 (say so explicitly) | — | ☐ |
| 9 | **Builders & Brews city** (City Winner, $500) | Select the city if any of us attended an IRL event | — | ☐ |

Rules worth remembering:
- Judges may judge **only** from the text, images and video, so the video and README must stand alone.
- Everything must be in English.
- The demo must be free and unrestricted until judging ends (give credentials if anything is gated).
- The project must install and run as shown in the video.
- Prize stacking: one Overall award **or** one Track award, **plus** one Bonus award (e.g. Best Use of Tavily).

---

## 3. Track fit and judging criteria

**Stage 1 (pass/fail):** the project must be a genuine attempt at the track goal and use the required APIs.
- Best Apps and Agents asks for "an app or agent someone would actually use… a workflow that runs itself… powered by Nemotron on Token Factory."
- Our product is an autonomous research → hypothesise → simulate → verify workflow for city planners, and every reasoning step is a Nemotron call on Token Factory.

**Stage 2 (equally weighted):**

| Criterion | What we show |
|---|---|
| **Technological Implementation** | Multi-model routing exactly as the track suggests (Ultra for hypotheses and report, Super for the agent loop, Nano/Lightning for extraction). Structured outputs constrained to a finite experiment catalogue. Numbers come only from SUMO, never from the LLM. Isolated, parallel SUMO experiments in Token Factory Sandboxes (a non-obvious use of a product built for coding agents) |
| **Design** | A complete Lovable product: policy form → live agent timeline → map of Δ traffic → Policy Failure Report → benchmark. Replay mode and precomputed simulations, so judges get a fast, smooth experience even on a cold start |
| **Potential Impact** | A real, current pain point: traffic displacement from closures, Low Traffic Neighbourhoods and Paris's 2024 limited-traffic zone (ZTL). Real audience: city transport planners, consultants, residents' groups. Real Paris data and network |
| **Quality of the Idea** | The LLM is not a chatbot over a simulator. It designs experiments under a budget, grounded in literature. We benchmark adaptive vs fixed vs random selection and state our assumptions and uncertainties honestly |

---

## 4. Problem, user, solution

**Problem.** Cities close roads and create pedestrian zones or cycle lanes to improve urban life. An intervention that calms one street can divert traffic onto nearby residential streets and move the problem instead of solving it. Traffic simulators can compare scenarios, but someone still has to decide *what* to test, interpret the results and check whether a fix works.

**User.** A city transport planner, or a consultant or residents' group reviewing a proposal, who asks: *"Will this policy achieve its goal, or will it simply move the problem elsewhere?"*

**Solution.** An agent that:
1. **Researches** published evaluations to find likely risks.
2. **Turns** that evidence into explicit, testable hypotheses.
3. **Runs** targeted SUMO experiments chosen from a finite, validated catalogue.
4. **Verifies** mitigations across several demand assumptions.
5. **Writes** a Policy Failure Report: baseline, policy, discovered risks, mitigation results, evidence sources, assumptions and remaining uncertainties.

**How it works: three components in one evidence-driven loop.**

| Component | Role |
|---|---|
| **Tavily**: research | Searches and extracts evidence from published policy evaluations, transport studies and papers. It surfaces risks (e.g. traffic displacement) and possible mitigations |
| **NVIDIA Nemotron via Nebius Token Factory**: reason and plan | Turns evidence into testable hypotheses. After each simulation it analyses the measured results and picks the next experiment from the predefined catalogue |
| **SUMO + Python**: simulate and verify | SUMO supplies the numbers. Python computes traffic changes, journey times, constraint violations and whether a mitigation works |

Core loop: SUMO simulates → Python measures → Nemotron chooses the next experiment → SUMO tests again.

**Ground rule.** The agent cannot invent simulation results or run arbitrary scenarios. Python validates every experiment, SUMO supplies every number, and research findings only *inform* hypotheses: they don't establish what will happen in our network.

**Example journey (numbers illustrative, not measured).** A planner proposes closing the upper quays to through traffic.
1. Tavily finds evaluations of comparable closures (e.g., the 2016 Voie Georges-Pompidou closure) and evidence on traffic displacement and "traffic evaporation".
2. Nemotron Ultra writes hypotheses, e.g. "displaced traffic will use Le Marais streets parallel to the quays".
3. SUMO runs the baseline, then the closure.
4. Traffic on the quays falls, but a residential street rises 60%. Python flags a constraint violation.
5. Nemotron Super picks a mitigation from the catalogue (e.g., a modal filter on that street). SUMO verifies it under low/base/high demand.
6. The report summarises what holds, what fails, and how sure we are.

---

## 5. MVP scope

**MUST (vertical slice, target Sun 18 Oct):**
- One network (Paris Centre) with a baseline calibrated to the design hour (the busiest hour in the sensor data).
- One headline policy plus ~4 mitigation options.
- Agent loop end-to-end: Tavily → evidence cards → hypotheses → baseline → policy → violation detection → one mitigation verified.
- Deterministic metrics and violation checks.
- Report with numbers filled in from SUMO results.
- Lovable UI: timeline, map, report, plus replay mode from a static run JSON.

**SHOULD (by Sun 25 Oct):**
- Exhaustive sweep of the frozen catalogue: local multiprocessing, or a bounded batch in Token Factory Sandboxes. Feeds the simulation oracle and the benchmark.
- Live runs from the UI via the hosted thin API: live Nemotron + Tavily, simulation results from the oracle. SSE progress (polling fallback) and a "waking up" state for cold starts.
- Robustness across demand, evaporation and routing assumptions.
- Benchmark: adaptive vs fixed vs random.
- Model badges and latency/token stats per step in the UI.
- 2–3 policy presets.

**STRETCH:**
- Free-text policy intake mapped to presets.
- More policy types from our original vision: speed-limit changes, congestion / limited-traffic zones.
- School and hospital "sensitive receptor" constraint (OSM).
- Emissions and noise metrics.
- A second city.
- Downloadable PDF report.
- (Out of scope: resource 2, Cosmos Predict2 traffic video generation. It needs GPU fine-tuning and doesn't serve the core loop.)

---

## 6. Architecture

```
Lovable app (React, *.lovable.app)
  │  REST + SSE (polling fallback); replay JSON bundled in /public
  ▼
engine/ — thin FastAPI in Docker (Render free; Nebius Serverless Endpoint if AI Cloud credits)
  ├─ agent/      state machine + prompts + Pydantic schemas
  │    ├─ Tavily API (search + extract) .................. evidence      (live)
  │    └─ Token Factory inference (OpenAI-compatible) ... Nemotron 3 Ultra / Super / Nano (live)
  ├─ sim/        scenario catalogue + SimRunner interface
  │    ├─ OracleRunner .... looks up precomputed SUMO results (hosted default; no SUMO at request time)
  │    ├─ LocalRunner ..... SUMO subprocess (development, sweeps, local "fresh run")
  │    └─ SandboxRunner ... Token Factory Sandboxes: prepared image with SUMO + network,
  │                         one isolated operation per experiment, network disabled, ≤50 in parallel
  ├─ metrics/    per-street deltas, constraints, severity (pure Python, recomputed live,
  │              so changing thresholds in the UI needs no re-simulation)
  └─ report/     templated tables + LLM narrative with {{placeholders}}

Offline: sweep (LocalRunner or SandboxRunner) → results JSON/Parquet (oracle + benchmark ground truth)
```

**Why precompute?** The demo catalogue is small enough to enumerate, so we run all of it once. That makes the hosted demo fast, cheap and reproducible, and gives exact ground truth for the benchmark. The agent still sees **only the results of experiments it selects, within the same budget**. That mimics real deployments, where each calibrated city-scale run can take hours and enumeration is impossible. We state this openly in the UI and README.

**Model routing** (all IDs configurable via env; confirm with `GET /v1/models`):

| Step | Model | Output |
|---|---|---|
| Research query planning, evidence-card extraction | Nemotron 3 Nano / 3.5 Lightning | JSON |
| Hypotheses + test plan mapped onto the catalogue | Nemotron 3 Ultra | JSON |
| Next-experiment selection, result interpretation, mitigation choice | Nemotron 3 Super | JSON (enum-constrained IDs) |
| Final report narrative | Nemotron 3 Ultra | Markdown with `{{metric}}` placeholders |

Known Token Factory facts (verify on day 1):
- OpenAI-compatible API at `https://api.tokenfactory.nebius.com/v1/` with `NEBIUS_API_KEY`. Some cookbook examples use a regional host (`api.tokenfactory.us-central1.nebius.com`), so keep the base URL per model in config.
- Candidate IDs:
  - `nvidia/Nemotron-3-Ultra-550b-a55b`: 1M ctx, $1/$3 per M tokens.
  - `nvidia/nemotron-3-super-120b-a12b`: 256K ctx, tools + structured output, ~$0.30/$0.90.
  - `nvidia/Nemotron-3_5-Lightning`: 30B/3B.
  - `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`: ~$0.06/$0.24 (ID from an aggregator listing).
- `response_format: json_schema` and OpenAI-style tools are model-dependent; sources disagree on Nemotron support. Baseline rate limit is ~60 RPM / 400k TPM.
- **Day-0 capability probe** (`probe-models`): list `/v1/models`, then test json_schema, tool calling and the thinking toggle per model (`extra_body={"chat_template_kwargs": {"enable_thinking": false}}`, community docs). Save the results to a capabilities file that the LLM layer reads.

**Guardrails:**
- Experiment IDs are JSON-schema enums built from the remaining catalogue entries and validated by Pydantic.
- **Structured-output fallback chain:**
  1. `json_schema`, with the schema also given in the prompt.
  2. Retry with the validation errors fed back (max 2).
  3. Tool mode: a single named function whose parameters are the schema.
  4. The deterministic heuristic planner, logged as a `fallback_used` event.
  - If structured output fights with reasoning: Ultra reasons in free text, then Super or Nano formats the result into JSON.
- **No invented numbers:**
  - Python builds a **fact table** (`F1…Fn`: label, value, unit, seed range, provenance = experiment ID + metric + seeds + oracle hash). LLM text may contain digits only inside fact placeholders (`{{F12}}`) or evidence citations (`[E3]`). The validator strips those and rejects any digit that remains; an unknown fact ID triggers a retry.
  - Python renders each fact, e.g. "+212 veh/h (+61%; +180…+240 across seeds)". The UI shows it as a chip with a provenance popover.
  - Evidence quotes must be **verbatim substrings** of the Tavily-extracted text, or the card is dropped.
- **Per-run guards:** caps on simulations, LLM calls and tokens (~400k), 15 min wall-clock, and 3 consecutive invalid outputs (then switch to the heuristic). Every call is logged as an `llm_call` event (model, latency, tokens), which feeds the UI model badges and the README usage stats.

---

## 7. Simulation design (SUMO)

- **Network:**
  - **Analysis perimeter:** Hôtel de Ville / southern Marais, ~1.4 × 0.9 km. Constraints are evaluated here only, and not within 150 m of the network boundary.
  - **Simulation area:** the perimeter plus a ~400 m buffer (W 2.3400, S 48.8495, E 2.3720, N 48.8645; ~3.9 km²). The buffer keeps realistic detours (Sébastopol, St-Antoine, both banks' quays, the island bridges). Cutting too tight would overstate residential spillover.
  - OSM extract → `netconvert` with street names kept, which per-street aggregation needs. Key flags:

    ```
    netconvert --osm-files paris_centre.osm.xml --keep-edges.by-vclass passenger,taxi,bus \
      --remove-edges.isolated --geometry.remove --roundabouts.guess --junctions.join \
      --tls.guess-signals --tls.discard-simple --tls.join --osm.lane-access \
      --output.street-names --output.original-names -o net.net.xml.gz
    ```

  - Stored as `.net.xml.gz` (SUMO reads gzip; keeps files small for Lovable and GitHub). Check maxspeed tags (Paris default is 30 km/h).
  - Exported to GeoJSON for the map. Each edge gets a stable integer `idx`, a street id, road class, and flags for "in perimeter" and "residential".
- **Calibration data:** Paris permanent sensors (dataset `comptages-routiers-permanents`; hourly flow `q` and occupancy `k` per arc; ODbL).
  - Days: Tue–Thu, 8 Sep – 16 Oct 2026 (before the Toussaint school holidays; VERIFY). Query with `timezone=Europe/Paris` and bulk-download via `/exports/parquet`. Keep arcs with `etat_barre = Ouvert` and ≥ 70% completeness. `t_1h` is UTC unless `timezone` is set. Some consecutive arcs report identical `q` (likely one detector), so keep one arc per group to avoid counting it twice.
  - **Design hour:** the busiest hour in the data, not an assumed 08:00. Some quay sensors peak in the evening.
  - Target counts = the per-arc median flow in the design hour.
  - **Arcs are directional** (`iu_nd_amont → iu_nd_aval`; `geo_shape` follows the direction of travel). Match each arc to SUMO edges by distance, bearing and street-name similarity (sumolib `getNeighboringEdges`). Check the matches on a review map; manual overrides go in a YAML file.
  - **Coverage check (done 11 Oct):** 42 live sensor arcs within 700 m of Hôtel de Ville, the best of six candidate areas. Means at 08:00: Quai de Gesvres ≈1,060 veh/h, Quai des Célestins ≈920, Quai de l'Hôtel de Ville ≈850, Bd Sébastopol ≈850, Beaubourg/Renard ≈355, Rivoli ≈240, St-Antoine ≈140. Sensors sit on arterials and quays, not residential streets.
  - **Rue de Rivoli has been bus/taxi/bike-only since 2020** (made permanent). It's evidence and precedent for the bus + taxi policy, not a closure target.
- **Demand:**
  - SUMO's `randomTrips` generates candidate routes. Drop routes that start or end on an edge any scenario could close. `routeSampler --optimize full` then fits the rest to the sensor counts.
  - Target fit: ≥ 75% of sensors with GEH < 5. Publish the fit in the UI's assumptions section, measured on the **simulated baseline** (the honest number), not just routeSampler's own fit. If the baseline gridlocks, calibrate to 90–95% of counts and say so.
  - ~10% of vehicles are taxis (share to VERIFY with evidence), so "bus + taxi only" behaves differently from a full closure. Buses and motorcycles aren't simulated; listed as an assumption.
  - Residential streets have no sensors, so their volumes are a **model output**. We say so.
  - Counts don't give full origin–destination routes, so we test several plausible demand and routing assumptions instead of claiming an exact prediction.
- **Route choice in scenarios:**
  - Unaffected vehicles keep their calibrated routes.
  - A 50% "adaptive" share reroutes every 120 s.
  - Vehicles whose route uses a now-forbidden edge become trips, routed at insertion on the scenario network.
  - Evaporation drops E% of those affected vehicles (seeded).
  - This keeps the baseline calibrated while still modelling diversion.
- **Assumptions we vary (robustness):**
  - Demand low / normal / high = P10 / median / P90 of the daily design-hour totals (roughly ×0.85–0.9 / ×1.0 / ×1.1–1.15). Applied by seeded removal or by cloning vehicles with ±60 s jitter.
  - Traffic "evaporation" after closure 0% / 10% / 20%. The agent chooses which to test from evidence.
  - Routing: dynamic rerouting vs static shortest path.
  - 3 random seeds.
- **Policies:** full closure, one-direction closure, bus + taxi only (optionally a lane reallocation).
- **Mitigations (finite list, precomputed sites):**
  - Modal filter on residential street k.
  - 20 km/h limit on street k.
  - Turn ban at junction j.
  - Priority/capacity on the designated diversion arterial.
  - Sites are picked by a rule, never by peeking at simulation results. Python finds the shortest detours for trips that used the target and ranks the residential streets those detours use.
- **How interventions are built:**
  - Every intervention is a netconvert plain-XML patch: edge `allow` lists, lane permissions, `speed`, and connection `delete` for turn bans. Scenario networks are cached by patch hash.
  - Never delete edges, so edge IDs and map features stay aligned across scenarios.
  - No TraCI. Time-window closures (rerouter `closingReroute`) are STRETCH.
- **Metrics:**
  - Per-street vehicle counts, speed and time loss (edgeData).
  - Trip duration and time loss (tripinfo).
  - Teleports and unfinished trips (gridlock flags).
  - Optional emissions.
- **Constraints (defaults, editable in the UI):**

| ID | Rule | Default threshold |
|---|---|---|
| G1 | Goal: target-street motor volume must fall by at least | 70% (full closure; lower for partial policies) |
| G2 (should) | Goal: perimeter vehicle-km must not grow by more than (the "evaporation vs displacement" debate) | +3% (tolerates seed noise) |
| C1 | Residential spillover: violated if a residential street rises by both… (Δ% uses max(base, 50 veh/h) so tiny bases don't explode) | > 30% **and** > 100 veh/h |
| C1b (should) | Environmental capacity: violated if a residential street crosses (Buchanan / Appleyard; cite via Tavily) | 400 veh/h |
| C2 | Network delay: violated if total delay (time loss + insertion delay) rises by both… | > 10% **and** > 20 veh·h |
| C3 | Gridlock (always critical): violated if jam teleports, or unfinished trips, reach… | ≥ max(10, 0.5% of inserted) teleports; ≥ 2% unfinished |
| C4 (stretch) | Sensitive receptors: violated if a street near a school rises by | > 50 veh/h |

- **Robustness:** a violation is **robust** if it happens in ≥ 2 of 3 seeds, and **confirmed** if it also holds on seeds 4–5. Severity is how far the value goes past the threshold. Classes are minor, major and critical (gridlock is always critical).
- **Scenario catalogue:**
  - Experiment IDs follow `{target}:{policy}.{mitigation}.{demand}.{evaporation}`, e.g. `quays:FC.F_verrerie.DH.E0`.
  - Size: ~4 policies × 7 mitigation options (incl. none) × 9 demand/evaporation conditions = **~252 experiments per target**, plus 3 baselines. Adding a routing dimension doubles it.
  - Default budget is **K = 10 experiments** (the UI offers 6/10/16), each run with 3 seeds.
  - It's enumerable, so the exhaustive sweep gives an upper bound **for this catalogue** (not real-world truth).
- **Runtimes** (to measure on day 1):
  - One micro run (~4 km², 8–15k veh/h): ~15–90 s. One meso run: ~3–15 s.
  - Full sweep: 252 × 5 seeds ≈ 1,260 runs ≈ 5–30 CPU-hours in micro mode. That's a few hours to overnight on an 8-core laptop, or roughly 15–60 min across 50 Sandboxes.
  - Rule: if a baseline micro run takes under ~90 s, use micro everywhere; otherwise use meso everywhere. Never mix modes between the oracle and the benchmark.
  - Use one mode everywhere; micro is preferred for credibility.
  - Verified 11 Oct: the `eclipse-sumo` 1.28 wheel ships `tools/` (randomTrips, routeSampler, osmGet). See §11.4.
- **Attribution:** "© OpenStreetMap contributors" and "Ville de Paris, Comptages routiers permanents" (both ODbL), shown in the UI and README, with a `DATA-LICENSE.md` next to the data files.

---

## 8. Agent loop

**Phases** (Python enforces every transition): intake → research → hypotheses → baseline → policy test → adaptive loop (budget *B*, with at most 2 extra research steps) → mitigation search → robustness check → report.

- **Network-context brief:** the LLM can't see the map, so Python gives it a short text summary: the target, detour streets ranked by graph screening, their baseline flows and road classes, and sensor coverage.
- **Research (Tavily):** advanced search with preferred domains (paris.fr, apur.org, cerema.fr, airparif.fr, bruitparif.fr, ademe.fr, journals), queries in French and English. The top ~8 sources are extracted, then Nano turns them into ≤ 12 evidence cards (verbatim quote, digit-free claim, tags, URL). Responses are cached, but runs call Tavily live up to a daily cap.
- **Hypotheses** (Ultra) carry a structured test: constraint, location (street), and condition (demand, evaporation). That lets Python mark each one supported / refuted / inconclusive / open (k of n matching experiments tested), and list which experiments would resolve it.
- **Each adaptive step:**
  1. Super receives the hypotheses, the results so far and the untested catalogue entries.
  2. It returns `{action: run | research | start_mitigation | stop, experiment_id, hypothesis_ids, rationale}`. `experiment_id` is restricted to the remaining catalogue IDs.
  3. Python validates the choice and the simulation oracle returns its results.
  4. Python computes deltas and violations, then updates each hypothesis status by **deterministic rules**. Super explains the outcome in words.
- **Mitigation phase:** starts once a robust violation exists (or 60% of the budget is used). Ultra ranks the catalogue mitigations.
  - A fix only counts as **verified** if three things hold: the target violation is no longer robust, the goals are still met, and no new major violation appears elsewhere. The last check catches "whack-a-mole" displacement.
- **Stop when** the budget is spent, OR a verified mitigation also holds at the adverse corner (high demand, no evaporation), OR all hypotheses are resolved, OR a guard trips. If no failure is found, the report says "no failure found within budget" and shows coverage.
- **Every step emits an event:** `phase_started`, `evidence_found`, `hypothesis_created`, `experiment_selected`, `simulation_finished`, `violation_detected`, `mitigation_verified`, `report_ready`. The UI timeline and replay files are just these events.
- **Caching:** Tavily and LLM responses are keyed by request hash. Simulation results come from the oracle, keyed by scenario ID + seed. This makes repeat demos cheap and the benchmark reproducible.

---

## 9. Evaluation: does adaptive selection find failures faster?

**Positioning.** We don't claim that combining an LLM with SUMO is new; existing projects already do that. Our contribution is to test whether **evidence-guided, budget-constrained experiment selection** finds policy failures more efficiently than a fixed set of stress tests.

- **Budget:** same *K* experiments after the mandatory nominal policy test, for every strategy. K ∈ {4, 6, 10, 16}.
- **Strategies:**
  - **Fixed:** the stress tests a planner would run by default, **pre-registered in a YAML file before anyone looks at sweep results**.
  - **Random:** uniform without replacement, 500 repetitions (free, because it uses the oracle).
  - **Heuristic adaptive** (SHOULD): adverse conditions first, then mitigations matched to the violating street. It is also the agent's fallback.
  - **Adaptive agent:** the Nemotron loop, 10 repetitions per budget.
  - **Ablation** (STRETCH): the agent without evidence cards, which tests the "evidence-guided" part.
- **Ground truth:** the exhaustive sweep, run once as a parallel Token Factory Sandboxes batch (or locally). After that, fixed and random cost nothing (they're table lookups) and the adaptive agent only costs LLM tokens.
- **Metrics:**
  - severity-weighted recall of distinct failure modes (constraint × street) at budget K
  - worst severity found
  - simulations to the first critical failure
  - whether a verified robust fix was found
  - false-fix rate
  - for the agent: tokens, cost and fallback rate
- **Statistics:** means with 95% bootstrap confidence intervals.
- **We report the result honestly, even if adaptive doesn't win.**

---

## 10. Repo, Lovable workflow and contracts

```
/                      ← Lovable Vite app root (Lovable-managed)
  src/                 React UI
  public/replays/      precomputed run JSONs (replay mode, no backend needed)
  public/geo/          network GeoJSON
  .env                 VITE_API_BASE_URL (public, non-secret)
  engine/              Python backend (pyproject, crashtest/ {agent,sim,metrics,report,api,bench}, networks/, scripts/, tests/, Dockerfile)
  contracts/           JSON Schemas generated from engine Pydantic models (source of truth for UI types)
  docs/                architecture.md · feedback.md · devpost.md · video-script.md
  plan.md · README.md · LICENSE (MIT)
```

**Setup** (Lovable can't import an existing repo; connecting always creates a new one):
1. Create the Lovable project from our UI prompt (Appendix A).
2. Click **Connect GitHub**. Lovable creates `Toonggg/<name>`.
3. Clone it and copy in `plan.md`, `LICENSE` and the README from `nebius-hackathon`.
   - ⚠️ Put the Python `.gitignore` in **`engine/.gitignore`**, not the root. Its `lib/` rule would otherwise silently ignore Lovable's `src/lib/`.
   - Add only `.env`, `.venv/` and `__pycache__/` to the root `.gitignore`.
4. Push. Lovable syncs automatically.
5. Make the repo **public** and check that the licence shows in About.
6. Archive `nebius-hackathon`.

**Rules of the road:**
- Only the default branch syncs to Lovable. Backend work goes through branches and PRs. Run `git pull --rebase` before every push to `main`.
- One person owns `src/` at a time, to avoid "diverged" `lovable-sync` branches.
- Put the ownership rules in Lovable's project **Knowledge**: never modify `engine/`, `contracts/`, `docs/`, `public/replays/` or `public/geo/`; never hand-edit generated types; no Supabase.
- After frontend pushes, someone clicks **Publish** in Lovable to update the live demo.
- Keep every file under 10 MB.
- Lovable's free plan is about 5 credits/day (third-party sources; verify). Build the bulk of the UI in code, push it, and spend Lovable credits on polish and Publish. Upgrade to Pro ($25/month) for the final week only if needed.

**Interface contracts (frozen Tue 13 Oct)** so we can work in parallel:
- `RunState` = events[] + experiments[] + report
- `AgentEvent`
- `ExperimentResult` (per-street deltas, constraint results)
- `Scenario`
- `contracts/fixtures/sample_run.json`. The UI builds against this fixture from day 1.
- **Pipeline:** Pydantic models in `engine/` are the source of truth → exported `contracts/*.schema.json` → TypeScript types generated with `json-schema-to-typescript`, committed and never hand-edited.
- CI fails if the exported schemas drift from what's committed. A test validates the fixtures against the models.
- After the freeze, contract changes are additive only.

**Backend API:**

| Method + path | Purpose |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/presets` | Areas, policies, constraint defaults |
| `GET /api/areas/{id}/geojson` | Network geometry for the map |
| `POST /api/runs` | Start a run; returns `run_id` |
| `GET /api/runs/{id}` | Full run state |
| `GET /api/runs/{id}/events?after=n` | Poll for new events |
| `GET /api/runs/{id}/stream` | SSE event stream |
| `GET /api/benchmarks/{area}` | Benchmark results |

Plus:
- CORS for `*.lovable.app` and `*.lovableproject.com` (Lovable preview; VERIFY), plus localhost.
- Per-IP rate limit (e.g. 3 runs/hour), daily caps on runs, tokens and Tavily credits, and a `LIVE_RUNS_ENABLED` kill switch. Together these protect our Token Factory credits during judging.
- SSE with a 15 s keep-alive ping. The 2 s polling fallback is mandatory, because proxy buffering on free hosts is unknown.
- Run lifecycle: `queued → running(phase) → completed | failed | cancelled`.

**Hosting (credit-aware):**
- **Frontend:** Lovable publish (free, `*.lovable.app`).
- **API:** thin FastAPI image on **Render's free web service**.
  - No SUMO at runtime. The oracle is bundled as compact gzipped JSON (~8 MB per target; edge deltas as small integer arrays), with no pandas in the API image, so it fits in ~512 MB of RAM.
  - It spins down after 15 min idle and wakes in under ~1 min, so the UI shows a wake-up state while replay mode works instantly.
  - Server state is ephemeral (lost on spin-down), so the browser keeps the full run bundle (events + results) for the report and for sharing as a replay.
  - Optional keep-warm: a GitHub Actions cron hitting `/api/health`.
  - Alternatives: Google Cloud Run free tier (needs a billing account), or a Nebius Serverless Endpoint (`cpu-d3`) if AI Cloud credits appear.
  - Hugging Face Docker Spaces now need a paid plan, so we're not using them.
- **Secrets:** `NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID` (Sandboxes), `TAVILY_API_KEY`. Stored only as host secrets, never in `VITE_*` variables.
- **Cost envelope:** a live run is cents of Token Factory tokens plus ~15 Tavily credits (free tier: 1,000 credits/month). Cap live runs per day; everything else is served from replay and cache.

---

## 11. Setup: what we need to add (accounts, API keys, installs)

The **SUMO simulation itself needs no API keys**. SUMO is local open-source software, and the OpenStreetMap and Paris traffic data are public. Keys are only needed for:
- the agent (Nemotron + Tavily),
- the optional Sandboxes runner,
- hosting.

### 11.1 What each part needs

| To run… | Accounts / keys | Installs |
|---|---|---|
| **SUMO simulation only** (build network, calibrate, run scenarios, local sweep) | None | Python 3.12 + `eclipse-sumo==1.28.0` (and the engine's Python deps) |
| **Agent run** (research → hypotheses → experiments → report) | Token Factory API key, Tavily API key | Same as above |
| **Sweep in Token Factory Sandboxes** (optional) | Same Token Factory key + project ID + Sandboxes Beta access | `contree-sdk==0.3.6`; `contree-cli` for checks |
| **Frontend development** | GitHub access to the repo | Node 20+ and npm |
| **Hosted demo** | GitHub (repo + Lovable GitHub app), Lovable, Render | Docker (optional, for local image builds) |
| **Submission** | Devpost (every teammate), YouTube | — |

### 11.2 Accounts and keys checklist

| # | What | Where to get it | Env var / place | Who | ☐ |
|---|---|---|---|---|---|
| 1 | **Token Factory API key** | tokenfactory.nebius.com → API keys (`/project/api-keys`), log in with Google or GitHub. It's shown once, so save it in a password manager | `NEBIUS_API_KEY` | Each dev gets their own key, plus one separate **demo key** for the hosted API | ☐ |
| 2 | Token Factory credits | $25 from the form on the hackathon Resources page (code `NEBIUS-DEVPOST-GLOBAL26`), plus $25 more by joining the Nebius Builders Program (link on the same page) | — | Each of us can claim | ☐ |
| 3 | Token Factory project ID | Token Factory → Project settings | `NEBIUS_PROJECT_ID` (SDK) / `NEBIUS_AI_PROJECT` (CLI) | Sandboxes owner | ☐ |
| 4 | Sandboxes Beta access | Request it via Token Factory. Check with `contree auth ls`: `ok` = access, `inactive` = permission still missing | — | Sandboxes owner | ☐ |
| 5 | **Tavily API key** | app.tavily.com (1,000 free credits/month; +$25 via the Builders Program) | `TAVILY_API_KEY` | Agent owner, plus a demo key | ☐ |
| 6 | GitHub access | Collaborator on `Toonggg/<name>`; Lovable's GitHub app installed on the owner account | — | All | ☐ |
| 7 | Lovable | Owner workspace; invite teammates | — | Frontend owner | ☐ |
| 8 | Render | Free account linked to GitHub; one web service built from `engine/Dockerfile`; secrets set in its dashboard | Render env vars | Platform owner | ☐ |
| 9 | Devpost + YouTube | Every teammate joins the Devpost project; the video goes on a public YouTube channel | — | All / WS5 | ☐ |
| — | *Not needed* | OpenStreetMap / Overpass, Paris Open Data (both public, no key), SUMO (open source) | — | — | — |
| — | *Only if we get credits* | Nebius AI Cloud (Serverless Endpoints/Jobs), Google Cloud Run | — | — | — |

### 11.3 Environment variables

`engine/.env.example` is committed with blank values. Copy it to `engine/.env` (gitignored).

```bash
NEBIUS_API_KEY=              # Token Factory key (required for agent runs)
TAVILY_API_KEY=              # Tavily key (required for agent runs)
NEBIUS_PROJECT_ID=           # only needed for SIM_RUNNER=sandbox

TOKEN_FACTORY_BASE_URL=https://api.tokenfactory.nebius.com/v1/
MODEL_REASONING=nvidia/Nemotron-3-Ultra-550b-a55b    # confirm every ID with GET /v1/models
MODEL_MAIN=nvidia/nemotron-3-super-120b-a12b
MODEL_FAST=nvidia/Nemotron-3_5-Lightning

SIM_RUNNER=local             # oracle | local | sandbox
SUMO_HOME=                   # optional: `import sumo` sets it to the pip package automatically

LIVE_RUNS_ENABLED=true       # hosted API guard
DAILY_RUN_CAP=40
ALLOWED_ORIGINS=https://<name>.lovable.app
```

The repo-root `.env` is **public and committed**; Vite/Lovable read it:

```bash
VITE_API_BASE_URL=https://<api-name>.onrender.com
```

| Secret | Laptop | Render (hosted API) | Lovable / browser | GitHub |
|---|---|---|---|---|
| `NEBIUS_API_KEY`, `TAVILY_API_KEY` | `engine/.env` (gitignored) | Env vars (demo keys) | ❌ never | ❌ never (CI uses fakes) |
| `NEBIUS_PROJECT_ID` | `engine/.env` | Only if the API uses Sandboxes | ❌ | ❌ |
| `VITE_API_BASE_URL` | Root `.env` | — | ✅ public | ✅ committed |

### 11.4 Install and run a first simulation (no keys needed)

```bash
# Python side
cd engine && uv sync                       # or: python3.12 -m venv .venv && pip install -e .
uv run python -c "import sumo; print(sumo.__version__, sumo.SUMO_HOME)"
export SUMO_HOME=$(uv run python -c "import sumo; print(sumo.SUMO_HOME)")   # for tools/*.py scripts
uv run sumo --version && uv run netconvert --version

# Build data and run one scenario (planned CLI, implemented in the MVP)
uv run crashtest build-net             # OSM via Overpass → networks/paris_centre/net.net.xml.gz
uv run crashtest fetch-sensors         # Paris Open Data counts (no key)
uv run crashtest calibrate             # randomTrips + routeSampler → calibrated demand
uv run crashtest sim run quays:FC.M0.DN.E10 --seeds 1,2,3

# Frontend (Lovable app at the repo root)
npm install && npm run dev
```

**SUMO install facts (checked 11 Oct):**
- The `eclipse-sumo` 1.28 wheel includes the binaries (`sumo`, `netconvert`, `duarouter`, `sumo-gui`, `netedit`) and `tools/` (`randomTrips.py`, `routeSampler.py`, `osmGet.py`). `import sumo` sets `SUMO_HOME` automatically.
- Wheel size: 55 MB on macOS arm64, 149 MB on Linux x86_64.
- **Wheels exist for Apple Silicon Macs, Linux and Windows, but not Intel Macs.** On an Intel Mac, use Docker or Homebrew.
- The hosted API image doesn't need SUMO (oracle mode); only the sweep/Sandboxes image does.
- `sumo-gui` (for video footage) may need extra GUI setup on macOS (VERIFY).
- If Overpass throttles us, fall back to a Geofabrik Île-de-France extract clipped to our bbox with `osmium`.

### 11.5 Day-1 smoke tests for each key

```bash
# Token Factory: the key works, and which Nemotron models we can call
curl -s https://api.tokenfactory.nebius.com/v1/models -H "Authorization: Bearer $NEBIUS_API_KEY" \
  | python3 -c "import json,sys; print([m['id'] for m in json.load(sys.stdin)['data'] if 'emotron' in m['id']])"

# Tavily: the key works (costs 1 credit)
curl -s -X POST https://api.tavily.com/search -H "Authorization: Bearer $TAVILY_API_KEY" \
  -H "Content-Type: application/json" -d '{"query": "traffic evaporation road closure", "max_results": 1}'

# Sandboxes: permission is active ("ok"; "inactive" = Beta access still missing)
uv tool install "contree-cli==0.9.4"
NEBIUS_AI_PROJECT=$NEBIUS_PROJECT_ID contree auth -y && contree auth ls

# Public data (no key)
curl -s "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/comptages-routiers-permanents/records?limit=1"
```

### 11.6 Key hygiene

- One key per person for development, plus a separate demo key on Render. Revoke dev keys after the hackathon, and rotate the demo key if it leaks.
- `.env` files are gitignored and `.env.example` is committed with blanks. Turn on GitHub secret-scanning push protection.
- Keys never go in `VITE_*` variables, Lovable code or the browser. The frontend only talks to our API.
- The API's daily caps (runs, tokens, Tavily credits) limit what a leaked demo URL can spend.
- CI never calls paid APIs. Tests use recorded fixtures and the fake oracle.

### 11.7 Free allowances and expected spend

| Service | Free allowance | Our use | Expected spend |
|---|---|---|---|
| Token Factory | $25 (form) + $25 (Builders Program) per person | All Nemotron calls | ~$0.10–0.30 per agent run; a few $ for the benchmark |
| Tavily | 1,000 credits/month (+$25 Builders Program) | Research phase | ~15 credits per fresh research phase |
| Render | Free web service, 750 h/month | Thin API | $0 |
| Lovable | ~5 credits/day on the free plan | UI polish + Publish | $0 (Pro at $25 only if needed) |
| Token Factory Sandboxes | Beta; billing not documented | One-off parallel sweep | TBD (ask Nebius) |
| OSM Overpass, Paris Open Data | Free, no key (fair use) | One-off downloads | $0 |

---

## 12. Workstreams (we work separately; contracts keep us in sync)

| WS | Scope | Key deliverables |
|---|---|---|
| **WS1 Data & Network** | OSM → SUMO net, sensor matching, demand calibration, GeoJSON | `engine/networks/paris_centre/`, `public/geo/*.geojson`, `docs/data.md` |
| **WS2 Simulation & Metrics** | Catalogue, `SimRunner` (Oracle + Local + Sandboxes), metrics, constraints, sweep → oracle | `crashtest/sim`, `crashtest/metrics`, CLI `crashtest sim …` / `crashtest sweep` |
| **WS3 Agent** | Tavily + Token Factory clients, prompts, schemas, loop, report | `crashtest/agent`, `crashtest/report`, CLI `crashtest run …` → run JSON |
| **WS4 Frontend (Lovable)** | Landing, crash-test view, map, timeline, report, benchmark | Lovable app against `contracts/` + fixtures |
| **WS5 Platform & Submission** | Docker, API hosting, Sandboxes access, README, video, Devpost text, feedback | Deployed URL, YouTube link, submission |

---

## 13. Timeline (today: Sun 11 Oct)

| Dates | Milestone |
|---|---|
| Sun 11 – Tue 13 Oct | Everyone completes the setup checklist and smoke tests (§11). Pick name. Create Lovable project and repo. Freeze contracts and fixture. Claim the extra credits (Token Factory form code `NEBIUS-DEVPOST-GLOBAL26`, Builders Program for Token Factory + Tavily). **Request Sandboxes Beta access.** Confirm model IDs (`GET /v1/models`). Build the network and check sensor matching |
| Wed 14 – Sun 18 Oct | **Vertical slice** via CLI (baseline → closure → spillover → mitigation, with Nemotron + Tavily). Lovable UI running on replay fixture |
| Mon 19 – Thu 22 Oct | **Freeze the catalogue (Wed 21).** Sweep v1 (local; Sandboxes once access is granted) → oracle. Thin API deployed on Render. Live runs from UI. Map deltas. Report. Robustness assumptions |
| Fri 23 – Sun 25 Oct | Benchmark (fixed / random / adaptive on the oracle). Final sweep if the catalogue changed. UI polish. README with architecture diagram. Curated replay runs |
| Mon 26 – Tue 27 Oct | **Feature freeze Tue 27.** Test from a fresh clone. Feedback write-up. Devpost text |
| Wed 28 Oct | Record and edit video (< 3 min). Upload to YouTube (public) |
| Thu 29 Oct | **Submit** (internal deadline). Then tag `submission-v1` and stop feature pushes to `main`: the rules forbid changing the submission after the deadline, and Lovable syncs `main`. Fri 30 Oct is buffer only |

---

## 14. Demo video (< 3 min)

| Time | Content |
|---|---|
| 0:00–0:15 | Hook: "Close a road and the traffic doesn't vanish. Where does it go?" |
| 0:15–0:35 | Planner picks a policy and constraints in the app |
| 0:35–1:25 | Agent runs live: Tavily evidence cards → Nemotron Ultra hypotheses → SUMO baseline vs closure on the map → spillover flagged |
| 1:25–2:05 | Nemotron Super picks a mitigation; verification across demand assumptions |
| 2:05–2:30 | Policy Failure Report; benchmark: adaptive vs fixed vs random |
| 2:30–2:55 | Architecture: Token Factory model routing (Ultra/Super/Nano), Token Factory Sandboxes for parallel experiments, Tavily, SUMO, open-source repo |

---

## 15. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Model IDs, regions or structured-output support differ from the docs | Model map and base URL via env; test on day 1; JSON-mode + Pydantic fallback |
| Unrealistic flows or gridlock in SUMO | Small bbox; `routeSampler` calibration; teleport and junction tuning; present results as plausible scenarios, not predictions |
| Lovable sync conflicts or credit limits | Single owner for `src/`; push-only workflow; Publish checklist; bulk UI work in code, Lovable for polish |
| Demo dies before judging ends (15 Dec) | Replay mode is static (lives in the Lovable app); thin API on a free tier with wake-up UI and keep-warm ping; health check |
| Catalogue changes late, so the oracle goes stale | One-command sweep script (`crashtest sweep`) with a deterministic catalogue hash; freeze the catalogue Wed 21 Oct |
| Judges ask whether results are "really simulated" | Every oracle entry stores its SUMO version, config and seed. The README shows how to regenerate it locally; the video includes a few seconds of a real SUMO run (sumo-gui) |
| Token Factory credits run out (also funds judge runs until 15 Dec) | Caching, Nano/Lightning for routine steps, replay by default, daily live-run cap, spend tracking from token usage |
| Sandboxes Beta access delayed, or billing unclear | `SimRunner` abstraction: `LocalRunner` works without Sandboxes. Ask in Nebius Discord / contree@nebius.com whether Sandboxes draw on Token Factory credits |
| Over-claiming | Keep the illustrative/assumption framing in the UI and report; don't claim "LLM + SUMO" is new |
| Repo changes after the deadline count as altering the submission | Tag `submission-v1`; no feature pushes to `main` after submitting; only critical ops fixes (e.g. the API host), documented in the README |

---

## 16. Open decisions

1. Name (§1), decided with the team.
2. Monorepo created by Lovable (recommended) vs separate frontend and backend repos.
3. Headline policy preset (after the network build).
4. API host: Render free (recommended) vs Cloud Run free tier vs a Nebius Serverless Endpoint (only with AI Cloud credits).
5. Token Factory Sandboxes: sweep only, or also a live "re-run this experiment fresh in a sandbox" button? Depends on Beta access, start latency and whether they draw on Token Factory credits.
6. Did anyone attend a Builders & Brews event (City Winner field)?
7. Who owns WS1–WS5?

---

## 17. Resources

- Hackathon: https://nebiusglobalaihackathon.devpost.com/ · Rules: https://nebiusglobalaihackathon.devpost.com/rules · Resources and credits: https://nebiusglobalaihackathon.devpost.com/resources
- Token Factory docs: https://docs.tokenfactory.nebius.com/ (quickstart, function calling, structured output, rate limits) · Nemotron cookbook: https://github.com/nebius/token-factory-cookbook/tree/main/models/nemotron
- Token Factory API keys: https://tokenfactory.nebius.com/project/api-keys · Tavily dashboard: https://app.tavily.com · Tavily search API: https://docs.tavily.com/documentation/api-reference/endpoint/search
- Token Factory Sandboxes (Beta): https://docs.tokenfactory.nebius.com/sandboxes/overview.md · Access setup: https://docs.tokenfactory.nebius.com/sandboxes/start/set-up-access.md · Python SDK `contree-sdk`: https://docs.tokenfactory.nebius.com/sandboxes/start/python-quickstart.md · Batch recipe: https://docs.tokenfactory.nebius.com/sandboxes/cookbook/run-bounded-evaluation-batch.md
- Nebius Serverless (only if we get AI Cloud credits): https://docs.nebius.com/serverless/quickstart/endpoints
- Render free web services (API host): https://render.com/docs/free
- Lovable Git sync: https://docs.lovable.dev/integrations/github
- SUMO: https://sumo.dlr.de/docs/ (netconvert, randomTrips, routeSampler, edgeData, tripinfo)
- Paris traffic counts (ODbL): https://opendata.paris.fr/explore/dataset/comptages-routiers-permanents/ · OpenStreetMap (ODbL)
- Tavily: https://docs.tavily.com/
- (Out of scope) Traffic Anomaly Generation with Cosmos Predict2: https://nvidia-cosmos.github.io/cosmos-cookbook/recipes/post_training/predict2/its-accident/post_training.html

---

## Appendix A: Lovable starter prompt (draft, used once to create the project)

> Build a polished, map-first web app called "[Name] — City Policy Crash-Test" for city transport planners. Stack: React + Vite + TypeScript + Tailwind + shadcn/ui, with MapLibre GL for the map (basemap: OpenFreeMap "positron" style, free and no API key). No auth and no Supabase. Data comes from a REST API at `import.meta.env.VITE_API_BASE_URL`. If the API is unreachable, fall back to replay files in `/public/replays/*.json`.
>
> Pages:
> 1. **Landing.** Headline "Does your policy fix the street — or just move the traffic elsewhere?", a 3-step explainer (Research → Simulate → Verify), and the buttons "Watch a crash test" (replay) and "Run a live crash test".
> 2. **Crash Test workspace.**
>    - Left panel: policy preset dropdown, constraint sliders (target-street reduction %, max residential increase as % and veh/h, max network delay %), simulation budget.
>    - Centre: full-height map with street lines coloured by change in traffic volume (diverging scale, legend, toggle Baseline / Policy / Mitigation).
>    - Right panel: live agent timeline. Cards for Evidence (source, quote, link), Hypothesis (status badge), Experiment (scenario chips, key metrics, violation badges) and Mitigation. Each card has a small badge showing which Nemotron model ran the step, its latency and tokens.
> 3. **Report.** Verdict, baseline vs policy vs mitigation tables, discovered risks, evidence sources, assumptions and uncertainties, plus "Download Markdown".
> 4. **Benchmark.** Chart of Fixed vs Random vs Adaptive (violations found vs simulations used).
> 5. **How it works.** Architecture and model-routing diagram.
>
> Use mock data matching `contracts/fixtures/sample_run.json` until the API is live. Style: clean and civic; navy/white base, amber/red for violations, teal for improvements; accessible contrast.
