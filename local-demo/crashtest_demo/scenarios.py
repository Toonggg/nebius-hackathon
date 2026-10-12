"""The finite experiment catalogue (PLAN.md §7, heavily trimmed).

Experiment IDs: ``quays:{policy}.{mitigation}.{demand}``, e.g. ``quays:FC.F1.DH``.

- policy:     BASE (no change) | FC (one quay segment closed to private cars, one direction)
- mitigation: M0 (none) | F1 / F2 (modal filter on the 1st / 2nd ranked detour street) | F12 (both)
- demand:     DL / DN / DH (x0.85 / x1.0 / x1.15 of the design-hour demand)

Mitigation sites are picked by a rule (shortest detours around the closure on the policy
network), never by looking at simulation results.
"""

import functools
import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import dataclass

import sumolib

from . import config, network

DEMAND_SCALE = {"DL": 0.85, "DN": 1.0, "DH": 1.15}
POLICIES = ("BASE", "FC")
MITIGATIONS = ("M0", "F1", "F2", "F12")

# Rue de Rivoli has been bus/taxi/bike-only since 2020 (PLAN.md §7). We only simulate
# private cars, so it is closed to them in every scenario, including the baseline.
BASE_RESTRICTED_STREETS = ("Rue de Rivoli",)

SITES_FILE = config.DATA / "sites.json"


@dataclass(frozen=True)
class Scenario:
    policy: str
    mitigation: str
    demand: str

    @property
    def id(self):
        return f"quays:{self.policy}.{self.mitigation}.{self.demand}"

    @property
    def baseline(self):
        return Scenario("BASE", "M0", self.demand)

    @classmethod
    def parse(cls, experiment_id):
        policy, mitigation, demand = experiment_id.split(":", 1)[1].split(".")
        s = cls(policy, mitigation, demand)
        if s not in catalogue():
            raise ValueError(f"{experiment_id} is not in the catalogue")
        return s


def catalogue():
    """Every experiment the agent may run. Mitigations only make sense with the policy."""
    out = [Scenario("BASE", "M0", d) for d in DEMAND_SCALE]
    out += [Scenario("FC", m, d) for m in MITIGATIONS for d in DEMAND_SCALE]
    return out


# --- network patches -------------------------------------------------------------------


def _edges_of(streets):
    data = network.load_streets()
    return [e for s in streets for e in data[s]["edges"]]


@functools.cache
def _base_net():
    return sumolib.net.readNet(str(config.NET_FILE))


def fringe_edges(net):
    """Car edges where trips enter (no car edge feeds them) or leave the network."""
    cars = [e for e in net.getEdges() if e.allows("passenger")]
    sources = [e for e in cars if not any(i.allows("passenger") for i in e.getIncoming())]
    sinks = [e for e in cars if not any(o.allows("passenger") for o in e.getOutgoing())]
    return sources, sinks


def target_edges():
    """Edges of TARGET_STREET from its junction with TARGET_BETWEEN[0] to TARGET_BETWEEN[1]."""
    net = _base_net()
    streets = network.load_streets()
    along = set(streets[config.TARGET_STREET]["edges"])

    def junctions(cross):
        return {n for e in streets[cross]["edges"] for n in (net.getEdge(e).getFromNode(), net.getEdge(e).getToNode())
                if any(x.getID() in along for x in n.getIncoming() + n.getOutgoing())}

    start, goal = (junctions(c) for c in config.TARGET_BETWEEN)
    picked = set()
    # Depth-first walk along the target street only, keeping the edges on start -> goal.
    stack = [(n, [], {n}) for n in start]
    while stack:
        node, path, seen = stack.pop()
        if node in goal and path:
            picked.update(path)
            continue
        for e in node.getOutgoing():
            if e.getID() in along and e.getToNode() not in seen:
                stack.append((e.getToNode(), path + [e.getID()], seen | {e.getToNode()}))
    if not picked:
        raise RuntimeError(f"No {config.TARGET_STREET} edges between {config.TARGET_BETWEEN}")
    return sorted(picked)


def target_label():
    return f"{config.TARGET_STREET} from {config.TARGET_BETWEEN[0]} to {config.TARGET_BETWEEN[1]}"


def policy_label():
    return f"{target_label()} closed to eastbound cars"


