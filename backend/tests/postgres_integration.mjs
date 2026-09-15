// Execute generated mutations against an ephemeral PostgreSQL engine.
// Usage: node postgres_integration.mjs <pglite-module> <python>

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const modulePath = process.argv[2];
const python = process.argv[3] || "python";
if (!modulePath) throw new Error("pass the installed @electric-sql/pglite module path");
const { PGlite } = await import(pathToFileURL(resolve(modulePath)).href);
const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "../..");
const bridge = join(repo, "backend/modules/cloud_connector.py");
const work = mkdtempSync(join(tmpdir(), "uav-pg-"));
const db = new PGlite();

function jsonFile(name, value) {
  const path = join(work, name);
  writeFileSync(path, JSON.stringify(value) + "\n", "utf8");
  return path;
}

function render(name, plan) {
  const input = jsonFile(name + ".json", plan);
  const output = join(work, name + ".sql");
  execFileSync(python, [bridge, "sql", input, output], { cwd: repo });
  return readFileSync(output, "utf8");
}

function validate(name, prepared, actions) {
  const preparedPath = jsonFile(name + "-prepared.json", prepared);
  const actionsPath = jsonFile(name + "-actions.json", actions);
  const output = join(work, name + "-validated.json");
  execFileSync(python, [bridge, "validate-actions", preparedPath, actionsPath, output], { cwd: repo });
  return JSON.parse(readFileSync(output, "utf8"));
}

await db.exec(readFileSync(join(repo, "supabase/schema.sql"), "utf8"));
const pgVersion = (await db.query("select version() as version")).rows[0].version;
assert.match(pgVersion, /PostgreSQL/i);
await db.exec([
  "insert into scraped_jobs (id, title, company, url) values",
  "(11, 'AI Engineer', 'Screen Co', 'https://seed/11'),",
  "(12, 'AI Engineer', 'Draft Co', 'https://seed/12');",
  "insert into message_requests (id, message_type, params, status)",
  "values (13, 'follow-up', '{}'::jsonb, 'pending');",
].join("\n"));

const run1 = "2026-09-15T06:59:00+05:30.retry-a";
const scrape = {
  schema_version: 1, run_id: run1, kind: "scrape",
  jobs: [{
    title: "AI Engineer", company: "O'Reilly Café", location: "भारत",
    source: "LinkedIn AI/ML", url: "https://example.test/unicode",
    description: "Résumé — Python", score: 0, noc_verdict: "",
    skill_match: 0, verdict: "EASY_APPLY", ats_score: 10,
  }],
  email_log: {
    subject: "Job Alert #integration", markdown_content: "Résumé — O'Reilly",
    html_content: "", jobs_count: 1, sources_summary: {"LinkedIn AI/ML": 1},
    email_sent: false,
  },
  notification: {title: "Job alert", body: "1 new job", type: "job_alert", metadata: {}},
  health_notification: null,
};
const scrapeSql = render("scrape", scrape);
await db.exec(scrapeSql);
await db.exec(scrapeSql);
assert.equal((await db.query("select count(*)::int as n from scraped_jobs where url='https://example.test/unicode'")).rows[0].n, 1);
assert.equal((await db.query("select count(*)::int as n from notifications where metadata->>'run_id'=$1 and metadata->>'stage'='job_alert'", [run1])).rows[0].n, 1);

const items = {
  schema_version: 1, run_id: run1, kind: "items", followup_requests: [{
    message_type: "follow-up",
    params: {company_name: "O'Reilly Café", role_title: "AI Engineer",
             follow_up_number: 1, _application_id: 7},
  }],
};
const itemsSql = render("items", items);
await db.exec(itemsSql);
await db.exec(itemsSql);
assert.equal((await db.query("select count(*)::int as n from message_requests where params->>'_application_id'='7'")).rows[0].n, 1);

const prepared1 = {
  schema_version: 1, run_id: run1, kind: "items", profile: "profile",
  screen_jobs: [{id: 11}], outreach_jobs: [{id: 12, char_limit: 600}],
  requests: [{request_id: 13, char_limit: 28, prompt: "write"}],
  followup_requests: [],
};
const actions1 = {
  schema_version: 1, run_id: run1,
  screens: [{job_id: 11, decision: "pass", reason: "Résumé matches"}],
  outreach_drafts: [{job_id: 12, content: "It's a grounded résumé note — नमस्ते."}],
  request_results: [{request_id: 13, status: "ready",
                     content: "First sentence fits. Second sentence is deliberately too long."}],
  notification: {title: "Hourly summary", body: "0 new jobs"},
};
const validated1 = validate("actions1", prepared1, actions1);
assert.ok(validated1.request_results[0].content.length <= 28);
const actionsSql1 = render("actions1", validated1);
await db.exec(actionsSql1);
const retryActions = {
  ...actions1,
  outreach_drafts: [],
  request_results: [{request_id: 13, status: "ready", content: "Retry must not overwrite ready content."}],
};
const retrySql = render("actions1-retry", validate("actions1-retry", prepared1, retryActions));
await db.exec(retrySql);
assert.equal((await db.query("select count(*)::int as n from job_messages where scraped_job_id=12 and message_type='cold_dm'")).rows[0].n, 1);
assert.equal((await db.query("select status from message_requests where id=13")).rows[0].status, "ready");
assert.equal((await db.query("select content from message_requests where id=13")).rows[0].content,
             validated1.request_results[0].content);
assert.equal((await db.query("select count(*)::int as n from notifications where type='run_summary' and metadata->>'run_id'=$1", [run1])).rows[0].n, 1);

const run2 = "2026-09-15T07:59:00+05:30.retry-b";
const prepared2 = {...prepared1, run_id: run2, screen_jobs: [], outreach_jobs: [], requests: []};
const actions2 = {...actions1, run_id: run2, screens: [], outreach_drafts: [], request_results: []};
const validated2 = validate("actions2", prepared2, actions2);
await db.exec(render("actions2", validated2));
assert.equal((await db.query("select count(*)::int as n from notifications where type='run_summary' and title='Hourly summary' and body='0 new jobs'")).rows[0].n, 2);

const rollbackRun = "2026-09-15T08:59:00+05:30.rollback";
const rollbackPrepared = {...prepared1, run_id: rollbackRun, screen_jobs: [{id: 999}], outreach_jobs: [], requests: []};
const rollbackActions = {
  schema_version: 1, run_id: rollbackRun,
  screens: [{job_id: 999, decision: "pass", reason: "forces foreign-key failure"}],
  outreach_drafts: [], request_results: [],
  notification: {title: "Rollback marker", body: "must not persist"},
};
let failed = false;
try {
  await db.exec(render("rollback", validate("rollback", rollbackPrepared, rollbackActions)));
} catch {
  failed = true;
  try { await db.exec("ROLLBACK;"); } catch {}
}
assert.equal(failed, true);
assert.equal((await db.query("select count(*)::int as n from notifications where metadata->>'run_id'=$1", [rollbackRun])).rows[0].n, 0);

await db.close();
console.log("PostgreSQL integration checks passed: " + pgVersion);
