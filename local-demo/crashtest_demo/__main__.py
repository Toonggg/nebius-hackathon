"""CLI: python -m crashtest_demo {prepare | streets [NAME] | warm | catalogue | sim ID | watch ID | run}.

Most people want ../crashtest.py instead: it loads .env and runs this in a Token Factory
Sandbox or locally.
"""

import argparse
import base64
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict

import sumolib

from . import config, network, report, scenarios
from .agent import NOMINAL, Agent
from .plot import delta_map
from .runner import LocalRunner, sim_args
from .scenarios import Scenario


def prepare(args):
    sites = network.prepare(force=args.rebuild)
    print(f"Network: {config.NET_FILE.relative_to(config.ROOT)}")
    print(f"Policy target: {scenarios.target_label()} -> edges {scenarios.target_edges()}")
    for code, site in sites.items():
        print(f"Mitigation site {code}: modal filter on {site['street']} (edges {site['edges']})")


def warm(args):
    """Build every scenario network and demand file (no simulations). Used when baking the sandbox image."""
    from . import demand

    for s in scenarios.catalogue():
        scenarios.scenario_net(s)
    for seed in config.SEEDS:
        for d in scenarios.DEMAND_SCALE:
            demand.trips_file(seed, d)
    print(f"warm: {len(scenarios.catalogue())} scenario nets, {len(config.SEEDS) * 3} demand files")


def streets(args):
    """Street names in the network, for filling in scenario.json (policy.street / from / to)."""
    data = network.load_streets()
    if not args.name:
        rows = sorted(((s["length_m"], n, s["road_class"]) for n, s in data.items()
                       if not n.startswith("(unnamed")), reverse=True)
        for length, name, road_class in rows[:args.top]:
            print(f"{length:7.0f} m  {road_class:28} {name}")
        return
    if args.name not in data:
        raise SystemExit(f"No street named {args.name!r}. Run without a name to list them.")
    net = sumolib.net.readNet(str(config.NET_FILE))
    e2s = network.edge_to_street()
    for e in data[args.name]["edges"]:
        edge = net.getEdge(e)
        crossing = sorted({e2s[x.getID()] for n in (edge.getFromNode(), edge.getToNode())
                           for x in n.getIncoming() + n.getOutgoing()
                           if x.getID() in e2s and e2s[x.getID()] != args.name})
        print(f"{e:16} {edge.getFromNode().getID()} -> {edge.getToNode().getID()}  crosses: {', '.join(crossing)}")


def catalogue(args):
    for s in scenarios.catalogue():
        print(f"{s.id:22} {scenarios.describe(s)}")


def sim(args):
    scenario = Scenario.parse(args.experiment_id)
    runner = LocalRunner()
    runs = runner.run(scenario)
    for r in runs:
        print({k: v for k, v in r.items() if k not in ("edge_volume", "street_volume")})
    if scenario.policy != "BASE":
        from .metrics import compare

        result = compare(runner.run(scenario.baseline), runs)
        print(json.dumps({k: v for k, v in result.items() if k != "edge_delta"}, indent=1, ensure_ascii=False))


def watch(args):
    """Open sumo-gui on one experiment + seed, with the same inputs and options as the agent's run."""
    scenario = Scenario.parse(args.experiment_id)
    cmd = [sumolib.checkBinary("sumo-gui"), *sim_args(scenario, args.seed),
           "--gui-settings-file", str(config.DATA / "gui-settings.xml"),
           "--delay", str(args.delay), "--start", "--window-size", "1400,1000"]
    if args.print:
        print(shlex.join(cmd))
        return
    print(f"{scenario.id} seed {args.seed}: {scenarios.describe(scenario)}")
    closed = sorted(set(scenarios.closed_edges(scenario)) - set(scenarios.base_restricted_edges()))
    if closed:
        print(f"Closed by this scenario: {', '.join(closed)} (find them in the GUI with Locate > Edges)")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as err:
        raise SystemExit(f"sumo-gui exited with {err.returncode}. On macOS it needs XQuartz "
                         "(brew install --cask xquartz, then log out and back in).")


