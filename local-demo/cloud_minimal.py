#!/usr/bin/env python3
"""Minimal cloud example: SUMO simulates and Nemotron judges, both on Nebius Token Factory.

    python3 cloud_minimal.py

One self-contained file, standard library only, independent of crashtest_demo/. It shows the
mechanism crashtest.py uses, on a toy 5x5 street grid instead of Paris:

1. Once: build a Sandboxes image with SUMO (tag sumo-minimal:1, about a minute).
2. One sandbox operation runs JOB below: generate a grid, simulate 1,000 car trips for an hour
   with and without one closed street, then ask Nemotron (Token Factory) to judge the closure.
3. This machine only starts the operation, waits, and prints the JSON result.

Needs NEBIUS_API_KEY and NEBIUS_PROJECT_ID (from .env next to this file) with Sandboxes access.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.tokenfactory.nebius.com/sandboxes/v1"
IMAGE_TAG = "sumo-minimal:1"
SETUP = (  # system libraries the SUMO binaries need, then SUMO itself
    "set -e; apt-get update -qq && apt-get install -y -qq --no-install-recommends "
    "libexpat1 libatomic1 libx11-6 libxext6 libxrender1 libgl1 >/dev/null; "
    "pip install -q --no-cache-dir --root-user-action=ignore eclipse-sumo==1.28.0"
)

# Runs inside the sandbox: SUMO twice, then the LLM judge. Prints one JSON object.
JOB = r'''
import json, os, subprocess, sys, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
import sumo
bin_, tools = Path(sumo.SUMO_HOME) / "bin", Path(sumo.SUMO_HOME) / "tools"
run = lambda *cmd: subprocess.run([str(c) for c in cmd], check=True, capture_output=True)

run(bin_ / "netgenerate", "--grid", "--grid.number", 5, "--grid.length", 200, "-o", "grid.net.xml")
run(sys.executable, tools / "randomTrips.py", "-n", "grid.net.xml", "-o", "trips.xml", "--seed", 1,
    "-e", 3600, "--insertion-rate", 1000, "--fringe-factor", 10, "--validate")
Path("closed.edg.xml").write_text('<edges><edge id="B2C2" disallow="passenger"/></edges>')
run(bin_ / "netconvert", "-s", "grid.net.xml", "-e", "closed.edg.xml", "-o", "closed.net.xml")

def simulate(net):
    run(bin_ / "sumo", "-n", net, "-r", "trips.xml", "--statistic-output", "stats.xml", "--no-step-log",
        "--tripinfo-output", "tripinfo.xml",  # trip statistics are only collected with tripinfo on
        "--ignore-route-errors", "--time-to-teleport", 300, "--device.rerouting.probability", 0.5)
    stats = ET.parse("stats.xml").getroot()
    trips = stats.find("vehicleTripStatistics").attrib
    return {"trips": int(trips["count"]), "mean_trip_s": round(float(trips["duration"]), 1),
            "mean_delay_s": round(float(trips["timeLoss"]), 1),
            "teleports": int(stats.find("teleports").get("total"))}

results = {"baseline": simulate("grid.net.xml"), "street_B2C2_closed": simulate("closed.net.xml")}

schema = {"type": "object", "required": ["verdict", "reason"], "properties": {
    "verdict": {"enum": ["acceptable", "unacceptable"]}, "reason": {"type": "string"}}}
body = {"model": "nvidia/nemotron-3-super-120b-a12b", "temperature": 0, "max_tokens": 2000,
        "response_format": {"type": "json_schema", "json_schema": {"name": "judgement", "schema": schema}},
        "messages": [{"role": "user", "content": "A city closes one street in a grid to cars. SUMO measured "
                      "this (mean_delay_s = time lost per trip vs free flow, teleports = jammed cars removed):\n"
                      + json.dumps(results) + "\nIs the closure acceptable for traffic? Use only these "
                      "numbers. One-sentence reason. Reply as JSON."}]}
req = urllib.request.Request("https://api.tokenfactory.nebius.com/v1/chat/completions",
                             data=json.dumps(body).encode(), headers={
                                 "Authorization": "Bearer " + os.environ["NEBIUS_API_KEY"],
                                 "Content-Type": "application/json"})
reply = json.load(urllib.request.urlopen(req, timeout=180))
results["nemotron_judge"] = json.loads(reply["choices"][0]["message"]["content"])
results["nemotron_tokens"] = reply["usage"]["total_tokens"]
print(json.dumps(results, indent=1))
'''


def main():
    load_env(Path(__file__).with_name(".env"))
    t0 = time.time()
    image = f"tag:{IMAGE_TAG}" if image_exists() else build_image()
    print("Running SUMO + Nemotron judge in a sandbox ...", flush=True)
    op = api("POST", "/instances", {
        "image": image, "command": f"cd /tmp && python3 - <<'PY'\n{JOB}\nPY", "shell": True,
        "env": {"NEBIUS_API_KEY": os.environ["NEBIUS_API_KEY"]},  # for the judge call; not stored
        "disposable": True, "timeout": 900,
    })
    result = wait(op["uuid"])
    print(output(result, "stdout"))
    print(f"Done in {time.time() - t0:.0f} s (operation {op['uuid']})")


def build_image():
    print(f"Building image {IMAGE_TAG} (one-off, about a minute) ...", flush=True)
    base = wait(api("POST", "/images/import", {"registry": {"url": "docker://docker.io/library/python:3.12-slim"},
                                               "timeout": 900})["uuid"])
    built = wait(api("POST", "/instances", {"image": base["result_image_uuid"], "command": SETUP, "shell": True,
                                             "disposable": False, "timeout": 900})["uuid"])
    api("PATCH", f"/images/{built['result_image_uuid']}/tag", {"tag": IMAGE_TAG})
    return built["result_image_uuid"]


def image_exists():
    try:
        api("GET", f"/inspect/?tag={IMAGE_TAG}")
        return True
    except urllib.error.HTTPError as err:
        if err.code in (302, 404):
            return err.code == 302  # 302 = found (redirect to the image)
        raise


def wait(op_id):
    """Poll an operation until it ends; exit with its output if the command failed."""
    while (op := api("GET", f"/operations/{op_id}"))["status"] not in ("SUCCESS", "FAILED", "CANCELLED"):
        time.sleep(2)
    state = ((op.get("metadata") or {}).get("result") or {}).get("state") or {}
    if op["status"] != "SUCCESS" or state.get("exit_code") not in (0, None):
        sys.exit(f"Operation {op_id} ended {op['status']} (exit {state.get('exit_code')}):\n"
                 f"{op.get('error') or ''}{output(op, 'stderr')[-2000:]}")
    return op


def output(op, stream):
    s = ((op.get("metadata") or {}).get("result") or {}).get(stream) or {}
    if s.get("encoding") == "base64":
        import base64
        return base64.b64decode(s.get("value") or "").decode(errors="replace")
    return s.get("value") or ""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def api(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {os.environ['NEBIUS_API_KEY']}",
                                          "Project": os.environ["NEBIUS_PROJECT_ID"],
                                          "Content-Type": "application/json"})
    with urllib.request.build_opener(_NoRedirect).open(req, timeout=120) as resp:
        text = resp.read().decode()
    return json.loads(text) if text.strip() else {}


def load_env(path):
    for line in path.read_text().splitlines() if path.exists() else []:
        key, sep, value = line.partition("=")
        if sep and not key.strip().startswith("#"):
            os.environ.setdefault(key.strip(), value.split(" #")[0].strip().strip("'\""))


if __name__ == "__main__":
    main()
