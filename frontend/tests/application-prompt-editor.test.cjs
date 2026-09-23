/* eslint-disable @typescript-eslint/no-require-imports -- Node CommonJS test harness for TypeScript without adding a runner. */
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
const source = fs.readFileSync("src/lib/application-prompt-editor.ts", "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const api = { exports: {} };
new Function("exports", "require", "module", compiled)(api.exports, require, api);
const { toPromptEditor, fromPromptEditor } = api.exports;
const saved = {
  prompt_template: "Apply using {{application_answers}}. Resume: {{resume_url}} Jobs: {{batch_jobs}}",
  submission_authorization: "Ask before submitting.",
  notice_period: "Two weeks\nAfter confirmation.",
  current_ctc: "", expected_ctc: "₹500,000", expected_start_date: "",
  current_location: "Pune", relocation_preference: "Ask me",
};
test("existing settings and multiline Unicode answers round-trip without freezing dynamic values", () => {
  assert.deepEqual(fromPromptEditor(toPromptEditor(saved), saved), saved);
});
test("inline edits update backend fields and instructions; clearing an answer is deliberate", () => {
  const text = toPromptEditor(saved).replace("Apply using", "My instructions using")
    .replace("Current location: Pune", "Current location:")
    .replace("Expected compensation: ₹500,000", "Expected compensation: ₹600,000");
  const result = fromPromptEditor(text, saved);
  assert.equal(result.current_location, "");
  assert.equal(result.expected_ctc, "₹600,000");
  assert.ok(result.prompt_template.startsWith("My instructions"));
  assert.ok(result.prompt_template.includes("{{batch_jobs}}"));
});
test("custom templates without answer placeholder gain one without losing stored answers", () => {
  const custom = { ...saved, prompt_template: "Custom {{resume_url}}" };
  const result = fromPromptEditor(toPromptEditor(custom), custom);
  assert.equal(result.notice_period, custom.notice_period);
  assert.equal(result.prompt_template, custom.prompt_template + "\n\n{{application_answers}}");
});
test("missing, duplicate or malformed labels and sections cannot silently erase answers", () => {
  const text = toPromptEditor(saved);
  for (const broken of [
    text.replace("[/Application answers]", ""),
    text + "[Application answers]",
    text.replace("Current location:", "Location:"),
    text.replace("Current location: Pune", "Current location: Pune\nCurrent location: Delhi"),
    text.replace("[Application answers]", "[Application answers]\nUnlabelled answer"),
    text.replace("Current location: Pune", "Current location: " + "x".repeat(501)),
    "x".repeat(12001) + text,
  ]) assert.throws(() => fromPromptEditor(broken, saved));
});
