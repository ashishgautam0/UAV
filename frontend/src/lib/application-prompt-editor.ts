import type { ApplicationPromptSettings } from "./types";

const fields = [
  ["submission_authorization", "Submission authorization"],
  ["notice_period", "Notice period"],
  ["current_ctc", "Current compensation"],
  ["expected_ctc", "Expected compensation"],
  ["expected_start_date", "Expected start date"],
  ["current_location", "Current location"],
  ["relocation_preference", "Relocation preference"],
] as const;
const start = "[Application answers]";
const end = "[/Application answers]";
const rulesStart = "[Automation rules]";
const rulesEnd = "[/Automation rules]";

export function toPromptEditor(settings: ApplicationPromptSettings): string {
  const answers = `${start}\n${fields.map(([key, label]) => `${label}: ${settings[key]}`).join("\n")}\n${end}`;
  const application = settings.prompt_template.includes("{{application_answers}}")
    ? settings.prompt_template.replace("{{application_answers}}", answers)
    : `${settings.prompt_template}\n\n${answers}`;
  return `${rulesStart}\n${settings.automation_rules.trimEnd()}\n${rulesEnd}\n\n${application}`;
}

export function fromPromptEditor(text: string, previous: ApplicationPromptSettings): ApplicationPromptSettings {
  if (!text.startsWith(`${rulesStart}\n`) || text.split(rulesStart).length !== 2 ||
      text.split(rulesEnd).length !== 2 || text.indexOf(rulesEnd) < text.indexOf(rulesStart)) {
    throw new Error("Keep one [Automation rules] section at the start and its closing marker in the prompt.");
  }
  const rules = text.slice(rulesStart.length, text.indexOf(rulesEnd)).trim();
  if (rules.length > 12000) throw new Error("Automation rules must be 12,000 characters or fewer.");
  const application = text.slice(text.indexOf(rulesEnd) + rulesEnd.length).replace(/^\n\n/, "");
  if (application.split(start).length !== 2 || application.split(end).length !== 2 || application.indexOf(end) < application.indexOf(start)) {
    throw new Error("Keep one [Application answers] section and its closing marker in the prompt.");
  }
  const first = application.indexOf(start);
  const last = application.indexOf(end);
  const block = application.slice(first + start.length, last).trim();
  const result = { ...previous, automation_rules: rules };
  const seen = new Set<string>();
  let current: typeof fields[number][0] | undefined;
  for (const line of block.split("\n")) {
    const field = fields.find(([, label]) => line.startsWith(`${label}:`));
    if (field) {
      if (seen.has(field[0])) throw new Error(`Duplicate answer: ${field[1]}`);
      current = field[0];
      seen.add(current);
      result[current] = line.slice(field[1].length + 1).trim();
    } else if (current) {
      result[current] += `\n${line}`;
    } else if (line.trim()) {
      throw new Error("Keep the answer labels unchanged; edit the text after each colon.");
    }
  }
  for (const [key, label] of fields) {
    if (!seen.has(key)) throw new Error(`Keep the ${label}: label; leave its value blank if unknown.`);
    result[key] = result[key].trim();
    if (result[key].length > 500) throw new Error(`${label} must be 500 characters or fewer.`);
  }
  result.prompt_template = `${application.slice(0, first)}{{application_answers}}${application.slice(last + end.length)}`;
  if (result.prompt_template.length > 12000) throw new Error("Prompt instructions must be 12,000 characters or fewer.");
  return result;
}
