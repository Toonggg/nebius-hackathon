#!/usr/bin/env python3
"""The full crash test, cloud only: python3 cloud_crashtest.py [--planner rules] [--budget N]

Like cloud_minimal.py, but runs the real agent on the case in scenario.json. Your machine needs
only Python 3 and .env (NEBIUS_API_KEY, NEBIUS_PROJECT_ID); no local SUMO, even after editing
scenario.json:

1. Once: a Sandboxes image with the SUMO runtime (system libraries + requirements.txt),
   tagged by a hash of both, so it's rebuilt only when requirements change.
2. Every run uploads the current code, data/ and scenario.json (~0.6 MB), then one sandbox
   operation runs JOB: `prepare` (rebuilds the road network if scenario.json changed; a new
   area is downloaded from OpenStreetMap inside the sandbox), then the agent (Nemotron + SUMO).
3. The agent's events stream to this terminal. The result lands in runs/latest/ (and the web
   app's recorded run, for Nemotron runs); a network rebuilt in the cloud is copied back to data/.

crashtest.py does the same with the code baked into the image (that's what the web app's
"Run live" uses) and can also run locally.
"""

import argparse
import base64
import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

import crashtest as ct  # sandbox API helpers, output handling

SETUP = (  # SUMO's binaries need these system libraries even headless; then the Python deps
    "set -e; apt-get update -qq && apt-get install -y -qq --no-install-recommends "
    "libexpat1 libatomic1 libx11-6 libxext6 libxrender1 libgl1 >/dev/null && rm -rf /var/lib/apt/lists/*; "
    "pip install -q --no-cache-dir --root-user-action=ignore -r /tmp/requirements.txt"
)

# Runs in the sandbox, in the unpacked source. stdout: one JSON {bundle, data_tgz?}; stderr: events.
JOB = r'''
import base64, hashlib, io, json, subprocess, sys, tarfile
from pathlib import Path
digest = lambda: hashlib.sha256(b"".join(p.read_bytes() for p in sorted(Path("data").glob("*")))).hexdigest()
before = digest()
subprocess.run([sys.executable, "-m", "crashtest_demo", "prepare"], check=True, stdout=sys.stderr)
run = subprocess.run([sys.executable, "-m", "crashtest_demo", "run", "--bundle", "--fresh",
                      "--runner-label", "sandbox", *sys.argv[1:]], check=True, stdout=subprocess.PIPE)
out = {"bundle": json.loads(run.stdout)}
if digest() != before:  # scenario changed: send the rebuilt network back
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add("data")
    out["data_tgz"] = base64.b64encode(buf.getvalue()).decode()
print(json.dumps(out, ensure_ascii=False))
'''


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--planner", choices=["auto", "nemotron", "rules"], default="auto")
    p.add_argument("--budget", type=int, default=6)
    args = p.parse_args()
    ct.load_env(ct.ROOT / ".env")

    image = runtime_image()
    source, _ = ct.source_archive()  # requirements, scenario.json, crashtest_demo/*.py, data/* (never .env)
    upload = ct.api("POST", "/files", raw=source)
    print("Running the crash test in a sandbox ...", flush=True)
    command = ("set -e; mkdir -p /job && tar -xzf /tmp/src.tgz -C /job && cd /job && "
               f"python3 - --planner {args.planner} --budget {int(args.budget)} <<'PY'\n{JOB}\nPY")
    op = ct.api("POST", "/instances", {
        "image": image, "command": command, "shell": True, "disposable": True,
        "env": {k: os.environ[k] for k in ("NEBIUS_API_KEY", "MODEL_REASONING", "MODEL_MAIN") if os.environ.get(k)},
        "files": {"/tmp/src.tgz": {"uuid": upload["uuid"], "mode": "0644"}},
        "timeout": ct.RUN_TIMEOUT_S, "truncate_output_at": 10 * 1024 * 1024,
    })
    result = json.loads(ct.stream_text(ct.wait(op["uuid"], stream_stderr=True), "stdout"))
    ct.save_bundle(result["bundle"])
    if "data_tgz" in result:
        replace_data(base64.b64decode(result["data_tgz"]))


def runtime_image():
    """Tag of the SUMO runtime image, built once per (setup, requirements)."""
    requirements = (ct.ROOT / "requirements.txt").read_bytes()
    tag = "crashtest-runtime:" + hashlib.sha256(SETUP.encode() + requirements).hexdigest()[:12]
    if ct.image_exists(tag):
        return f"tag:{tag}"
    print(f"Building the SUMO runtime image {tag} (one-off, about a minute) ...", flush=True)
    base = ct.wait(ct.api("POST", "/images/import", {"registry": {"url": ct.BASE_IMAGE}, "timeout": 900})["uuid"])
    req = ct.api("POST", "/files", raw=requirements)
    built = ct.wait(ct.api("POST", "/instances", {
        "image": base["result_image_uuid"], "command": SETUP, "shell": True, "disposable": False, "timeout": 1200,
        "files": {"/tmp/requirements.txt": {"uuid": req["uuid"], "mode": "0644"}},
    })["uuid"], stream_stderr=True)
    ct.api("PATCH", f"/images/{built['result_image_uuid']}/tag", {"tag": tag})
    return f"tag:{tag}"


def replace_data(tgz):
    """Swap in the data/ the sandbox rebuilt for the new scenario.json (validated, then swapped whole)."""
    with tempfile.TemporaryDirectory(dir=ct.ROOT) as tmp, tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz") as tar:
        for m in tar.getmembers():  # only plain files and folders under data/ (works on Python < 3.12 too)
            parts = Path(m.name).parts
            if not (m.isfile() or m.isdir()) or m.name.startswith("/") or ".." in parts or parts[0] != "data":
                raise SystemExit(f"Unexpected entry in the data archive from the sandbox: {m.name!r}")
        tar.extractall(tmp)
        shutil.rmtree(ct.ROOT / "data")
        shutil.move(str(Path(tmp) / "data"), str(ct.ROOT / "data"))
    print("data/ updated: the cloud rebuilt the road network for the changed scenario.json")


if __name__ == "__main__":
    main()
