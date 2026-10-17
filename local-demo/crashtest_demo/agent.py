"""The agent loop (PLAN.md §8).

Two pieces, kept apart on purpose:

- A planner makes every *judgement*: which hypotheses to write and which experiment to run
  next. ``nemotron.NemotronPlanner`` asks Nemotron on Token Factory (Ultra for hypotheses,
  Super for each step); ``StateMachinePlanner`` below is the rule-based fallback. Both
  return the same ``Decision`` shape.
- ``Agent`` enforces the rules: phase transitions, the experiment catalogue, the budget,
  and deterministic verdicts (constraint checks, hypothesis status, mitigation verification).
  It never trusts the planner with a number.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Protocol

from . import config, metrics, network, scenarios
from .scenarios import Scenario


class Phase(str, Enum):
    RESEARCH = "research"
    HYPOTHESES = "hypotheses"
    BASELINE = "baseline"
    POLICY_TEST = "policy_test"
    MITIGATION = "mitigation"
    ROBUSTNESS = "robustness"
    REPORT = "report"


# Python, not the planner, owns the allowed transitions.
TRANSITIONS = {
    Phase.POLICY_TEST: {Phase.MITIGATION, Phase.ROBUSTNESS},
    Phase.MITIGATION: {Phase.ROBUSTNESS},
    Phase.ROBUSTNESS: {Phase.REPORT},
}

NOMINAL = "quays:FC.M0.DN"  # the mandatory policy test


@dataclass
class Decision:
    """What the planner (state machine today, Nemotron Super later) returns each step."""

    action: str  # "run" | "next_phase" | "stop"
    experiment_id: str | None = None
    next_phase: Phase | None = None
    hypothesis_ids: list = field(default_factory=list)
    rationale: str = ""


@dataclass
class Hypothesis:
    id: str
    text: str
    experiment_id: str  # the experiment that settles it
    check: str  # "G1", a violation key such as "C1:Rue X", or "verified" for mitigations
    expect: bool  # True: goal met / violation present / mitigation verified
    evidence: list
    status: str = "open"  # open | supported | refuted


@dataclass
class RunState:
    budget: int
    phase: Phase = Phase.RESEARCH
    evidence: list = field(default_factory=list)
    brief: dict = field(default_factory=dict)
    hypotheses: list = field(default_factory=list)
    results: dict = field(default_factory=dict)  # experiment_id -> metrics.compare() output
    mitigations: dict = field(default_factory=dict)  # mitigation code -> verification verdict
    events: list = field(default_factory=list)

    @property
    def used(self):
        return sum(1 for e in self.results if not e.startswith("quays:BASE"))

    @property
    def remaining(self):
        return [s.id for s in scenarios.catalogue() if s.policy != "BASE" and s.id not in self.results]

    def verified_mitigation(self):
        return next((m for m, v in self.mitigations.items() if v["verified"]), None)


class Planner(Protocol):
    """Anything that can make the agent's judgement calls (``nemotron.NemotronPlanner`` or the rules below)."""

    name: str

    def plan_hypotheses(self, evidence: list, brief: dict) -> list[Hypothesis]: ...

    def decide(self, state: RunState) -> Decision: ...


