"""Paths and constants for the local demo. Everything stays inside local-demo/."""

import os
from pathlib import Path

import sumo  # the eclipse-sumo wheel; importing it gives us SUMO_HOME

os.environ.setdefault("SUMO_HOME", sumo.SUMO_HOME)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"  # committed inputs: filtered OSM + built network
WORK = ROOT / "work"  # SUMO scratch: scenario nets, demand, raw outputs (gitignored)
RUNS = ROOT / "runs"  # agent run outputs: events.json, report.md, map PNG

# Hôtel de Ville / Quai de Gesvres / Quai de l'Hôtel de Ville / southern Marais.
# Much smaller than the ~3.9 km² area in PLAN.md §7 so a run takes seconds.
BBOX = (2.3460, 48.8515, 2.3640, 48.8610)  # W, S, E, N (~1.3 x 1.1 km)

OSM_FILE = DATA / "hdv.osm.xml.gz"
NET_FILE = DATA / "net.net.xml.gz"
STREETS_FILE = DATA / "streets.json"

SIM_SECONDS = 3600  # one design hour
SEEDS = (1, 2, 3)
BOUNDARY_BUFFER_M = 60  # streets this close to the edge of the network are not judged

# The policy: a scaled-down version of PLAN.md's headline "close the upper quays". Eastbound
# cars can no longer drive along Quai de l'Hôtel de Ville from the first cross street to the
# second; westbound stays open. Closing both directions (or the whole quay) in an area this
# small leaves the eastbound through traffic no detour, and SUMO gridlocks at any demand.
TARGET_STREET = "Quai de l'Hôtel de Ville"
TARGET_BETWEEN = ("Rue de Brosse", "Pont Louis-Philippe")  # closed in this direction of travel