def run(args):
    if args.fresh:
        shutil.rmtree(config.WORK / "results", ignore_errors=True)
    out = config.RUNS / args.name
    shutil.rmtree(out, ignore_errors=True)
    (out / "maps").mkdir(parents=True)

    # --bundle: stdout carries one JSON document (run + report + maps); stderr carries one JSON
    # event per line as it happens, with a human-readable "msg". That's how crashtest.py and the
    # Lovable edge function follow a run and collect its results.
    on_event = None
    if args.bundle:
        def on_event(event, msg):
            print(json.dumps({**event, "msg": msg}, ensure_ascii=False, default=str), file=sys.stderr, flush=True)
    runner = LocalRunner()
    runner.name = args.runner_label or runner.name
    state = Agent(runner, planner=_planner(args.planner), budget=args.budget, on_event=on_event).run()
    run_json = write_outputs(state, out)
    if args.bundle:
        maps = {k: base64.b64encode((out / v).read_bytes()).decode() for k, v in run_json["maps"].items()}
        scenario = config.scenario_subset([k for k in config.SCENARIO if not k.startswith("_")])
        scenario["policy_label"] = scenarios.policy_label()
        json.dump({"scenario": scenario, "run": run_json, "report_md": (out / "report.md").read_text(),
                   "maps_png_base64": maps}, sys.stdout, ensure_ascii=False, default=str)
        return
    print(f"\nVerdict: {run_json['verdict']}")
    print(f"Report:  {(out / 'report.md').relative_to(config.ROOT)}")
    print(f"Events:  {(out / 'run.json').relative_to(config.ROOT)}")


def _planner(choice):
    if choice == "rules" or (choice == "auto" and not os.environ.get("NEBIUS_API_KEY")):
        return None  # Agent defaults to StateMachinePlanner
    from .nemotron import NemotronPlanner

    return NemotronPlanner()


def write_outputs(state, out):
    """Maps, report.md and run.json for a finished agent run. Also used by --bundle (sandbox runs)."""
    maps = {}
    for exp_id, result in state.results.items():
        if exp_id == NOMINAL or (exp_id in {m["experiment_id"] for m in state.mitigations.values()}):
            png = out / "maps" / (exp_id.replace(":", "_").replace(".", "_") + ".png")
            delta_map(result, Scenario.parse(exp_id), png)
            maps[exp_id] = png.relative_to(out).as_posix()

    report.write(state, out, maps)
    state.events.append({"seq": len(state.events), "type": "report_ready", "path": "report.md"})
    run_json = {
        "events": state.events,
        "hypotheses": [asdict(h) for h in state.hypotheses],
        "mitigations": state.mitigations,
        "maps": maps,
        # Raw per-seed edge volumes are left in work/; the run file keeps the comparisons.
        "experiments": {k: v for k, v in state.results.items() if not scenarios.is_baseline(k)},
        "verdict": report.verdict(state),
    }
    (out / "run.json").write_text(json.dumps(run_json, indent=1, ensure_ascii=False, default=str))
    return run_json


def main():
    p = argparse.ArgumentParser(prog="crashtest_demo")
    sub = p.add_subparsers(required=True)
    a = sub.add_parser("prepare", help="bring data/ in line with scenario.json (network + mitigation sites)")
    a.add_argument("--rebuild", action="store_true", help="re-download and rebuild everything")
    a.set_defaults(func=prepare)
    sub.add_parser("warm", help="build all scenario nets and demand files (no simulation)").set_defaults(func=warm)
    a = sub.add_parser("streets", help="list streets, or the cross streets along one (for scenario.json)")
    a.add_argument("name", nargs="?")
    a.add_argument("--top", type=int, default=40, help="how many streets to list (longest first)")
    a.set_defaults(func=streets)
    sub.add_parser("catalogue", help="list every experiment the agent may run").set_defaults(func=catalogue)
    a = sub.add_parser("sim", help="run one experiment (3 seeds) and print its metrics")
    a.add_argument("experiment_id")
    a.set_defaults(func=sim)
    a = sub.add_parser("watch", help="watch one experiment live in sumo-gui")
    a.add_argument("experiment_id")
    a.add_argument("--seed", type=int, default=config.SEEDS[0])
    a.add_argument("--delay", type=int, default=20, help="ms per simulation step (0 = as fast as possible)")
    a.add_argument("--print", action="store_true", help="print the sumo-gui command instead of running it")
    a.set_defaults(func=watch)
    a = sub.add_parser("run", help="run the agent end to end and write a report")
    a.add_argument("--budget", type=int, default=6, help="max policy experiments (baselines are free)")
    a.add_argument("--name", default="latest", help="output folder under runs/")
    a.add_argument("--fresh", action="store_true", help="ignore cached simulation results")
    a.add_argument("--planner", choices=["auto", "nemotron", "rules"], default="auto",
                   help="auto = Nemotron if NEBIUS_API_KEY is set, else the rule-based planner")
    a.add_argument("--bundle", action="store_true", help="print one JSON bundle to stdout, log to stderr")
    a.add_argument("--runner-label", help=argparse.SUPPRESS)  # "sandbox" when run inside one
    a.set_defaults(func=run)
    args = p.parse_args()
    if args.func is not prepare:
        config.require_current_data()
    args.func(args)


if __name__ == "__main__":
    main()