class StateMachinePlanner:
    """Deterministic stand-in for the Nemotron planner.

    States are the phases; each ``decide`` call looks only at the current phase and at
    what has been measured so far:

        POLICY_TEST --(robust C1 spillover)--> MITIGATION --(verified, or nothing left)--> ROBUSTNESS --> REPORT
        POLICY_TEST --(no spillover)--------------------------------------------------> ROBUSTNESS
    """

    name = "state-machine"

    def plan_hypotheses(self, evidence, brief):
        f1, f2 = brief["sites"]["F1"]["street"], brief["sites"]["F2"]["street"]
        return [
            Hypothesis("H1", f"Closing {brief['target']} to eastbound cars removes at least "
                       f"{metrics.CONSTRAINTS['G1']['min_drop_pct']}% of the car traffic on that segment.",
                       NOMINAL, "G1", True, []),
            Hypothesis("H2", f"Displaced through traffic spills onto {f1}, the street most "
                       "shortest detours use.", NOMINAL, f"C1:{f1}", True, ["E2", "E3", "E4"]),
            Hypothesis("H3", f"Displaced through traffic spills onto {f2}.", NOMINAL, f"C1:{f2}", True,
                       ["E2", "E3", "E4"]),
            Hypothesis("H4", "Total delay in the area grows past the network-delay limit, i.e. "
                       "traffic does not simply evaporate.", NOMINAL, "C2", True, ["E1"]),
            Hypothesis("H5", "At high demand the closure tips the area into gridlock.",
                       "quays:FC.M0.DH", "C3", True, ["E2"]),
            Hypothesis("H6", f"A modal filter on {f1} removes its spillover without creating "
                       "a new failure elsewhere.", "quays:FC.F1.DN", "verified", True, ["E3"]),
        ]

    def decide(self, s):
        if s.phase == Phase.POLICY_TEST:
            if NOMINAL not in s.results:
                return Decision("run", NOMINAL, hypothesis_ids=["H1", "H2", "H3", "H4"],
                                rationale="Mandatory first test: the policy as proposed, at normal demand.")
            if any(v.startswith("C1:") for v in s.results[NOMINAL]["robust_violations"]):
                return Decision("next_phase", next_phase=Phase.MITIGATION,
                                rationale="Robust residential spillover found; look for a mitigation.")
            return Decision("next_phase", next_phase=Phase.ROBUSTNESS,
                            rationale="No robust spillover at normal demand; stress-test instead.")

        if s.phase == Phase.MITIGATION:
            if s.verified_mitigation():
                return Decision("next_phase", next_phase=Phase.ROBUSTNESS,
                                rationale=f"{s.verified_mitigation()} verified; check it under stress.")
            for code, why in self._rank_mitigations(s):
                exp = f"quays:FC.{code}.DN"
                if exp in s.remaining:
                    hyps = ["H6"] if code == "F1" else []
                    return Decision("run", exp, hypothesis_ids=hyps, rationale=why)
            return Decision("next_phase", next_phase=Phase.ROBUSTNESS,
                            rationale="No untried mitigation in the catalogue is worth testing.")

        if s.phase == Phase.ROBUSTNESS:
            subject = s.verified_mitigation() or "M0"
            for demand, why in (("DH", "adverse corner: high demand"), ("DL", "favourable corner: low demand")):
                exp = f"quays:FC.{subject}.{demand}"
                if exp in s.remaining:
                    hyps = ["H5"] if exp == "quays:FC.M0.DH" else []
                    label = "the verified mitigation" if subject != "M0" else "the policy"
                    return Decision("run", exp, hypothesis_ids=hyps, rationale=f"Re-test {label} at the {why}.")
            return Decision("next_phase", next_phase=Phase.REPORT, rationale="Robustness checks done.")

        return Decision("stop", rationale="Nothing left to decide.")

    def _rank_mitigations(self, s):
        """Filter the worst-hit street first; combine filters only if singles just move the problem."""
        sites = s.brief["sites"]
        violated = [v["street"] for v in s.results[NOMINAL]["violations"]
                    if v["robust"] and v["constraint"] == "C1"]
        ranked = []
        for street in violated:
            for code in ("F1", "F2"):
                if sites[code]["street"] == street:
                    ranked.append((code, f"{street} has the worst robust spillover; filter it."))
        tried = s.mitigations
        if {"F1", "F2"} <= tried.keys() and not any("C3" in tried[m]["new"] for m in ("F1", "F2")):
            ranked.append(("F12", "Each single filter pushed traffic onto the other street; try both."))
        return ranked


