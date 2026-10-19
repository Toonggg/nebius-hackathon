#!/usr/bin/env python3
"""City Policy Crash-Test: one command, one full run (SUMO simulations + Nemotron decisions).

    python3 crashtest.py                  # auto: Token Factory Sandbox if your project has access, else local SUMO
    python3 crashtest.py --sumo sandbox   # whole run inside a Token Factory Sandbox (needs only Python 3)
    python3 crashtest.py --sumo local     # SUMO on this machine (needs .venv, see README)
    python3 crashtest.py --planner rules  # no LLM: rule-based planner

Reads NEBIUS_API_KEY and NEBIUS_PROJECT_ID from .env next to this file. Writes runs/latest/
(report.md, run.json, maps/*.png), prints the verdict and, for Nemotron runs, refreshes the
web app's recorded run (lovable/public/demo/latest.json). If scenario.json changed, data/ is
rebuilt first.

In a sandbox the run is one Sandboxes operation on a prepared image (Python + SUMO + this code),
built once and tagged by a hash of the code and data. That one operation is also what the Lovable
app starts on click (lovable/supabase/functions/crashtest-run). Standard library only.
"""

import argparse
import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPLAY_FILE = ROOT / "lovable/public/demo/latest.json"  # the recorded run the web app replays
SANDBOX_API = "https://api.tokenfactory.nebius.com/sandboxes/v1"
BASE_IMAGE = "docker://docker.io/library/python:3.12-slim"
IMAGE_FILES = ["requirements.txt", "scenario.json", "crashtest_demo/*.py", "data/*"]  # what goes into the sandbox image
RUN_TIMEOUT_S = 1800
# Image recipe. The SUMO wheel's binaries need a few system libraries the slim image lacks
# (X11/GL even for headless sumo). Part of the image fingerprint, so editing it forces a rebuild.
IMAGE_SETUP = (
    "set -e; apt-get update -qq && apt-get install -y -qq --no-install-recommends "
    "libexpat1 libatomic1 libx11-6 libxext6 libxrender1 libgl1 >/dev/null && rm -rf /var/lib/apt/lists/*; "
    "mkdir -p /app && tar -xzf /tmp/src.tgz -C /app && rm /tmp/src.tgz && cd /app && "
    "pip install --no-cache-dir -q --root-user-action=ignore -r requirements.txt && python -m crashtest_demo warm"
)
LATEST_TAG = "crashtest-sumo:latest"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--sumo", choices=["auto", "sandbox", "local"], default="auto")
    p.add_argument("--planner", choices=["auto", "nemotron", "rules"], default="auto",
                   help="auto = Nemotron if NEBIUS_API_KEY is set")
    p.add_argument("--budget", type=int, default=6, help="max policy experiments (baselines are free)")
    p.add_argument("--rebuild-image", action="store_true", help="rebuild the sandbox image even if it exists")
    args = p.parse_args()
    load_env(ROOT / ".env")
    ensure_prepared()

    where = args.sumo
    if where == "auto":
        ok, why = sandbox_access()
        where = "sandbox" if ok else "local"
        print(f"SUMO runs {'in a Token Factory Sandbox' if ok else 'locally'} ({why})", flush=True)
    if where == "sandbox":
        run_in_sandbox(args)
    else:
        run_locally(args)


# --- scenario ----------------------------------------------------------------------------


def ensure_prepared():
    """If scenario.json changed since data/ was built, rebuild data/ (needs the local venv)."""
    scenario = json.loads((ROOT / "scenario.json").read_text())
    strip = lambda v: {k: strip(x) for k, x in v.items() if not k.startswith("_")} if isinstance(v, dict) else v  # noqa: E731
    want = {k: strip(scenario[k]) for k in ("bbox", "residential_road_types", "policy", "always_closed_to_cars")}
    built_file = ROOT / "data/built_for.json"
    if built_file.exists() and json.loads(built_file.read_text()) == want:
        return
    python = ROOT / ".venv/bin/python"
    if not python.exists():
        sys.exit("scenario.json changed: data/ must be rebuilt, which needs the local venv (see README).")
    print("scenario.json changed: rebuilding data/ (network, streets, mitigation sites) ...", flush=True)
    if subprocess.run([str(python), "-m", "crashtest_demo", "prepare"], cwd=ROOT).returncode:
        sys.exit("prepare failed; fix scenario.json (see AGENTS.md) and try again.")


# --- local -------------------------------------------------------------------------------


