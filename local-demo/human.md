# Quick review: how the demo is put together

**One file defines the case: `scenario.json`.** City, study area, which street closes (and in which
direction), streets that are always car-free, traffic volume, pass/fail thresholds, and the
evidence cards. Nothing about Paris is hard-coded anywhere else.

```
scenario.json  ──►  crashtest.py  ──►  runs/latest/report.md            (read this)
  (the case)         (one run)         lovable/public/demo/latest.json  (the web app shows this)
```

## Change the case in 3 steps

1. **Edit `scenario.json`.** Or ask a coding agent: "Change the scenario to closing X between Y and Z
   in <city>". `AGENTS.md` tells it exactly how.
2. **Run `python3 crashtest.py`.** It notices the change, rebuilds the road network and the
   mitigation sites, simulates, lets Nemotron decide, and writes the report.
3. **Copy `lovable/public/demo/latest.json` into the Lovable project.** The web app reads every label
   from that file, so nothing else in the app changes.

Step 2 runs in the cloud and also refreshes the sandbox image that the web app's "Run live" button uses.
No local SUMO installed? Run `python3 cloud_crashtest.py` first: it rebuilds the road network in the cloud
and copies it back. Then `python3 crashtest.py` needs nothing local either.

## What's automatic and what isn't

| Automatic | By hand (or by the agent, per `AGENTS.md`) |
|---|---|
| Downloading roads, building the network | Picking a sensible area and real street names |
| Choosing where mitigation filters go | Tuning the traffic volume so the baseline isn't jammed |
| Report, maps, web-app labels | Rewriting the evidence cards for the new case |
| Rebuilding the sandbox image (when run) | Updating the prose in README.md, GUIDE.md, WATCH.md |

**Limit:** the policy is always "close one stretch of one street to cars, in one direction", and the
fixes are modal filters on the two most-used detour streets. Other policy types need code changes
(`AGENTS.md`, "change the demo's structure").

**Tested:** switching the policy to Quai des Célestins (westbound) by editing only `scenario.json`
gave a different, plausible verdict. Switching back reproduced the Paris results exactly.

## Where to look

| File | What |
|---|---|
| `scenario.json` | The case |
| `crashtest.py` | The one command |
| `GUIDE.md` | How to read a run and its result |
| `AGENTS.md` | Instructions for coding agents (scenario changes, structure, contracts) |
| `crashtest_demo/` | The engine (Python) |
| `lovable/` | The web app's files (copied into Lovable as-is) |
