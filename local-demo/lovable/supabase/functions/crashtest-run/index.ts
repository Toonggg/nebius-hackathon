// Edge function "crashtest-run": starts one crash-test run in a Token Factory Sandbox and reports
// on it. The sandbox runs the whole agent (SUMO simulations + Nemotron decisions).
//
//   POST {}        -> { id }                                          start a run
//   POST { id }    -> { status, events, bundle, error }               poll every ~2 s
//
// status: PENDING | ASSIGNED | EXECUTING | SUCCESS | FAILED | CANCELLED
// events: every agent event so far (same shape as bundle.run.events), growing while it runs
// bundle: the full result once status is SUCCESS (see src/lib/crashtest.ts for the types)
//
// Secrets (Lovable Cloud → Secrets): NEBIUS_API_KEY, NEBIUS_PROJECT_ID.
// The sandbox image (crashtest-sumo:latest) is built and refreshed by `python3 crashtest.py` in the
// repo's local-demo/ folder. If starting a run fails (access, quota), the app shows the recorded run.
// Anyone who can call this function can start runs that spend Token Factory credits.

const API = "https://api.tokenfactory.nebius.com/sandboxes/v1";
const IMAGE = "tag:crashtest-sumo:latest";
const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

type Stream = { value?: string; encoding?: string };
const text = (s?: Stream) =>
  s?.encoding === "base64"
    ? new TextDecoder().decode(Uint8Array.from(atob(s.value ?? ""), (c) => c.charCodeAt(0)))
    : s?.value ?? "";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  const reply = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { ...cors, "Content-Type": "application/json" } });
  const key = Deno.env.get("NEBIUS_API_KEY");
  const project = Deno.env.get("NEBIUS_PROJECT_ID");
  if (!key || !project) return reply({ error: "NEBIUS_API_KEY / NEBIUS_PROJECT_ID secrets are not set" }, 500);
  const headers = { Authorization: `Bearer ${key}`, Project: project, "Content-Type": "application/json" };
  const { id } = await req.json().catch(() => ({}));

  if (!id) {
    const res = await fetch(`${API}/instances`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        image: IMAGE,
        command: "cd /app && python -m crashtest_demo run --bundle --runner-label sandbox",
        shell: true,
        env: { NEBIUS_API_KEY: key },
        disposable: true,
        timeout: 1800,
        truncate_output_at: 10 * 1024 * 1024,
      }),
    });
    if (!res.ok) return reply({ error: `Could not start a sandbox run (${res.status}): ${await res.text()}` }, 502);
    return reply({ id: (await res.json()).uuid });
  }

  const res = await fetch(`${API}/operations/${id}?inflight=1`, { headers });
  if (!res.ok) return reply({ error: `Status check failed (${res.status}): ${await res.text()}` }, 502);
  const op = await res.json();
  const result = op.metadata?.result ?? op.result ?? {};
  const stderr = text(result.stderr).split("\n");
  const events = stderr.flatMap((line) => {
    try {
      return [JSON.parse(line)];
    } catch {
      return [];
    }
  });
  const ok = op.status === "SUCCESS" && (result.state?.exit_code ?? 0) === 0;
  const failed = op.status === "FAILED" || op.status === "CANCELLED" || (op.status === "SUCCESS" && !ok);
  return reply({
    status: failed ? "FAILED" : op.status,
    events,
    bundle: ok ? JSON.parse(text(result.stdout)) : null,
    error: failed ? op.error ?? stderr.filter((l) => !l.startsWith("{")).slice(-20).join("\n") : null,
  });
});
