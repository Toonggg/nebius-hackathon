// Client for the City Policy Crash-Test backend.
//
// - loadRecordedRun(): the latest real run, bundled with the app (public/demo/latest.json).
//   Always works; use it for "Watch a recorded run" and as the fallback when live runs fail.
// - replayRun(): plays a recorded run's events back with their original timing.
// - startLiveRun(): starts a fresh run in a Token Factory Sandbox via the "crashtest-run" edge
//   function and streams its events. Fails until the Nebius project has Sandboxes access.
//
// Both paths produce the same Bundle, so the UI renders them identically.

import { supabase } from "@/integrations/supabase/client";

export type Phase = "research" | "hypotheses" | "baseline" | "policy_test" | "mitigation" | "robustness" | "report";

/** One agent event. `type` decides which other fields are present (see EVENT_TYPES). */
export interface RunEvent {
  seq: number;
  t?: number; // seconds since the run started
  phase?: Phase;
  type: string;
  [field: string]: unknown;
}

/** Event types and their extra fields, in roughly the order they appear. */
export const EVENT_TYPES = {
  run_started: "policy, planner ('nemotron' | 'state-machine'), runner ('local' | 'sandbox'), budget, seeds",
  phase_started: "(phase is the new phase)",
  evidence_found: "card: { id, source, claim, tags }",
  network_brief: "brief: { target, detour_ranking: [{ street, detour_paths, road_class, length_m }], sites }",
  llm_call: "step ('hypotheses' | 'decision'), model, latency_s, prompt_tokens, completion_tokens",
  llm_error: "step, model, attempt, error",
  fallback_used: "step, planner (the rule-based planner took over this step)",
  hypothesis_created: "hypothesis: Hypothesis",
  decision: "planner, decision: { action ('run' | 'next_phase' | 'stop'), experiment_id, next_phase, hypothesis_ids, rationale }",
  experiment_selected: "experiment_id, label, hypothesis_ids, budget_left",
  simulation_finished: "experiment_id, label, goals?, robust_violations?, delay_vehh?, teleports?, runtime_s?",
  violation_detected: "experiment_id, violation: Violation",
  mitigation_verified: "experiment_id, still_violated, new_violations, goal_met",
  mitigation_rejected: "experiment_id, still_violated, new_violations, goal_met",
  hypothesis_updated: "hypothesis_id, status ('supported' | 'refuted')",
  budget_exhausted: "used",
  report_ready: "path",
} as const;

export interface Hypothesis {
  id: string;
  text: string;
  experiment_id: string;
  check: string; // "G1" | "C1:<street>" | "C2" | "C3" | "verified"
  expect: boolean;
  evidence: string[]; // evidence card ids
  status: "open" | "supported" | "refuted";
}

/** C1 residential spillover, C2 network delay, C3 gridlock. Numbers are means across seeds. */
export interface Violation {
  key: string; // e.g. "C1:Rue de Brosse"
  constraint: "C1" | "C2" | "C3";
  street: string | null;
  base: number;
  value: number;
  delta: number;
  delta_range: [number, number];
  pct: number;
  severity: "minor" | "major" | "critical";
  seeds_hit: number;
  seeds: number;
  robust: boolean;
}

export interface Experiment {
  label: string;
  goals: { G1: { met: boolean; drop_pct: number } }; // G1: traffic on the closed segment falls ≥ 70%
  violations: Violation[];
  robust_violations: string[];
  target_volume: { base: number; value: number }; // cars/h on the closed segment
  delay_vehh: { base: number; value: number }; // total delay, vehicle-hours
  teleports: number;
  unfinished: number;
  top_increases: [string, number][]; // [street, Δ cars/h]
}

export interface Bundle {
  run: {
    events: RunEvent[];
    hypotheses: Hypothesis[];
    mitigations: Record<string, { experiment_id: string; verified: boolean; still_violated: string[]; new: string[] }>;
    maps: Record<string, string>; // experiment id -> file name (images are in maps_png_base64)
    experiments: Record<string, Experiment>; // policy experiments only (baselines omitted)
    verdict: string;
  };
  report_md: string; // the full Policy Failure Report (markdown; image links point at maps/*.png)
  maps_png_base64: Record<string, string>; // experiment id -> PNG of Δ cars/h per street
}

/** <img src> for an experiment's map, or undefined if it has none. */
export const mapSrc = (bundle: Bundle, experimentId: string) =>
  bundle.maps_png_base64[experimentId] ? `data:image/png;base64,${bundle.maps_png_base64[experimentId]}` : undefined;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function loadRecordedRun(): Promise<Bundle> {
  const res = await fetch("/demo/latest.json");
  if (!res.ok) throw new Error(`recorded run missing (${res.status})`);
  return res.json();
}

/** Calls onEvents with a growing list of events, paced by their timestamps (speed 2 = twice as fast). */
export async function replayRun(
  bundle: Bundle,
  onEvents: (events: RunEvent[]) => void,
  { speed = 1, signal }: { speed?: number; signal?: AbortSignal } = {},
): Promise<Bundle> {
  const events = bundle.run.events;
  let last = 0;
  for (let i = 0; i < events.length; i++) {
    if (signal?.aborted) throw new DOMException("aborted", "AbortError");
    const t = events[i].t ?? last;
    await sleep(Math.max(0, ((t - last) * 1000) / speed));
    last = t;
    onEvents(events.slice(0, i + 1));
  }
  return bundle;
}

/** Fresh run in a Token Factory Sandbox. Throws if it can't start (e.g. no Sandboxes access yet). */
export async function startLiveRun(
  onEvents: (events: RunEvent[]) => void,
  { signal }: { signal?: AbortSignal } = {},
): Promise<Bundle> {
  const start = await supabase.functions.invoke("crashtest-run", { body: {} });
  if (start.error || !start.data?.id) throw new Error(start.data?.error ?? start.error?.message ?? "could not start");
  for (;;) {
    await sleep(2000);
    if (signal?.aborted) throw new DOMException("aborted", "AbortError");
    const poll = await supabase.functions.invoke("crashtest-run", { body: { id: start.data.id } });
    if (poll.error) throw new Error(poll.error.message);
    onEvents(poll.data.events ?? []);
    if (poll.data.status === "SUCCESS" && poll.data.bundle) return poll.data.bundle as Bundle;
    if (poll.data.status === "FAILED") throw new Error(poll.data.error ?? "run failed");
  }
}
