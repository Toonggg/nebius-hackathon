"""Deltas vs baseline and constraint checks (PLAN.md §7, subset). Pure Python, no SUMO."""

from statistics import mean

from . import config, network

_checks = config.SCENARIO["checks"]  # thresholds; PLAN.md §7 defaults in the Paris scenario
CONSTRAINTS = {
    "G1": {"rule": "target-street car volume falls by at least", "min_drop_pct": _checks["G1_min_drop_pct"]},
    "C1": {"rule": "residential street rises by more than both", "pct": _checks["C1_min_pct"],
           "vehh": _checks["C1_min_cars_per_h"], "floor": 50},
    "C2": {"rule": "network delay rises by more than both", "pct": _checks["C2_min_pct"], "vehh": _checks["C2_min_vehh"]},
    "C3": {"rule": "gridlock: teleports or unfinished trips reach", "teleports_min": 10,
           "teleports_share": 0.005, "unfinished_share": 0.02},
}
ROBUST_SEEDS = 2  # a violation is robust if it happens in at least this many seeds


def _pct(base, new, floor=1):
    return 100.0 * (new - base) / max(base, floor)


def _check_seed(base, run, streets):
    """Return (goal results, violations) for one paired seed."""
    c1, c2, c3 = CONSTRAINTS["C1"], CONSTRAINTS["C2"], CONSTRAINTS["C3"]
    violations = []

    for name, s in streets.items():
        if not (s["residential"] and s["judged"]) or name == config.TARGET_STREET:
            continue
        b, n = base["street_volume"][name], run["street_volume"][name]
        delta, pct = n - b, _pct(b, n, c1["floor"])
        if delta > c1["vehh"] and pct > c1["pct"]:
            severity = min(delta / c1["vehh"], pct / c1["pct"])
            violations.append({"key": f"C1:{name}", "constraint": "C1", "street": name,
                               "base": b, "value": n, "delta": delta, "pct": pct, "severity": severity})

    d_delta = run["total_delay_vehh"] - base["total_delay_vehh"]
    d_pct = _pct(base["total_delay_vehh"], run["total_delay_vehh"])
    if d_delta > c2["vehh"] and d_pct > c2["pct"]:
        violations.append({"key": "C2", "constraint": "C2", "street": None, "base": base["total_delay_vehh"],
                           "value": run["total_delay_vehh"], "delta": d_delta, "pct": d_pct,
                           "severity": min(d_delta / c2["vehh"], d_pct / c2["pct"])})

    tele_limit = max(c3["teleports_min"], c3["teleports_share"] * run["inserted"])
    unfinished_share = run["unfinished"] / max(run["loaded"], 1)
    if run["teleports"] >= tele_limit or unfinished_share >= c3["unfinished_share"]:
        violations.append({"key": "C3", "constraint": "C3", "street": None, "base": base["teleports"],
                           "value": run["teleports"], "delta": run["teleports"] - base["teleports"],
                           "pct": 100 * unfinished_share, "severity": float("inf")})

    drop = -_pct(base["target_volume"], run["target_volume"])
    goals = {"G1": {"met": drop >= CONSTRAINTS["G1"]["min_drop_pct"], "drop_pct": drop}}
    return goals, violations


def _severity_class(constraint, severity):
    if constraint == "C3":
        return "critical"
    return "major" if severity >= 1.5 else "minor"


def compare(base_runs, runs):
    """Aggregate paired seeds into one ExperimentResult-like dict."""
    streets = network.load_streets()
    per_seed = [_check_seed(b, r, streets) for b, r in zip(base_runs, runs)]
    n = len(per_seed)

    by_key = {}
    for _, violations in per_seed:
        for v in violations:
            by_key.setdefault(v["key"], []).append(v)
    violations = []
    for key, hits in by_key.items():
        first = hits[0]
        violations.append({
            "key": key,
            "constraint": first["constraint"],
            "street": first["street"],
            "seeds_hit": len(hits),
            "seeds": n,
            "robust": len(hits) >= min(ROBUST_SEEDS, n),
            "base": round(mean(h["base"] for h in hits), 1),
            "value": round(mean(h["value"] for h in hits), 1),
            "delta": round(mean(h["delta"] for h in hits), 1),
            "delta_range": [round(min(h["delta"] for h in hits), 1), round(max(h["delta"] for h in hits), 1)],
            "pct": round(mean(h["pct"] for h in hits), 1),
            "severity": _severity_class(first["constraint"], min(h["severity"] for h in hits)),
        })
    violations.sort(key=lambda v: ({"critical": 0, "major": 1, "minor": 2}[v["severity"]], -v["delta"]))

    g1 = [g["G1"] for g, _ in per_seed]
    residential_deltas = {
        name: round(mean(r["street_volume"][name] - b["street_volume"][name] for b, r in zip(base_runs, runs)), 1)
        for name, s in streets.items() if s["residential"] and s["judged"]
    }
    return {
        "goals": {"G1": {"met": sum(g["met"] for g in g1) >= min(ROBUST_SEEDS, n),
                         "drop_pct": round(mean(g["drop_pct"] for g in g1), 1)}},
        "violations": violations,
        "robust_violations": [v["key"] for v in violations if v["robust"]],
        "target_volume": {"base": round(mean(b["target_volume"] for b in base_runs), 1),
                          "value": round(mean(r["target_volume"] for r in runs), 1)},
        "delay_vehh": {"base": round(mean(b["total_delay_vehh"] for b in base_runs), 1),
                       "value": round(mean(r["total_delay_vehh"] for r in runs), 1)},
        "teleports": round(mean(r["teleports"] for r in runs), 1),
        "unfinished": round(mean(r["unfinished"] for r in runs), 1),
        "no_route": round(mean(r["no_route"] for r in runs), 1),
        "top_increases": sorted(residential_deltas.items(), key=lambda kv: -kv[1])[:5],
        "edge_delta": {
            e: round(mean(r["edge_volume"].get(e, 0) - b["edge_volume"].get(e, 0) for b, r in zip(base_runs, runs)), 1)
            for e in set().union(*(r["edge_volume"] for r in runs + base_runs))
        },
    }
