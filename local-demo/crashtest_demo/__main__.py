"""CLI: python -m crashtest_demo {prepare | catalogue | sim ID | watch ID | run}."""

import argparse
import json
import shlex
import shutil
import subprocess
from dataclasses import asdict

import sumolib

from . import config, network, report, scenarios
from .agent import NOMINAL, Agent
from .plot import delta_map
from .runner import LocalRunner, sim_args
from .scenarios import Scenario


def prepare(args):
    network.build_net(force=args.rebuild)
    sites = scenarios.screen_sites()
    print(f"Network: {config.NET_FILE.relative_to(config.ROOT)}")
    print(f"Policy target: {scenarios.target_label()} -> edges {scenarios.target_edges()}")
    for code, site in sites.items():
        print(f"Mitigation site {code}: modal filter on {site['street']} (edges {site['edges']})")


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

    state = Agent(LocalRunner(), budget=args.budget).run()

    maps = {}
    for exp_id, result in state.results.items():
        if exp_id == NOMINAL or (exp_id in {m["experiment_id"] for m in state.mitigations.values()}):
            png = out / "maps" / (exp_id.replace(":", "_").replace(".", "_") + ".png")
            delta_map(result, Scenario.parse(exp_id), png)
            maps[exp_id] = png.relative_to(out).as_posix()

    report_path = report.write(state, out, maps)
    state.events.append({"seq": len(state.events), "type": "report_ready", "path": "report.md"})
    run_json = {
        "events": state.events,
        "hypotheses": [asdict(h) for h in state.hypotheses],
        "mitigations": state.mitigations,
        # Raw per-seed edge volumes are left in work/; the run file keeps the comparisons.
        "experiments": {k: v for k, v in state.results.items() if not k.startswith("quays:BASE")},
        "verdict": report.verdict(state),
    }
    (out / "run.json").write_text(json.dumps(run_json, indent=1, ensure_ascii=False, default=str))
    print(f"\nVerdict: {run_json['verdict']}")
    print(f"Report:  {report_path.relative_to(config.ROOT)}")
    print(f"Events:  {(out / 'run.json').relative_to(config.ROOT)}")


def main():
    p = argparse.ArgumentParser(prog="crashtest_demo")
    sub = p.add_subparsers(required=True)
    a = sub.add_parser("prepare", help="build the SUMO network and pick mitigation sites")
    a.add_argument("--rebuild", action="store_true", help="rebuild the network from the OSM file")
    a.set_defaults(func=prepare)
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
    a.set_defaults(func=run)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
