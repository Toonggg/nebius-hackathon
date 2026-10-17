"""Paths and constants. The case itself (area, policy, demand, checks, evidence) comes from
../scenario.json; everything else here is engine settings. Everything stays inside local-demo/."""

import hashlib
import json
import os
from pathlib import Path

import sumo  # the eclipse-sumo wheel; importing it gives us SUMO_HOME

os.environ.setdefault("SUMO_HOME", sumo.SUMO_HOME)

ROOT = Path(__file__).resolve().parent.parent
SCENARIO_FILE = ROOT / "scenario.json"
SCENARIO = json.loads(SCENARIO_FILE.read_text())

BBOX = tuple(SCENARIO["bbox"])  # W, S, E, N
TARGET_STREET = SCENARIO["policy"]["street"]
TARGET_BETWEEN = (SCENARIO["policy"]["from"], SCENARIO["policy"]["to"])  # closed in this direction of travel
DIRECTION = SCENARIO["policy"]["direction"]

DATA = ROOT / "data"  # network built for the scenario (committed, rebuilt by `prepare`)
OSM_FILE = DATA / "osm.xml.gz"
NET_FILE = DATA / "net.net.xml.gz"
STREETS_FILE = DATA / "streets.json"
BUILT_FOR_FILE = DATA / "built_for.json"  # the scenario fields data/ was built from
RUNS = ROOT / "runs"  # agent run outputs

# Fields that change the network or the mitigation sites. If they differ from BUILT_FOR_FILE,
# data/ is stale and `python -m crashtest_demo prepare` must run first.
NETWORK_FIELDS = ("bbox", "residential_road_types")
SITE_FIELDS = ("policy", "always_closed_to_cars")
# Fields that change simulation results. work/ is keyed by them, so cached nets, demand and
# results never leak from one scenario into another.
SIM_FIELDS = NETWORK_FIELDS + SITE_FIELDS + ("demand",)


def scenario_subset(fields):
    """The given scenario fields without "_help"-style comment keys (editing those changes nothing)."""
    def strip(v):
        return {k: strip(x) for k, x in v.items() if not k.startswith("_")} if isinstance(v, dict) else v
    return {k: strip(SCENARIO[k]) for k in fields}


def _fingerprint(fields):
    return hashlib.sha1(json.dumps(scenario_subset(fields), sort_keys=True).encode()).hexdigest()[:10]


WORK = ROOT / "work" / f"{SCENARIO['id']}-{_fingerprint(SIM_FIELDS)}"  # SUMO scratch (gitignored)

SIM_SECONDS = 3600  # one design hour
SEEDS = (1, 2, 3)
BOUNDARY_BUFFER_M = 60  # streets this close to the edge of the network are not judged


def data_is_current():
    """True if data/ was built from the current scenario.json (network + mitigation sites)."""
    if not BUILT_FOR_FILE.exists():
        return False
    return json.loads(BUILT_FOR_FILE.read_text()) == scenario_subset(NETWORK_FIELDS + SITE_FIELDS)


def require_current_data():
    if not data_is_current():
        raise SystemExit("scenario.json changed since data/ was built. Run: "
                         ".venv/bin/python -m crashtest_demo prepare   (or just python3 crashtest.py)")