class Agent:
    def __init__(self, runner, planner: Planner | None = None, budget=6, log=print, on_event=None):
        self.runner = runner
        self.planner = planner or StateMachinePlanner()
        self.state = RunState(budget=budget)
        self.log = log
        self.on_event = on_event  # structured alternative to log (used by --bundle)
        self._t0 = time.time()
        if hasattr(self.planner, "emit"):  # LLM planners report their calls as events
            self.planner.emit = self.emit

    # --- events ---------------------------------------------------------------------

    def emit(self, type_, **payload):
        event = {"seq": len(self.state.events), "t": round(time.time() - self._t0, 2),
                 "phase": self.state.phase.value, "type": type_, **payload}
        self.state.events.append(event)
        if self.on_event:
            self.on_event(event, _format_event(event))
        else:
            self.log(_format_event(event))

    def enter(self, phase):
        self.state.phase = phase
        self.emit("phase_started")

    # --- main loop ------------------------------------------------------------------

    def run(self, max_steps=30):
        s = self.state
        self.emit("run_started", policy=scenarios.policy_label(),
                  planner=self.planner.name, runner=self.runner.name, budget=s.budget, seeds=list(config.SEEDS))

        self.enter(Phase.RESEARCH)
        s.evidence = _load_evidence()
        for card in s.evidence:
            self.emit("evidence_found", card=card)

        self.enter(Phase.HYPOTHESES)
        s.brief = network_brief()
        self.emit("network_brief", brief=s.brief)
        for h in self.planner.plan_hypotheses(s.evidence, s.brief):
            Scenario.parse(h.experiment_id)  # hypotheses may only point at catalogue entries
            s.hypotheses.append(h)
            self.emit("hypothesis_created", hypothesis=asdict(h))

        self.enter(Phase.BASELINE)
        self._baseline("DN")

        self.enter(Phase.POLICY_TEST)
        for _ in range(max_steps):
            if s.used >= s.budget and s.phase != Phase.REPORT:
                self.emit("budget_exhausted", used=s.used)
                break
            d = self.planner.decide(s)
            self.emit("decision", planner=self.planner.name, decision=_decision_dict(d))
            if d.action == "stop":
                break
            if d.action == "next_phase":
                if d.next_phase not in TRANSITIONS.get(s.phase, ()):
                    self.emit("decision_rejected", reason=f"{s.phase.value} -> {d.next_phase} not allowed")
                    break
                if d.next_phase == Phase.REPORT:
                    break
                self.enter(d.next_phase)
                continue
            if d.experiment_id not in s.remaining:
                self.emit("decision_rejected", reason=f"{d.experiment_id} is not an untested catalogue entry")
                break
            self._experiment(Scenario.parse(d.experiment_id), d.hypothesis_ids)

        self.enter(Phase.REPORT)
        return s

    # --- experiments ----------------------------------------------------------------

    def _baseline(self, demand):
        sid = f"quays:BASE.M0.{demand}"
        if sid in self.state.results:
            return
        runs = self.runner.run(Scenario.parse(sid))
        self.state.results[sid] = {"runs": runs, "label": scenarios.describe(Scenario.parse(sid))}
        self.emit("simulation_finished", experiment_id=sid, label=self.state.results[sid]["label"],
                  delay_vehh=round(sum(r["total_delay_vehh"] for r in runs) / len(runs), 1),
                  teleports=sum(r["teleports"] for r in runs))

    def _experiment(self, scenario, hypothesis_ids):
        s = self.state
        self.emit("experiment_selected", experiment_id=scenario.id, label=scenarios.describe(scenario),
                  hypothesis_ids=hypothesis_ids, budget_left=s.budget - s.used - 1)
        self._baseline(scenario.demand)
        runs = self.runner.run(scenario)
        result = metrics.compare(s.results[scenario.baseline.id]["runs"], runs)
        result["label"] = scenarios.describe(scenario)
        s.results[scenario.id] = result
        self.emit("simulation_finished", experiment_id=scenario.id, label=result["label"],
                  goals=result["goals"], robust_violations=result["robust_violations"],
                  runtime_s=round(sum(r["runtime_s"] for r in runs), 1))
        for v in result["violations"]:
            if v["robust"]:
                self.emit("violation_detected", experiment_id=scenario.id, violation=v)

        if scenario.mitigation != "M0" and scenario.demand == "DN":
            self._verify_mitigation(scenario, result)
        self._update_hypotheses(scenario.id)

    def _verify_mitigation(self, scenario, result):
        """PLAN.md §8: fixes the target violation, keeps the goal, creates nothing new."""
        policy = self.state.results[NOMINAL]
        targeted = {k for k in policy["robust_violations"] if k.startswith("C1:")}
        remaining = targeted & set(result["robust_violations"])
        new = [v["key"] for v in result["violations"]
               if v["robust"] and v["key"] not in policy["robust_violations"] and v["severity"] != "minor"]
        verified = not remaining and result["goals"]["G1"]["met"] and not new
        self.state.mitigations[scenario.mitigation] = {
            "experiment_id": scenario.id, "verified": verified, "still_violated": sorted(remaining), "new": new}
        self.emit("mitigation_verified" if verified else "mitigation_rejected",
                  experiment_id=scenario.id, still_violated=sorted(remaining), new_violations=new,
                  goal_met=result["goals"]["G1"]["met"])

    def _update_hypotheses(self, experiment_id):
        result = self.state.results[experiment_id]
        for h in self.state.hypotheses:
            if h.experiment_id != experiment_id or h.status != "open":
                continue
            if h.check == "G1":
                observed = result["goals"]["G1"]["met"]
            elif h.check == "verified":
                observed = self.state.mitigations[Scenario.parse(experiment_id).mitigation]["verified"]
            else:
                observed = h.check in result["robust_violations"]
            h.status = "supported" if observed == h.expect else "refuted"
            self.emit("hypothesis_updated", hypothesis_id=h.id, status=h.status)


