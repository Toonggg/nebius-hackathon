"""Policy Failure Report (markdown). Every number comes from the SUMO results.

In the real product, Nemotron Ultra writes the narrative with ``{{F12}}`` fact placeholders
(PLAN.md §6). Here the narrative is templated.
"""

import math

from . import config, demand, metrics, scenarios
from .agent import NOMINAL


def verdict(state):
    nominal = state.results.get(NOMINAL)
    if not nominal:
        return "INCOMPLETE: the policy test did not run."
    robust = [v for v in nominal["violations"] if v["robust"]]
    if not robust:
        return "No failure found within budget at normal demand."
    fixed = state.verified_mitigation()
    worst = ", ".join(_violation_name(v) for v in robust[:3])
    if fixed:
        return (f"FAILS AS PROPOSED ({worst}). Passes with the "
                f"{scenarios.describe(scenarios.Scenario('FC', fixed, 'DN')).split(', ')[1]}.")
    return f"FAILS ({worst}). No mitigation in the catalogue was verified within budget."


def _box_km():
    w, s, e, n = config.BBOX
    km_per_deg_lon = 111.32 * math.cos(math.radians((s + n) / 2))
    return f"{(e - w) * km_per_deg_lon:.1f} × {(n - s) * 110.57:.1f} km"


def _always_closed_line():
    streets = config.SCENARIO["always_closed_to_cars"]
    if not streets:
        return []
    why = config.SCENARIO.get("always_closed_reason")
    return [f"- {', '.join(streets)} {'is' if len(streets) == 1 else 'are'} closed to private cars in every "
            f"scenario, baseline included{f' ({why})' if why else ''}."]


def _run_line(s):
    start = s.events[0]
    calls = [e for e in s.events if e["type"] == "llm_call"]
    fallbacks = sum(e["type"] == "fallback_used" for e in s.events)
    line = (f"Planner: `{start['planner']}` · SUMO: `{start['runner']}` · Budget: {s.used}/{s.budget} "
            f"experiments · Seeds per experiment: {len(config.SEEDS)}")
    if calls:
        models = ", ".join(sorted({c["model"] for c in calls}))
        tokens = sum((c["prompt_tokens"] or 0) + (c["completion_tokens"] or 0) for c in calls)
        line += f" · LLM: {len(calls)} calls to {models}, {tokens:,} tokens"
    if fallbacks:
        line += f" · ⚠️ {fallbacks} step(s) fell back to the rule-based planner"
    return line


def _violation_name(v):
    names = {"C1": f"spillover on {v['street']}", "C2": "network delay", "C3": "gridlock"}
    return names[v["constraint"]]


def _fmt_violation(v):
    if v["constraint"] == "C1":
        lo, hi = v["delta_range"]
        return (f"**{v['street']}**: {v['base']:.0f} → {v['value']:.0f} cars/h (+{v['delta']:.0f}, "
                f"+{v['pct']:.0f}%; +{lo:.0f}…+{hi:.0f} across seeds)")
    if v["constraint"] == "C2":
        return f"**Network delay**: {v['base']:.0f} → {v['value']:.0f} veh·h (+{v['pct']:.0f}%)"
    return f"**Gridlock**: {v['value']:.0f} teleports on average (jammed vehicles SUMO had to remove)"


def write(state, out_dir, maps):
    s = state
    lines = [
        "# Policy Failure Report",
        "",
        f"**Policy:** {scenarios.policy_label()} (the opposite direction stays open).",
        "",
        f"**Verdict:** {verdict(s)}",
        "",
        _run_line(s),
        "",
        "## What we found",
        "",
    ]
    for exp_id, r in s.results.items():
        if scenarios.is_baseline(exp_id):
            continue
        robust = [v for v in r["violations"] if v["robust"]]
        lines.append(f"### `{exp_id}`: {r['label']}")
        lines.append("")
        g1 = r["goals"]["G1"]
        lines.append(f"- Goal G1 (target segment −{metrics.CONSTRAINTS['G1']['min_drop_pct']}%): "
                     f"{'met' if g1['met'] else 'NOT met'} ({r['target_volume']['base']:.0f} → "
                     f"{r['target_volume']['value']:.0f} cars/h)")
        lines.append(f"- Delay: {r['delay_vehh']['base']:.0f} → {r['delay_vehh']['value']:.0f} veh·h; "
                     f"teleports {r['teleports']:.0f}; unfinished trips {r['unfinished']:.0f}")
        if robust:
            lines += [f"- ⚠️ {v['severity']}: {_fmt_violation(v)}" for v in robust]
        else:
            lines.append("- No robust constraint violations.")
        if exp_id in maps:
            lines += ["", f"![{exp_id}]({maps[exp_id]})"]
        lines.append("")

    if s.mitigations:
        lines += ["## Mitigations tried", "", "| Mitigation | Verdict | Still violated | New violations |",
                  "|---|---|---|---|"]
        for code, m in s.mitigations.items():
            label = scenarios.describe(scenarios.Scenario("FC", code, "DN")).split(", ")[1]
            lines.append(f"| {label} | {'✅ verified' if m['verified'] else '❌ rejected'} | "
                         f"{', '.join(m['still_violated']) or '—'} | {', '.join(m['new']) or '—'} |")
        lines.append("")

    lines += ["## Hypotheses", "", "| ID | Hypothesis | Settled by | Evidence | Status |", "|---|---|---|---|---|"]
    for h in s.hypotheses:
        lines.append(f"| {h.id} | {h.text} | `{h.experiment_id}` | {', '.join(h.evidence) or '—'} | {h.status} |")
    lines.append("")

    lines += ["## Evidence (canned cards; no live Tavily search yet)", ""]
    lines += [f"- **[{c['id']}]** {c['claim']} — _{c['source']}_" for c in s.evidence]
    lines.append("")

    untested = [e for e in s.remaining]
    lines += [
        "## Assumptions and limitations",
        "",
        f"- Study area is a ~{_box_km()} box around {config.SCENARIO['area_name']}, {config.SCENARIO['city']} "
        f"(bbox {config.BBOX}); detours outside it are invisible to the model, which overstates local spillover.",
        f"- Demand is synthetic: {demand.TRIPS_PER_HOUR} random car trips/h at normal demand "
        f"(×{scenarios.DEMAND_SCALE['DL']} / ×{scenarios.DEMAND_SCALE['DH']} for low / high), biased to the "
        "network fringe. It is **not** calibrated to real traffic counts.",
        *_always_closed_line(),
        "- Only private cars are simulated: no buses, taxis, bikes or pedestrians.",
        "- Half of the drivers re-route every 2 minutes; nobody changes mode or time of travel, and no traffic "
        "evaporates (E1 suggests some would).",
        "- A street's volume is its busiest link. A violation is *robust* if it appears in at least "
        f"{metrics.ROBUST_SEEDS} of {len(config.SEEDS)} seeds.",
        f"- Untested catalogue entries ({len(untested)}): {', '.join(f'`{e}`' for e in untested) or 'none'}.",
        "",
        "Data: © OpenStreetMap contributors (ODbL). Simulation: Eclipse SUMO.",
    ]
    path = out_dir / "report.md"
    path.write_text("\n".join(lines) + "\n")
    return path