def run_locally(args):
    python = ROOT / ".venv/bin/python"
    if not python.exists():
        sys.exit("Local SUMO needs the venv: uv venv --python 3.12 .venv && "
                 "uv pip install --python .venv/bin/python -r requirements.txt")
    cmd = [str(python), "-m", "crashtest_demo", "run", "--bundle", "--fresh", "--planner", args.planner,
           "--budget", str(args.budget)]
    # Same --bundle protocol as in a sandbox: events on stderr, the result bundle on stdout (to a
    # temp file, so a large bundle can't block the pipe while we read events).
    with tempfile.TemporaryFile() as out:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=out, stderr=subprocess.PIPE, text=True)
        for line in proc.stderr:
            show(line)
        if proc.wait() != 0:
            sys.exit(f"Run failed (exit {proc.returncode}); see the output above.")
        out.seek(0)
        save_bundle(json.load(out))


# --- Token Factory Sandboxes -------------------------------------------------------------


def run_in_sandbox(args):
    tag = ensure_image(force=args.rebuild_image)
    env = {k: os.environ[k] for k in ("NEBIUS_API_KEY", "TOKEN_FACTORY_BASE_URL", "MODEL_REASONING", "MODEL_MAIN")
           if os.environ.get(k)}
    command = (f"cd /app && python -m crashtest_demo run --bundle --runner-label sandbox "
               f"--planner {args.planner} --budget {int(args.budget)}")
    print(f"Running the crash test in a sandbox ({tag}) ...")
    op = api("POST", "/instances", {
        "image": f"tag:{tag}", "command": command, "shell": True, "env": env,
        "disposable": True, "timeout": RUN_TIMEOUT_S, "truncate_output_at": 10 * 1024 * 1024,
    })
    result = wait(op["uuid"], stream_stderr=True)
    save_bundle(json.loads(stream_text(result, "stdout")))


def ensure_image(force=False):
    """Tag of a sandbox image with Python, SUMO, this code and data, built once per content hash."""
    archive, digest = source_archive()
    tag = f"crashtest-sumo:{digest[:12]}"
    if not force and image_exists(tag):
        return tag
    print(f"Building sandbox image {tag} (one-off, a few minutes) ...")
    base = wait(api("POST", "/images/import", {"registry": {"url": BASE_IMAGE}, "timeout": 900})["uuid"])
    if not base.get("result_image_uuid"):
        sys.exit(f"Importing {BASE_IMAGE} returned no image: {json.dumps(base)[:500]}")
    upload = api("POST", "/files", raw=archive)
    op = api("POST", "/instances", {
        "image": base["result_image_uuid"], "command": IMAGE_SETUP, "shell": True, "disposable": False,
        "timeout": 1200, "files": {"/tmp/src.tgz": {"uuid": upload["uuid"], "mode": "0644"}},
    })
    built = wait(op["uuid"], stream_stderr=True)
    if not built.get("result_image_uuid"):
        sys.exit("Image build produced no image; see the output above.")
    for name in (tag, LATEST_TAG):  # the Lovable edge function always runs LATEST_TAG
        api("PATCH", f"/images/{built['result_image_uuid']}/tag", {"tag": name})
    return tag


def source_archive():
    """Deterministic .tgz of the files the sandbox needs (never .env) and its sha256."""
    files = sorted({f for pattern in IMAGE_FILES for f in ROOT.glob(pattern) if f.is_file()})
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=6) as tar:
        for f in files:
            info = tarfile.TarInfo(f.relative_to(ROOT).as_posix())
            info.size, info.mode, info.mtime = f.stat().st_size, 0o644, 0
            with f.open("rb") as fh:
                tar.addfile(info, fh)
    digest = hashlib.sha256(IMAGE_SETUP.encode() + BASE_IMAGE.encode() +
                            b"".join(f.relative_to(ROOT).as_posix().encode() + f.read_bytes() for f in files))
    return buf.getvalue(), digest.hexdigest()


def image_exists(tag):
    try:
        api("GET", f"/inspect/?tag={urllib.parse.quote(tag)}")
        return True
    except ApiError as err:
        if err.code == 302:  # found: redirects to the image
            return True
        if err.code == 404:
            return False
        raise


