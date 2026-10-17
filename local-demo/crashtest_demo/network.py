"""Fetch the OSM extract, build the SUMO network and index its streets (all for scenario.json)."""

import gzip
import html
import json
import subprocess
import urllib.parse
import urllib.request

import sumolib

from . import config

OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
QUERY = '[out:xml][timeout:60];(way["highway"]({s},{w},{n},{e}););(._;>;);out body;'


def fetch_osm(force=False):
    """Download every highway way in the bbox (plus its nodes) from Overpass, gzipped."""
    if config.OSM_FILE.exists() and not force:
        return config.OSM_FILE
    config.DATA.mkdir(parents=True, exist_ok=True)
    w, s, e, n = config.BBOX
    body = urllib.parse.urlencode({"data": QUERY.format(w=w, s=s, e=e, n=n)}).encode()
    for url in OVERPASS_MIRRORS:
        req = urllib.request.Request(url, data=body, headers={"User-Agent": "crashtest-local-demo/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
        except OSError as err:
            print(f"Overpass mirror {url} failed: {err}")
            continue
        if b"<osm" in data[:500]:  # a busy server answers 200 with an HTML error page
            with gzip.open(config.OSM_FILE, "wb") as f:
                f.write(data)
            return config.OSM_FILE
        print(f"Overpass mirror {url} is busy")
    raise RuntimeError("All Overpass mirrors failed; try again in a minute")


def prepare(force=False):
    """Bring data/ in line with scenario.json, redoing only what changed. Returns the mitigation sites.

    bbox changed           -> download roads from OpenStreetMap, rebuild the SUMO network
    road types changed     -> re-index streets
    policy/closures changed -> re-screen the mitigation sites (scenarios.screen_sites)
    """
    from . import scenarios  # scenarios imports network

    built = json.loads(config.BUILT_FOR_FILE.read_text()) if config.BUILT_FOR_FILE.exists() else {}
    want = config.scenario_subset(config.NETWORK_FIELDS + config.SITE_FIELDS)
    new_area = force or built.get("bbox") != want["bbox"] or not config.NET_FILE.exists()
    if new_area:
        fetch_osm(force=True)
        build_net(force=True)
    elif built.get("residential_road_types") != want["residential_road_types"]:
        index_streets()
    sites = scenarios.screen_sites()
    config.BUILT_FOR_FILE.write_text(json.dumps(want, indent=1, ensure_ascii=False) + "\n")
    return sites


def build_net(force=False):
    """netconvert flags follow PLAN.md §7 (street names kept for per-street aggregation)."""
    if config.NET_FILE.exists() and not force:
        return config.NET_FILE
    fetch_osm()
    subprocess.run(
        [
            sumolib.checkBinary("netconvert"),
            "--osm-files", str(config.OSM_FILE),
            "--keep-edges.by-vclass", "passenger,taxi,bus",
            "--remove-edges.isolated", "--geometry.remove", "--roundabouts.guess", "--junctions.join",
            "--tls.guess-signals", "--tls.discard-simple", "--tls.join", "--osm.lane-access",
            "--output.street-names", "--output.original-names",
            "--no-turnarounds.except-deadend",
            "--no-warnings",
            "-o", str(config.NET_FILE),
        ],
        check=True,
    )
    index_streets()
    return config.NET_FILE


def index_streets():
    """Write streets.json: street name -> edges, road class, residential flag, judged flag."""
    net = sumolib.net.readNet(str(config.NET_FILE))
    (xmin, ymin), (xmax, ymax) = net.getBBoxXY()
    buf = config.BOUNDARY_BUFFER_M
    streets = {}
    for edge in net.getEdges():
        if not edge.allows("passenger"):
            continue
        name = html.unescape(edge.getName()) or f"(unnamed {edge.getID()})"
        x, y = sumolib.geomhelper.positionAtShapeOffset(edge.getShape(), edge.getLength() / 2)
        near_boundary = x < xmin + buf or x > xmax - buf or y < ymin + buf or y > ymax - buf
        road_class = edge.getType().replace("highway.", "")
        s = streets.setdefault(name, {"edges": [], "classes": set(), "length_m": 0.0, "interior_edges": 0})
        s["edges"].append(edge.getID())
        s["classes"].add(road_class)
        s["length_m"] += edge.getLength()
        s["interior_edges"] += 0 if near_boundary else 1
    out = {}
    for name, s in sorted(streets.items()):
        classes = sorted(s["classes"])
        out[name] = {
            "edges": s["edges"],
            "road_class": classes[0] if len(classes) == 1 else "/".join(classes),
            "residential": all(c in config.SCENARIO["residential_road_types"] for c in classes),
            "judged": s["interior_edges"] > 0 and not name.startswith("(unnamed"),
            "length_m": round(s["length_m"], 1),
        }
    config.STREETS_FILE.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def load_streets():
    return json.loads(config.STREETS_FILE.read_text())


def edge_to_street():
    return {e: name for name, s in load_streets().items() for e in s["edges"]}
