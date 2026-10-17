"""Static PNG map of the change in traffic per street segment (the UI map, minus the UI)."""

import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

import sumolib  # noqa: E402

from . import config, network, scenarios  # noqa: E402


def delta_map(result, scenario, path, limit=200):
    net = sumolib.net.readNet(str(config.NET_FILE))
    closed = set(scenarios.closed_edges(scenario)) - set(scenarios.base_restricted_edges())
    restricted = set(scenarios.base_restricted_edges())
    cmap, norm = plt.get_cmap("RdBu_r"), TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)

    fig, ax = plt.subplots(figsize=(9, 8))
    for edge in net.getEdges():
        if not edge.allows("passenger"):
            continue
        xs, ys = zip(*edge.getShape())
        eid = edge.getID()
        delta = result["edge_delta"].get(eid, 0)
        if eid in closed:
            ax.plot(xs, ys, color="black", lw=4, ls=(0, (2, 1)), zorder=3)
        elif eid in restricted:
            ax.plot(xs, ys, color="#bbbbbb", lw=1, ls=":", zorder=1)
        elif abs(delta) < 10:
            ax.plot(xs, ys, color="#d9d9d9", lw=1, zorder=1)
        else:
            ax.plot(xs, ys, color=cmap(norm(max(-limit, min(limit, delta)))), lw=1.5 + 3 * min(abs(delta), limit) / limit,
                    zorder=2)

    spillover = [v for v in result["violations"] if v["robust"] and v["street"]]
    for i, v in enumerate(spillover):
        edges = [net.getEdge(e) for e in network.load_streets()[v["street"]]["edges"]]
        edge = max(edges, key=lambda e: e.getLength())
        x, y = sumolib.geomhelper.positionAtShapeOffset(edge.getShape(), edge.getLength() / 2)
        ax.annotate(f"{v['street']}\n+{v['delta']:.0f} veh/h", (x, y), fontsize=8, color="#7f0000",
                    xytext=(40, 50 - 45 * i), textcoords="offset points", arrowprops={"arrowstyle": "-", "color": "#7f0000"},
                    bbox={"boxstyle": "round", "fc": "white", "ec": "#7f0000", "alpha": 0.85}, zorder=4)

    if "C3" in result["robust_violations"]:
        ax.text(0.5, 0.02, "GRIDLOCK: flows fall because traffic is jammed, not because it went away",
                transform=ax.transAxes, ha="center", fontsize=9, color="white",
                bbox={"boxstyle": "round", "fc": "#b30000", "ec": "none"}, zorder=5)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    fig.colorbar(sm, ax=ax, shrink=0.6, label="Δ cars per hour vs baseline (mean of seeds)")
    ax.set_title(f"{scenario.id}\n" + textwrap.fill(scenarios.describe(scenario), 90), fontsize=10)
    ax.set_aspect("equal")
    ax.set_axis_off()
    always = ", ".join(scenarios.BASE_RESTRICTED_STREETS)
    ax.text(0.0, -0.02, "Black dashed: closed to cars. " + (f"Dotted: {always} (no cars in any scenario). " if always
            else "") + "© OpenStreetMap contributors (ODbL).", transform=ax.transAxes, fontsize=7, color="#555555")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path

