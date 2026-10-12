"""Synthetic design-hour demand.

PLAN.md calibrates demand to Paris sensor counts with routeSampler. The demo skips that:
it draws random trips (biased towards the network fringe, so most of them are through
traffic) and then sanity-checks the baseline against the sensor means quoted in PLAN.md.
"""

import random
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import sumo

from . import config, scenarios

# Normal demand (DN), private cars. Roughly half of what the sensors in PLAN.md §7 imply:
# the study area is too small to carry more once the quay is cut (see README).
TRIPS_PER_HOUR = 1200
WARMUP_S = 300  # trips depart over WARMUP_S + SIM_SECONDS; only the last hour is measured
MAX_SCALE = max(scenarios.DEMAND_SCALE.values())


def trips_file(seed, demand):
    """Trips for one seed and demand level. DL ⊂ DN ⊂ DH, so comparisons stay paired."""
    out = config.WORK / "demand" / f"trips_s{seed}_{demand}.xml"
    if out.exists():
        return out
    full = _full_trips(seed)
    keep = scenarios.DEMAND_SCALE[demand] / MAX_SCALE
    rng = random.Random(f"{seed}-thin")
    tree = ET.parse(full)
    root = tree.getroot()
    for trip in list(root.findall("trip")):
        if rng.random() >= keep:
            root.remove(trip)
    tree.write(out, encoding="utf-8", xml_declaration=True)
    return out


def _full_trips(seed):
    """Highest-demand trip set for a seed; lower levels are seeded subsets of it."""
    out = config.WORK / "demand" / f"trips_s{seed}_full.xml"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = out.with_name(f"raw_s{seed}.xml")
    duration = WARMUP_S + config.SIM_SECONDS
    base_net = scenarios.scenario_net(scenarios.Scenario("BASE", "M0", "DN"))
    subprocess.run(
        [
            sys.executable, str(Path(sumo.SUMO_HOME) / "tools" / "randomTrips.py"),
            "-n", str(base_net), "-o", str(raw), "--seed", str(seed),
            "-b", "0", "-e", str(duration),
            "--insertion-rate", str(TRIPS_PER_HOUR * MAX_SCALE),
            "--fringe-factor", "20", "--min-distance", "250",
            "--vclass", "passenger", "--validate", "--remove-loops",
            "--prefix", f"s{seed}_",
        ],
        check=True, capture_output=True,
        cwd=out.parent,  # --validate drops a temporary routes.rou.xml into the working directory
    )
    # Keep only origin, destination and departure: SUMO routes each trip on the scenario
    # network at insertion time, so the same demand file serves every scenario.
    closable = scenarios.closable_edges()
    root = ET.Element("routes")
    for trip in ET.parse(raw).getroot().iter("trip"):
        if trip.get("from") in closable or trip.get("to") in closable:
            continue
        ET.SubElement(root, "trip", id=trip.get("id"), depart=trip.get("depart"),
                      **{"from": trip.get("from"), "to": trip.get("to")}, departLane="best", departSpeed="max")
    ET.ElementTree(root).write(out, encoding="utf-8", xml_declaration=True)
    for extra in [*raw.parent.glob(f"raw_s{seed}*"), raw.parent / "routes.rou.xml"]:
        extra.unlink(missing_ok=True)
    return out
