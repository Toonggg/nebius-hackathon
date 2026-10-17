"""NemotronPlanner: the agent's judgement calls made by Nemotron 3 on Token Factory.

- ``plan_hypotheses``: Nemotron Ultra turns evidence + the network brief into testable hypotheses.
- ``decide``: Nemotron Super picks the next step from what has been measured so far.

Each call gets a JSON schema built from the *current* state (untested catalogue IDs, allowed
phases, known hypothesis IDs), and Python re-validates the reply anyway. One invalid reply is
retried once with the error; after that the call falls back to ``StateMachinePlanner``.
After ``MAX_FAILURES`` failed calls in a row the LLM is switched off for the rest of the run.
Every LLM call, error and fallback is an event, so the UI and report can show it. The LLM
never supplies a number: verdicts and the report come from the SUMO results only.
"""

import json

from . import llm, metrics, network, scenarios
from .agent import NOMINAL, TRANSITIONS, Decision, Hypothesis, Phase, StateMachinePlanner

MAX_FAILURES = 3

SYSTEM = """You plan traffic-simulation experiments that crash-test a city traffic policy before it ships.
A Python harness runs SUMO for you; you never see or invent numbers it hasn't measured.
Policy: {policy}. Goal G1: traffic on that segment falls by at least {g1}%.
Constraints: C1 a residential street rises by >{c1_pct}% and >{c1_veh} cars/h; C2 network delay rises by
>{c2_pct}% and >{c2_veh} veh·h; C3 gridlock. A violation is robust if it shows up in most seeds.
Experiment IDs are quays:{{policy}}.{{mitigation}}.{{demand}}: policy FC = the closure; mitigation M0 none,
F1/F2 a modal filter on the 1st/2nd ranked detour street, F12 both; demand DL/DN/DH = low/normal/high.
Baselines (BASE) run automatically and are free. Reply with JSON only."""


def _system():
    c = metrics.CONSTRAINTS
    return SYSTEM.format(policy=scenarios.policy_label(), g1=c["G1"]["min_drop_pct"], c1_pct=c["C1"]["pct"],
                         c1_veh=c["C1"]["vehh"], c2_pct=c["C2"]["pct"], c2_veh=c["C2"]["vehh"])


class NemotronPlanner:
    name = "nemotron"

    def __init__(self):
        self.fallback = StateMachinePlanner()
        self.emit = lambda *a, **k: None  # Agent replaces this with its event emitter
        self.failures = 0

    # --- hypotheses (Ultra) -----------------------------------------------------------

    def plan_hypotheses(self, evidence, brief):
        experiments = [s.id for s in scenarios.catalogue() if s.policy != "BASE"]
        checks = ["G1", "C2", "C3", "verified"] + [f"C1:{s}" for s in _residential_streets()]
        card_ids = [c["id"] for c in evidence]
        schema = {
            "type": "object", "required": ["hypotheses"],
            "properties": {"hypotheses": {"type": "array", "minItems": 3, "maxItems": 7, "items": {
                "type": "object", "required": ["text", "experiment_id", "check", "expect", "evidence"],
                "properties": {
                    "text": {"type": "string"},
                    "experiment_id": {"enum": experiments},
                    "check": {"enum": checks},
                    "expect": {"type": "boolean"},
                    "evidence": {"type": "array", "items": {"enum": card_ids}},
                }}}},
        }
        user = json.dumps({
            "task": ("Write 3-7 testable hypotheses about what this policy will do in this network. Each names "
                     "the one experiment that settles it and the check that decides it: G1 (goal met), "
                     "C1:<street> (spillover onto that residential street), C2 (delay), C3 (gridlock), or "
                     "'verified' (for a mitigation experiment at DN: it fixes the spillover without new "
                     "failures). expect=true means you predict the check comes out true. Ground each in the "
                     f"evidence cards where you can. The first test will be {NOMINAL}."),
            "evidence": evidence, "network_brief": brief,
        }, ensure_ascii=False)
        reply = self._call(llm.MODEL_REASONING, user, schema, "hypotheses",
                           lambda r: _parse_hypotheses(r, experiments, checks, card_ids))
        if reply is None:
            self.emit("fallback_used", step="hypotheses", planner=self.fallback.name)
            return self.fallback.plan_hypotheses(evidence, brief)
        return reply

    # --- next step (Super) ------------------------------------------------------------

    def decide(self, state):
        allowed = sorted(p.value for p in TRANSITIONS.get(state.phase, ()))
        remaining = state.remaining
        schema = {
            "type": "object", "required": ["action", "experiment_id", "next_phase", "hypothesis_ids", "rationale"],
            "properties": {
                "action": {"enum": ["run", "next_phase", "stop"]},
                "experiment_id": {"enum": remaining + [None]},
                "next_phase": {"enum": allowed + [None]},
                "hypothesis_ids": {"type": "array", "items": {"enum": [h.id for h in state.hypotheses]}},
                "rationale": {"type": "string"},
            },
        }
        user = json.dumps(_summarise(state, allowed), ensure_ascii=False)
        decision = self._call(llm.MODEL_MAIN, user, schema, "decision",
                              lambda r: _parse_decision(r, state, remaining, allowed))
        if decision is None:
            self.emit("fallback_used", step="decide", planner=self.fallback.name)
            return self.fallback.decide(state)
        return decision

    # --- shared -------------------------------------------------------------------------

    def _call(self, model, user, schema, name, parse):
        """LLM call + validation, one retry with the error. None means: use the fallback."""
        if self.failures >= MAX_FAILURES:
            return None
        log_call = lambda **kw: self.emit("llm_call", step=name, **kw)  # noqa: E731
        error = None
        for attempt in range(2):
            prompt = user if error is None else user + f"\n\nYour previous reply was invalid: {error}. Fix it."
            try:
                reply = llm.chat_json(model, _system(), prompt, schema, name=name, on_call=log_call)
                result = parse(reply)
                self.failures = 0
                return result
            except (llm.LLMError, ValueError, KeyError, TypeError) as err:
                error = str(err)[:300]
                self.emit("llm_error", step=name, model=model, attempt=attempt + 1, error=error)
                if isinstance(err, llm.LLMError) and "HTTP 4" in error:
                    break  # auth/billing/quota: retrying won't help
        self.failures += 1
        if self.failures >= MAX_FAILURES:
            self.emit("llm_disabled", reason=f"{MAX_FAILURES} failed calls in a row; rules from here on")
        return None