def base_restricted_edges():
    return _edges_of(BASE_RESTRICTED_STREETS)


def closed_edges(scenario):
    """Edges where private cars are not allowed in this scenario."""
    closed = list(base_restricted_edges())
    if scenario.policy == "FC":
        closed += target_edges()
    sites = load_sites()
    for i in ("1", "2"):
        if scenario.mitigation in (f"F{i}", "F12"):
            closed += sites[f"F{i}"]["edges"]
    return sorted(set(closed))


def closable_edges():
    """Every edge any scenario could close: trips must not start or end on these."""
    return set().union(*(closed_edges(s) for s in catalogue()))


def scenario_net(scenario):
    return _patched_net(closed_edges(scenario))


def _patched_net(closed):
    key = hashlib.sha1(json.dumps(closed).encode()).hexdigest()[:10]
    out = config.WORK / "nets" / f"{key}.net.xml.gz"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    patch = out.with_suffix("").with_suffix(".edg.xml")
    patch.write_text(
        "<edges>\n" + "".join(f'  <edge id="{e}" disallow="passenger"/>\n' for e in closed) + "</edges>\n"
    )
    subprocess.run(
        [sumolib.checkBinary("netconvert"), "-s", str(config.NET_FILE), "-e", str(patch),
         "-o", str(out), "--no-warnings"],
        check=True, capture_output=True,
    )
    return out


# --- mitigation site screening ---------------------------------------------------------


def screen_sites(top_n=2):
    """Rank residential streets by how many shortest detours around the closure use them.

    For every fringe-to-fringe car trip whose shortest path uses the quays today, find its
    shortest path on the closure network and count the residential streets it newly
    crosses. The filter for each chosen street goes on its longest segment (both
    directions), so residents can still reach every address from one side.
    """
    streets = network.load_streets()
    e2s = network.edge_to_street()
    target = set(target_edges())
    restricted = set(base_restricted_edges())
    base = sumolib.net.readNet(str(_patched_net(sorted(restricted))))
    closed = sumolib.net.readNet(str(_patched_net(sorted(target | restricted))))

    def is_residential(name):
        return name and streets[name]["residential"] and streets[name]["judged"]

    sources, sinks = fringe_edges(base)

    counts = Counter()
    for a in (e.getID() for e in sources):
        for b in (e.getID() for e in sinks):
            before, _ = base.getShortestPath(base.getEdge(a), base.getEdge(b), vClass="passenger")
            if not before or not target & {e.getID() for e in before}:
                continue
            after, _ = closed.getShortestPath(closed.getEdge(a), closed.getEdge(b), vClass="passenger")
            used_before = {e2s.get(e.getID()) for e in before}
            for name in {e2s.get(e.getID()) for e in after or []} - used_before:
                if is_residential(name):
                    counts[name] += 1
    ranking = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))  # ties: alphabetical
    sites = {}
    for i, (name, n) in enumerate(ranking[:top_n], start=1):
        longest = max(streets[name]["edges"], key=lambda e: closed.getEdge(e).getLength())
        edge = closed.getEdge(longest)
        pair = [longest] + [
            o.getID() for o in edge.getToNode().getOutgoing()
            if o.getToNode() == edge.getFromNode() and e2s.get(o.getID()) == name
        ]
        sites[f"F{i}"] = {"street": name, "edges": pair, "detour_paths": n}
    SITES_FILE.write_text(json.dumps({"ranking": ranking, **sites}, indent=1, ensure_ascii=False))
    return sites


def load_sites():
    if not SITES_FILE.exists():
        screen_sites()
    return json.loads(SITES_FILE.read_text())


def describe(scenario):
    """Plain-English label, used in events and the report."""
    sites = load_sites()
    policy = "baseline" if scenario.policy == "BASE" else policy_label()
    mit = {
        "M0": None,
        "F1": f"modal filter on {sites['F1']['street']}",
        "F2": f"modal filter on {sites['F2']['street']}",
        "F12": f"modal filters on {sites['F1']['street']} and {sites['F2']['street']}",
    }[scenario.mitigation]
    demand = {"DL": "low demand", "DN": "normal demand", "DH": "high demand"}[scenario.demand]
    return ", ".join(p for p in (policy, mit, demand) if p)