def network_brief():
    """The text-only network context an LLM planner would get (it cannot see the map)."""
    streets = network.load_streets()
    sites = scenarios.load_sites()
    return {
        "target": scenarios.target_label(),
        "closed_direction": "eastbound",
        "detour_ranking": [
            {"street": name, "detour_paths": n, "road_class": streets[name]["road_class"],
             "length_m": streets[name]["length_m"]}
            for name, n in sites["ranking"][:5]
        ],
        "sites": {k: v for k, v in sites.items() if k.startswith("F")},
        "restricted": list(scenarios.BASE_RESTRICTED_STREETS),
    }


def _load_evidence():
    return json.loads((config.DATA / "evidence.json").read_text())["cards"]


def _decision_dict(d):
    out = asdict(d)
    out["next_phase"] = d.next_phase.value if d.next_phase else None
    return out


def _format_event(e):
    t, kind = f"[{e['t']:6.1f}s]", e["type"]
    if kind == "phase_started":
        return f"\n{t} == {e['phase'].upper()} =="
    if kind == "evidence_found":
        return f"{t} evidence {e['card']['id']}: {e['card']['claim']}"
    if kind == "hypothesis_created":
        h = e["hypothesis"]
        return f"{t} hypothesis {h['id']}: {h['text']}  (settled by {h['experiment_id']})"
    if kind == "decision":
        d = e["decision"]
        what = d["experiment_id"] or d["next_phase"] or ""
        return f"{t} decision [{e['planner']}] {d['action']} {what} — {d['rationale']}"
    if kind == "simulation_finished":
        extra = f" robust violations: {e['robust_violations'] or 'none'}" if "robust_violations" in e else ""
        return f"{t} simulated {e['experiment_id']} ({e['label']}).{extra}"
    if kind == "violation_detected":
        v = e["violation"]
        where = f" on {v['street']}" if v["street"] else ""
        return f"{t}   ! {v['constraint']}{where}: {v['base']} -> {v['value']} ({v['severity']}, {v['seeds_hit']}/{v['seeds']} seeds)"
    if kind in ("mitigation_verified", "mitigation_rejected"):
        verdict = "VERIFIED" if kind == "mitigation_verified" else "rejected"
        return (f"{t} mitigation {e['experiment_id']} {verdict}; still violated: {e['still_violated'] or 'none'};"
                f" new: {e['new_violations'] or 'none'}")
    if kind == "hypothesis_updated":
        return f"{t} {e['hypothesis_id']} -> {e['status']}"
    if kind == "network_brief":
        ranking = ", ".join(f"{r['street']} ({r['detour_paths']})" for r in e["brief"]["detour_ranking"])
        return f"{t} network brief: streets on shortest detours (paths): {ranking}"
    if kind == "experiment_selected":
        return f"{t} running {e['experiment_id']} × {len(config.SEEDS)} seeds (budget left after: {e['budget_left']})"
    if kind == "llm_call":
        return (f"{t}   llm {e['step']}: {e['model']} {e['latency_s']}s "
                f"({e['prompt_tokens']} in / {e['completion_tokens']} out tokens)")
    if kind == "llm_error":
        return f"{t}   llm {e['step']} error (attempt {e['attempt']}): {e['error']}"
    if kind == "fallback_used":
        return f"{t}   ! {e['step']}: falling back to the {e['planner']} planner"
    if kind == "run_started":
        return f"{t} crash test: {e['policy']} | planner={e['planner']} runner={e['runner']} budget={e['budget']}"
    return f"{t} {kind} {({k: v for k, v in e.items() if k not in ('seq', 't', 'phase', 'type', 'brief')})}"
