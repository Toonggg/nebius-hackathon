# Running the demo off Nebius

The local demo has two seams that were built for this move:

| Seam | Local today | On Nebius |
|---|---|---|
| `Planner` protocol (`crashtest_demo/agent.py`) | `StateMachinePlanner` | `NemotronPlanner`: Nemotron 3 on **Token Factory** (Ultra for hypotheses, Super for each step) |
| `SimRunner` protocol (`crashtest_demo/runner.py`) | `LocalRunner` (SUMO subprocess) | `SandboxRunner` (**Token Factory Sandboxes**), or `OracleRunner` over a sweep precomputed there |

Nothing else changes: the `Agent` loop, catalogue, metrics, report and event stream stay as
they are. The guardrails stay in Python: phase transitions, catalogue validation, budget, and
deterministic verdicts. So a misbehaving model can waste a step but can't invent a result.

Facts about Token Factory below come from PLAN.md §6/§11 and are marked VERIFY there. Confirm
model IDs with `GET /v1/models` and check structured-output support per model before relying on it.

---

## 1. Planner → Nemotron on Token Factory

### Setup

```bash
uv pip install --python .venv/bin/python openai
export NEBIUS_API_KEY=...                                    # tokenfactory.nebius.com → API keys
export TOKEN_FACTORY_BASE_URL=https://api.tokenfactory.nebius.com/v1/
export MODEL_REASONING=nvidia/Nemotron-3-Ultra-550b-a55b     # hypotheses (VERIFY ID)
export MODEL_MAIN=nvidia/nemotron-3-super-120b-a12b          # per-step decisions (VERIFY ID)
```

Keep keys in `local-demo/.env` (gitignored) or in the host's secret store, never in the repo.

### What the model gets and returns

Each call replaces one method of `StateMachinePlanner` and returns the same dataclass:

| Method | Model | Input (text only; the model can't see the map) | Output |
|---|---|---|---|
| `plan_hypotheses(evidence, brief)` | Ultra | evidence cards, `network_brief()`, catalogue IDs, constraint definitions | list of `Hypothesis` (`experiment_id` must be a catalogue ID; `check` is `G1`, `C1:<street>`, `C2`, `C3` or `verified`) |
| `decide(state)` | Super | phase, allowed next phases, hypotheses + status, per-experiment summaries (goals, robust violations, deltas; **not** `edge_delta`), mitigation verdicts, untested IDs, budget left | `Decision` |

Build the JSON schema fresh on every call, so the model can only name **untested catalogue
entries** and **allowed phases**. The `Agent` re-validates either way.

### Sketch

Untested sketch: the shape of the code, not a drop-in file.

```python
# crashtest_demo/nemotron_planner.py
import json, os
from openai import OpenAI
from .agent import Decision, Phase, StateMachinePlanner, TRANSITIONS

client = OpenAI(base_url=os.environ["TOKEN_FACTORY_BASE_URL"], api_key=os.environ["NEBIUS_API_KEY"])


class NemotronPlanner:
    name = "nemotron"

    def __init__(self):
        self.fallback = StateMachinePlanner()   # PLAN.md §6: last step of the fallback chain
        self.calls = []                         # model, latency, tokens → README stats + UI badges

    def plan_hypotheses(self, evidence, brief):
        ...  # same pattern as decide(), model=os.environ["MODEL_REASONING"], array-of-Hypothesis schema

    def decide(self, state):
        schema = {
            "type": "object",
            "properties": {
                "action": {"enum": ["run", "next_phase", "stop"]},
                "experiment_id": {"enum": state.remaining + [None]},
                "next_phase": {"enum": [p.value for p in TRANSITIONS.get(state.phase, ())] + [None]},
                "hypothesis_ids": {"type": "array", "items": {"enum": [h.id for h in state.hypotheses]}},
                "rationale": {"type": "string"},
            },
            "required": ["action", "experiment_id", "next_phase", "hypothesis_ids", "rationale"],
        }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\nReply with JSON matching:\n" + json.dumps(schema)},
            {"role": "user", "content": json.dumps(summarise(state))},  # no edge-level data
        ]
        for _ in range(3):  # json_schema → retry with validation errors (max 2)
            resp = client.chat.completions.create(
                model=os.environ["MODEL_MAIN"],
                messages=messages,
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "decision", "schema": schema}},
                temperature=0,
            )
            self.calls.append({"model": resp.model, "usage": resp.usage.model_dump()})
            try:
                d = json.loads(resp.choices[0].message.content)
                return Decision(d["action"], d["experiment_id"],
                                Phase(d["next_phase"]) if d["next_phase"] else None,
                                d["hypothesis_ids"], d["rationale"])
            except (ValueError, KeyError) as err:
                messages.append({"role": "user", "content": f"Invalid: {err}. Reply with valid JSON only."})
        return self.fallback.decide(state)  # log as a `fallback_used` event
```

Wire it in `__main__.py`, e.g. `Agent(LocalRunner(), planner=NemotronPlanner() if args.llm else None, ...)`.

Notes:
- **Structured output.** If `response_format=json_schema` is rejected for a model, use tool
  mode instead: one function whose parameters are the schema. If reasoning and JSON fight, let
  Ultra think in free text and have Super format the result (PLAN.md §6).
- **No invented numbers.** The rationale is free text, but the report never takes numbers
  from it. `report.py` reads them from `state.results` only. If Ultra writes the report
  narrative later, use `{{F12}}` fact placeholders and reject any other digit (PLAN.md §6).
- **Guards.** Cap LLM calls and tokens per run, and stop after 3 consecutive invalid outputs.
  The `Agent` already caps steps (`max_steps`) and experiments (`budget`).
- **Evidence.** Replace `_load_evidence()` with Tavily search + extract plus Nemotron Nano (or
  Lightning) for card extraction. Tavily is not a Nebius service, but it's the other runtime
  call in PLAN.md.

---

## 2. Simulations → Token Factory Sandboxes

SUMO needs no API keys, and one experiment-seed takes about 1 s here, so local runs are fine for
the demo. Sandboxes earn their place for the **full sweep**: every catalogue entry × every
seed, in parallel. That sweep feeds the oracle and the benchmark (PLAN.md §9).

### The unit of work

`LocalRunner._run_one(scenario, seed)` is already self-contained:

```
input : experiment_id, seed
needs : data/net.net.xml.gz, data/streets.json, data/sites.json, crashtest_demo/, eclipse-sumo + sumolib
output: work/results/<id>/s<seed>/result.json   (≈ 10 KB: edge + street volumes, delay, teleports, …)
```

The output is deterministic for a given SUMO version, network, demand file and seed, so
results computed in a sandbox and results computed locally are interchangeable.

### Image

Bake everything into the image so each operation is offline (PLAN.md: "network disabled"):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt     # eclipse-sumo ships Linux x86_64 wheels
COPY crashtest_demo/ crashtest_demo/
COPY data/ data/
# Pre-build every scenario net and trips file so operations only run SUMO.
RUN python -c "from crashtest_demo import scenarios, demand, config; \
  [scenarios.scenario_net(s) for s in scenarios.catalogue()]; \
  [demand.trips_file(seed, d) for seed in config.SEEDS for d in scenarios.DEMAND_SCALE]"
ENTRYPOINT ["python", "-m", "crashtest_demo", "sim"]
```

`python -m crashtest_demo sim <experiment_id>` already runs all seeds and prints the metrics.
For the sandbox, add a `--seed` and `--json` flag so one operation = one experiment-seed and
stdout is the `result.json`.

### SandboxRunner

Follow the Token Factory Sandboxes batch recipe (`contree-sdk`; links in PLAN.md §17). The
calls below are placeholders: check the SDK quickstart for the real names.

```python
class SandboxRunner:
    name = "sandbox"

    def run(self, scenario, seeds=config.SEEDS):
        cached = [self._cache(scenario, s) for s in seeds]
        todo = [s for s, c in zip(seeds, cached) if c is None]
        # PLACEHOLDER API: submit one isolated operation per seed (≤ 50 concurrent, network off),
        # command = ["python", "-m", "crashtest_demo", "sim", scenario.id, "--seed", str(s), "--json"]
        results = sandboxes.run_batch(image=IMAGE, commands=[...], concurrency=min(50, len(todo)))
        for s, r in zip(todo, results):
            self._store(scenario, s, json.loads(r.stdout))   # same work/results/ layout as LocalRunner
        return [self._cache(scenario, s) for s in seeds]
```

Setup (PLAN.md §11.2): Token Factory project ID in `NEBIUS_PROJECT_ID`, Sandboxes Beta access
(`contree auth ls` must say `ok`), and the same `NEBIUS_API_KEY`.

### Sweep → oracle

```bash
# 12 policy experiments + 3 baselines, × 3 seeds = 45 SUMO runs
python -m crashtest_demo sweep --runner sandbox   # to add: loops over scenarios.catalogue()
```

Store the results as one gzipped JSON keyed by `experiment_id` + `seed` plus a catalogue hash.
Then add an `OracleRunner` whose `run()` looks results up in that file. The hosted API then needs
no SUMO at all, and the agent still only sees experiments it chose, within budget.

---

## 3. Where the pieces run

| Piece | Recommended (PLAN.md) | If Nebius AI Cloud credits appear |
|---|---|---|
| Agent loop + API | Thin FastAPI on a free host, `OracleRunner` + `NemotronPlanner` | Nebius Serverless Endpoint (CPU) with the same image |
| LLM calls | Token Factory (the only Nebius dependency we're sure is covered by our credits) | same |
| Sweep | Token Factory Sandboxes (`SandboxRunner`), or `LocalRunner` overnight | Nebius Serverless Jobs running the sweep image |
| Fresh one-off run from the UI | `SandboxRunner` for a single experiment (stretch) | same |

## 4. Checklist

1. `GET /v1/models` with the key, then fill in `MODEL_*`. Probe `json_schema` and tool calling per model.
2. Add `nemotron_planner.py` plus a `--llm` flag. Run once with `--budget 4` and compare `run.json`
   against the state-machine run: same catalogue and same verdict rules, so only the choices should differ.
3. Log every LLM call as an `llm_call` event (model, latency, tokens) next to `decision`.
4. Add `--seed/--json` to `sim`, build the image, and add `SandboxRunner` behind `--runner sandbox`.
5. Add `sweep` + `OracleRunner`, then point the hosted API at the oracle.
6. Before scaling up, swap the toy pieces for PLAN.md's real ones: wider study area, calibrated
   demand (routeSampler on Paris sensor counts), live Tavily evidence.
