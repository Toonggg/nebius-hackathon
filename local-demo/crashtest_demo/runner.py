"""SimRunner: turn an experiment ID + seeds into raw SUMO measurements.

Only ``LocalRunner`` exists in the demo: SUMO runs as a subprocess and every file it
reads or writes lives under ``local-demo/work/``. PLAN.md's ``OracleRunner`` (lookup of
precomputed results) and ``SandboxRunner`` (Token Factory Sandboxes) would implement the
same ``run()`` method; see NEBIUS.md.
"""

import importlib.metadata
import json
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

import sumolib

from . import config, demand, network, scenarios

COOLDOWN_S = 1200  # let trips finish after the last departure


class SimRunner(Protocol):
    name: str

    def run(self, scenario: scenarios.Scenario, seeds=config.SEEDS) -> list[dict]:
        """One result dict per seed (see ``_parse`` for the fields)."""


class LocalRunner:
    name = "local"

    def __init__(self, workers=None):
        self.workers = workers or min(len(config.SEEDS), os.cpu_count() or 1)

    def run(self, scenario, seeds=config.SEEDS):
        """Raw per-seed measurements; cached under work/results/ by experiment ID + seed."""
        # Build networks and demand up front: the SUMO tools step on each other's temp
        # files when several run at once. Only the simulations themselves run in parallel.
        scenarios.scenario_net(scenario)
        for seed in seeds:
            demand.trips_file(seed, scenario.demand)
        with ThreadPoolExecutor(self.workers) as pool:
            return list(pool.map(lambda s: self._run_one(scenario, s), seeds))

    def _run_one(self, scenario, seed):
        out_dir = config.WORK / "results" / scenario.id.replace(":", "_") / f"s{seed}"
        result_file = out_dir / "result.json"
        if result_file.exists():
            return json.loads(result_file.read_text())
        out_dir.mkdir(parents=True, exist_ok=True)

        begin, end = demand.WARMUP_S, demand.WARMUP_S + config.SIM_SECONDS
        (out_dir / "edgedata.add.xml").write_text(
            f'<additional><edgeData id="design_hour" file="edgedata.xml" begin="{begin}" end="{end}"'
            ' excludeEmpty="true"/></additional>\n'
        )
        cmd = [
            sumolib.checkBinary("sumo"), *sim_args(scenario, seed),
            "-a", str(out_dir / "edgedata.add.xml"),
            "--tripinfo-output", str(out_dir / "tripinfo.xml"), "--tripinfo-output.write-unfinished",
            "--statistic-output", str(out_dir / "stats.xml"),
            "--no-step-log", "--no-warnings", "--duration-log.disable",
        ]
        t0 = time.time()
        subprocess.run(cmd, check=True, capture_output=True)
        result = _parse(out_dir, scenario, seed)
        result["runtime_s"] = round(time.time() - t0, 2)
        result_file.write_text(json.dumps(result))
        return result


def sim_args(scenario, seed):
    """SUMO options shared by the measured runs and the GUI (``watch``), so both match."""
    return [
        "-n", str(scenarios.scenario_net(scenario)),
        "-r", str(demand.trips_file(seed, scenario.demand)),
        "--begin", "0", "--end", str(demand.WARMUP_S + config.SIM_SECONDS + COOLDOWN_S),
        "--seed", str(seed),
        # PLAN.md §7: half the drivers adapt their route every 2 minutes.
        "--device.rerouting.probability", "0.5", "--device.rerouting.period", "120",
        "--time-to-teleport", "300", "--ignore-route-errors",
    ]


def _parse(out_dir, scenario, seed):
    edge_entered = {}
    for edge in ET.parse(out_dir / "edgedata.xml").getroot().iter("edge"):
        edge_entered[edge.get("id")] = int(float(edge.get("entered", 0)))

    street_volume = {}
    for name, street in network.load_streets().items():
        # A street's volume is its busiest link (veh/h), so long streets aren't over-counted.
        street_volume[name] = max((edge_entered.get(e, 0) for e in street["edges"]), default=0)

    delay_s = 0.0
    for trip in ET.parse(out_dir / "tripinfo.xml").getroot().iter("tripinfo"):
        delay_s += float(trip.get("timeLoss", 0)) + float(trip.get("departDelay", 0))

    stats = ET.parse(out_dir / "stats.xml").getroot()
    veh = stats.find("vehicles").attrib
    tele = stats.find("teleports").attrib
    trip_stats = stats.find("vehicleTripStatistics").attrib
    loaded, inserted = int(veh["loaded"]), int(veh["inserted"])
    running, waiting = int(veh["running"]), int(veh["waiting"])
    delay_s += float(trip_stats.get("departDelayWaiting", 0) or 0) * waiting

    return {
        "experiment_id": scenario.id,
        "seed": seed,
        "edge_volume": edge_entered,
        "street_volume": street_volume,
        "target_volume": max(edge_entered.get(e, 0) for e in scenarios.target_edges()),
        "loaded": loaded,
        "inserted": inserted,
        "no_route": loaded - inserted - waiting,  # trips with no legal route in the study area
        "unfinished": running + waiting,
        "teleports": int(tele["total"]),
        "total_delay_vehh": round(delay_s / 3600, 2),
        "sumo_version": importlib.metadata.version("eclipse-sumo"),
    }
