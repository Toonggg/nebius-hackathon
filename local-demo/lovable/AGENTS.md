# AGENTS.md: Crash-Test web app

Rules for coding agents (including Lovable) working on the web app built from these files. The
simulation engine lives elsewhere: `local-demo/` in https://github.com/Toonggg/nebius-hackathon
(its own `AGENTS.md` covers changing the scenario).

- **Scenario-agnostic UI.** Never hard-code a city, street, policy or evidence text. Read it from
  `bundle.scenario` (`Scenario` in `src/lib/crashtest.ts`). A new scenario arrives as a new
  `public/demo/latest.json`, and the UI must show it with no code change.
- **Use `src/lib/crashtest.ts` as the only data layer:** `loadRecordedRun`, `replayRun`,
  `startLiveRun`, `mapSrc`. Don't call the Sandboxes API from the browser.
- **Don't change the types** in `crashtest.ts` unless the engine's output changed. They mirror what the
  engine writes. `EVENT_TYPES` lists every event and its fields.
- **`supabase/functions/crashtest-run/index.ts`** holds the API key server-side (secrets
  `NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID`). Keep keys out of client code and out of the repo.
- **Live runs can fail** (no Sandboxes access, quota). Always fall back to the recorded run, with a
  short notice.
- **`public/demo/latest.json` is generated** by the engine's `crashtest.py`. Replace it; never edit it.
- The page spec is in `CRASHTEST_PROMPT.md`.