def _residential_streets():
    return sorted(n for n, s in network.load_streets().items() if s["residential"] and s["judged"])


def _parse_hypotheses(reply, experiments, checks, card_ids):
    out = []
    for i, h in enumerate(reply["hypotheses"], 1):
        if h["experiment_id"] not in experiments or h["check"] not in checks:
            raise ValueError(f"hypothesis {i}: unknown experiment_id or check")
        if h["check"] == "verified" and scenarios.Scenario.parse(h["experiment_id"]).mitigation == "M0":
            raise ValueError(f"hypothesis {i}: 'verified' needs a mitigation experiment (F1, F2 or F12)")
        out.append(Hypothesis(f"H{i}", str(h["text"]), h["experiment_id"], h["check"], bool(h["expect"]),
                              [e for e in h["evidence"] if e in card_ids]))
    if not out:
        raise ValueError("no hypotheses")
    return out


def _parse_decision(reply, state, remaining, allowed):
    action = reply["action"]
    if action == "run":
        if state.phase == Phase.POLICY_TEST and NOMINAL not in state.results and reply["experiment_id"] != NOMINAL:
            raise ValueError(f"the first experiment must be {NOMINAL}")
        if reply["experiment_id"] not in remaining:
            raise ValueError(f"{reply['experiment_id']} is not an untested catalogue entry")
        return Decision("run", reply["experiment_id"], hypothesis_ids=_known_ids(reply, state),
                        rationale=str(reply["rationale"]))
    if action == "next_phase":
        if reply["next_phase"] not in allowed:
            raise ValueError(f"next_phase must be one of {allowed}")
        return Decision("next_phase", next_phase=Phase(reply["next_phase"]), rationale=str(reply["rationale"]))
    if action == "stop":
        return Decision("stop", rationale=str(reply["rationale"]))
    raise ValueError(f"unknown action {action!r}")


def _known_ids(reply, state):
    known = {h.id for h in state.hypotheses}
    return [i for i in reply.get("hypothesis_ids") or [] if i in known]


def _summarise(state, allowed):
    """What Super sees each step: text only, no edge-level data."""
    experiments = {}
    for exp_id, r in state.results.items():
        if exp_id.startswith("quays:BASE"):
            continue
        experiments[exp_id] = {
            "label": r["label"],
            "goal_G1_met": r["goals"]["G1"]["met"],
            "target_cars_per_h": r["target_volume"],
            "delay_vehh": r["delay_vehh"],
            "teleports": r["teleports"],
            "robust_violations": [
                {k: v[k] for k in ("key", "base", "value", "severity", "seeds_hit", "seeds")}
                for v in r["violations"] if v["robust"]],
            "top_residential_increases": r["top_increases"],
        }
    return {
        "phase": state.phase.value,
        "allowed_next_phases": allowed,
        "budget": {"used": state.used, "total": state.budget, "left": state.budget - state.used},
        "phase_guide": {
            "policy_test": f"Run {NOMINAL} first. If it shows robust C1 spillover, go to mitigation; else robustness.",
            "mitigation": ("Try modal filters (F1, F2, F12 at DN) on the streets that spill over. A mitigation is "
                           "verified when it removes the targeted spillover, keeps G1, and adds no new major or "
                           "critical violation. Move on once one is verified or none is worth trying."),
            "robustness": ("Re-test the verified mitigation (or the bare policy, M0, if none) at DH and DL, then "
                           "go to report."),
        },
        "network_brief": state.brief,
        "hypotheses": [{"id": h.id, "text": h.text, "experiment_id": h.experiment_id, "status": h.status}
                       for h in state.hypotheses],
        "experiments_run": experiments,
        "mitigations": state.mitigations,
        "untested": [{"id": e, "label": scenarios.describe(scenarios.Scenario.parse(e))} for e in state.remaining],
        "instructions": ("Choose the single most informative next step. action=run needs experiment_id from "
                         "untested (next_phase null); action=next_phase needs next_phase from allowed_next_phases "
                         "(experiment_id null). Give a one or two sentence rationale citing the measurements."),
    }
