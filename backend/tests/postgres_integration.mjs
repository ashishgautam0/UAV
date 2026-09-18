// Execute generated mutations against an ephemeral PostgreSQL engine.
// Usage: node postgres_integration.mjs <pglite-module> <python>

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createHash } from "node:crypto";

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

const jdHash = (value) => createHash("sha256").update(value.trim(), "utf8").digest("hex");

await db.exec("create role anon; create role authenticated; create role service_role;");
await db.exec(readFileSync(join(repo, "supabase/schema.sql"), "utf8"));
const pgVersion = (await db.query("select version() as version")).rows[0].version;
assert.match(pgVersion, /PostgreSQL/i);
await db.exec([
  "insert into resume_profiles (id, username, version, source_filename, source_sha256, extraction_method, raw_text, status)",
  "values (5, 'subidh', 2, 'resume.pdf', repeat('a',64), 'pdf-profile-v1', 'Python FastAPI PostgreSQL', 'active');",
  "insert into scraped_jobs (id, title, company, url) values",
  "(11, 'AI Engineer', 'Screen Co', 'https://seed/11'),",
  "(12, 'AI Engineer', 'Draft Co', 'https://seed/12'),",
  "(14, 'AI Engineer', 'Letter Co', 'https://seed/14');",
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
    jd_hash: jdHash("Résumé — Python"),
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
  schema_version: 1, run_id: run1, kind: "items", rescored_jobs: [], followup_requests: [{
    message_type: "follow-up",
    params: {company_name: "O'Reilly Café", role_title: "AI Engineer",
             follow_up_number: 1, _application_id: 7},
  }],
};
const itemsSql = render("items", items);
await db.exec(itemsSql);
await db.exec(itemsSql);
assert.equal((await db.query("select count(*)::int as n from message_requests where params->>'_application_id'='7'")).rows[0].n, 1);

await db.exec("update scraped_jobs set description='Exact JD', jd_hash=repeat('c',64), jd_version=2, analysis_stale=true where id=11");
const rescoreItems = {...items, followup_requests: [], rescored_jobs: [{
  job_id: 11, jd_hash: "c".repeat(64), jd_version: 2, profile_version: 2,
  ats_score: 91, skill_match: 88, noc_verdict: "", analysis_version: "explainable-match-v1",
  analysis_details: {mandatory_eligibility: {overall: "passed"}},
}]};
await db.exec(render("rescore", rescoreItems));
let rescored = (await db.query("select ats_score, profile_version, analysis_stale from scraped_jobs where id=11")).rows[0];
assert.equal(rescored.ats_score, 91);
assert.equal(rescored.profile_version, 2);
assert.equal(rescored.analysis_stale, false);
await db.exec("update scraped_jobs set analysis_stale=true, jd_version=3 where id=11");
await db.exec(render("stale-rescore-guard", rescoreItems));
rescored = (await db.query("select analysis_stale from scraped_jobs where id=11")).rows[0];
assert.equal(rescored.analysis_stale, true);

const prepared1 = {
  schema_version: 1, run_id: run1, kind: "items", profile: "profile",
  screen_jobs: [{id: 11}], outreach_jobs: [{id: 12, char_limit: 600}],
  requests: [{request_id: 13, char_limit: 28, prompt: "write"}],
  cover_letters: [{job_id: 14, resume_profile_id: 5, resume_version: 2,
    jd_version: 1, jd_hash: "a".repeat(64), match_score: 94,
    analysis_version: "explainable-match-v1",
    rules_version: "grounded-cover-letter-v1", char_limit: 1200, prompt: "write",
    grounding_profile: "Python FastAPI PostgreSQL production systems",
    job_description: "Python FastAPI role at O'Reilly"}],
  followup_requests: [],
};
const actions1 = {
  schema_version: 1, run_id: run1,
  screens: [{job_id: 11, decision: "pass", reason: "Résumé matches"}],
  outreach_drafts: [{job_id: 12, content: "It's a grounded résumé note — नमस्ते."}],
  request_results: [{request_id: 13, status: "ready",
                     content: "First sentence fits. Second sentence is deliberately too long."}],
  cover_letter_drafts: [{job_id: 14, content: "Grounded résumé letter for O'Reilly — नमस्ते."}],
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
  cover_letter_drafts: [{job_id: 14, content: "Retry must not overwrite the first draft."}],
};
const retrySql = render("actions1-retry", validate("actions1-retry", prepared1, retryActions));
await db.exec(retrySql);
assert.equal((await db.query("select count(*)::int as n from job_messages where scraped_job_id=12 and message_type='cold_dm'")).rows[0].n, 1);
assert.equal((await db.query("select status from message_requests where id=13")).rows[0].status, "ready");
assert.equal((await db.query("select content from message_requests where id=13")).rows[0].content,
             validated1.request_results[0].content);
assert.equal((await db.query("select count(*)::int as n from notifications where type='run_summary' and metadata->>'run_id'=$1", [run1])).rows[0].n, 1);
assert.equal((await db.query("select count(*)::int as n from cover_letter_drafts where scraped_job_id=14")).rows[0].n, 1);
assert.match((await db.query("select content from cover_letter_drafts where scraped_job_id=14")).rows[0].content, /O'Reilly/);

const changedJd = {...scrape, jobs: [{
  title: "AI Engineer", company: "Letter Co", location: "India", source: "LinkedIn AI/ML",
  url: "https://seed/14", description: "Changed Python JD", score: 0, noc_verdict: "",
  skill_match: 90, verdict: "EXTERNAL", ats_score: 90, profile_version: 2,
  analysis_version: "explainable-match-v1", analysis_details: {}, jd_hash: "b".repeat(64),
}], email_log: null, notification: null};
changedJd.jobs[0].jd_hash = jdHash(changedJd.jobs[0].description);
await db.exec(render("changed-jd", changedJd));
assert.equal((await db.query("select jd_version from scraped_jobs where id=14")).rows[0].jd_version, 2);
assert.equal((await db.query("select is_outdated from cover_letter_drafts where scraped_job_id=14")).rows[0].is_outdated, true);

await db.exec([
  "insert into resume_profiles (id, username, version, source_filename, source_sha256, extraction_method, raw_text, status)",
  "values (6, 'subidh', 3, 'resume-v3.pdf', repeat('d',64), 'pdf-profile-v1', 'Python FastAPI PostgreSQL', 'pending_review');",
  "select * from activate_resume_profile(6, 'subidh', '{}'::jsonb, 'integration review');",
].join("\n"));
assert.equal((await db.query("select analysis_stale from scraped_jobs where id=14")).rows[0].analysis_stale, true);
const run3 = "2026-09-15T07:29:00+05:30.resume-v3";
const prepared3 = {...prepared1, run_id: run3, screen_jobs: [], outreach_jobs: [], requests: [],
  cover_letters: [{...prepared1.cover_letters[0], resume_profile_id: 6, resume_version: 3,
    jd_version: 2, jd_hash: changedJd.jobs[0].jd_hash, match_score: 90}]};
const actions3 = {...actions1, run_id: run3, screens: [], outreach_drafts: [], request_results: [],
  cover_letter_drafts: [{job_id: 14, content: "Grounded letter for reviewed resume v3."}]};
const sql3 = render("resume-v3-letter", validate("resume-v3-letter", prepared3, actions3));
await db.exec(sql3);
await db.exec(sql3);
assert.equal((await db.query("select count(*)::int as n from cover_letter_drafts where scraped_job_id=14")).rows[0].n, 2);
const currentLetter = (await db.query("select resume_version, is_outdated from cover_letter_drafts where scraped_job_id=14 and is_outdated=false")).rows[0];
assert.equal(currentLetter.resume_version, 3);
assert.equal(currentLetter.is_outdated, false);

const run2 = "2026-09-15T07:59:00+05:30.retry-b";
const prepared2 = {...prepared1, run_id: run2, screen_jobs: [], outreach_jobs: [], requests: [], cover_letters: []};
const actions2 = {...actions1, run_id: run2, screens: [], outreach_drafts: [], request_results: [], cover_letter_drafts: []};
const validated2 = validate("actions2", prepared2, actions2);
await db.exec(render("actions2", validated2));
assert.equal((await db.query("select count(*)::int as n from notifications where type='run_summary' and title='Hourly summary' and body='0 new jobs'")).rows[0].n, 3);
assert.equal((await db.query("select count(*)::int as n from notifications where type='run_summary' and metadata->>'run_id'=$1", [run2])).rows[0].n, 1);

const rollbackRun = "2026-09-15T08:59:00+05:30.rollback";
const rollbackPrepared = {...prepared1, run_id: rollbackRun, screen_jobs: [{id: 999}], outreach_jobs: [], requests: []};
const rollbackActions = {
  schema_version: 1, run_id: rollbackRun,
  screens: [{job_id: 999, decision: "pass", reason: "forces foreign-key failure"}],
  outreach_drafts: [], request_results: [],
  cover_letter_drafts: [],
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