def wait(op_id, stream_stderr=False):
    """Poll an operation to a terminal state; optionally echo its stderr live. Ctrl-C cancels it."""
    shown, deadline = 0, time.time() + RUN_TIMEOUT_S + 300
    try:
        while True:
            op = api("GET", f"/operations/{op_id}" + ("?inflight=1" if stream_stderr else ""))
            if stream_stderr:
                lines = stream_text(op, "stderr").split("\n")[:-1]  # complete lines only
                for line in lines[shown:]:
                    show(line)
                shown = len(lines)
            if op["status"] in ("SUCCESS", "FAILED", "CANCELLED"):
                break
            if time.time() > deadline:
                sys.exit(f"Gave up waiting for operation {op_id}")
            time.sleep(2)
    except KeyboardInterrupt:
        api("DELETE", f"/operations/{op_id}")
        sys.exit(f"\nCancelled operation {op_id}")
    state = (result_of(op).get("state") or {})
    if op["status"] != "SUCCESS" or state.get("exit_code") not in (0, None) or state.get("timed_out"):
        sys.exit(f"Operation {op_id} ended {op['status']} (exit {state.get('exit_code')}, "
                 f"timed out: {state.get('timed_out')}): {op.get('error') or stream_text(op, 'stderr')[-2000:]}")
    return op


def result_of(op):
    return (op.get("metadata") or {}).get("result") or op.get("result") or {}


def stream_text(op, name):
    stream = result_of(op).get(name) or {}
    value = stream.get("value") or ""
    return base64.b64decode(value).decode(errors="replace") if stream.get("encoding") == "base64" else value


def show(line):
    """Print one --bundle event line (JSON with a "msg"); anything else (e.g. a traceback) as is."""
    line = line.rstrip("\n")
    try:
        print(json.loads(line)["msg"], flush=True)
    except (ValueError, KeyError, TypeError):
        print(line, flush=True)


def save_bundle(bundle, out=ROOT / "runs" / "latest"):
    shutil.rmtree(out, ignore_errors=True)
    (out / "maps").mkdir(parents=True)
    (out / "run.json").write_text(json.dumps(bundle["run"], indent=1, ensure_ascii=False))
    (out / "report.md").write_text(bundle["report_md"])
    for exp_id, png in bundle["maps_png_base64"].items():
        (out / bundle["run"]["maps"][exp_id]).write_bytes(base64.b64decode(png))
    print(f"\nVerdict: {bundle['run']['verdict']}\nReport:  {(out / 'report.md').relative_to(ROOT)}")
    # The web app should show the real agent: only runs where Nemotron made the decisions replace it.
    if bundle["run"]["events"][0].get("planner") == "nemotron":
        REPLAY_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPLAY_FILE.write_text(json.dumps(bundle, ensure_ascii=False))
        print(f"Web app replay updated: {REPLAY_FILE.relative_to(ROOT)}")
    else:
        print(f"Web app replay NOT updated (no Nemotron in this run): {REPLAY_FILE.relative_to(ROOT)}")


def sandbox_access():
    if not (os.environ.get("NEBIUS_API_KEY") and os.environ.get("NEBIUS_PROJECT_ID")):
        return False, "NEBIUS_API_KEY / NEBIUS_PROJECT_ID not set"
    try:
        perms = api("GET", "/whoami").get("permissions", {})
    except (ApiError, urllib.error.URLError) as err:
        return False, f"Sandboxes not reachable: {err}"
    if not (perms.get("spawn") and perms.get("import")):
        return False, "your project has no Sandboxes access yet"
    return True, "Sandboxes access OK"


class ApiError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(f"HTTP {code}: {message}")
        self.code = code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # surface 302s (image found by tag) as HTTPError


_opener = urllib.request.build_opener(_NoRedirect)


def api(method, path, body=None, raw=None):
    headers = {"Authorization": f"Bearer {os.environ['NEBIUS_API_KEY']}",
               "Project": os.environ["NEBIUS_PROJECT_ID"]}
    data = raw
    if body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    elif raw is not None:
        headers["Content-Type"] = "application/octet-stream"
    req = urllib.request.Request(SANDBOX_API + path, data=data, method=method, headers=headers)
    try:
        with _opener.open(req, timeout=120) as resp:
            text = resp.read().decode()
    except urllib.error.HTTPError as err:
        raise ApiError(err.code, err.read().decode(errors="replace")[:500]) from None
    return json.loads(text) if text.strip() else {}


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.strip().startswith("#"):
            os.environ.setdefault(key.strip(), value.split(" #")[0].strip().strip("'\""))


if __name__ == "__main__":
    main()
