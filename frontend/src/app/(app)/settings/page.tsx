"use client";

import { useEffect, useRef, useState } from "react";
import {
  activateResumeProfile,
  getApplicationPromptSettings,
  getCompanyExclusions,
  getRenderedApplicationPrompt,
  getResumeProfileStatus,
  updateApplicationPromptSettings,
  updateCompanyExclusions,
  uploadResumePdf,
} from "@/lib/api";
import type { ApplicationPromptSettings, RenderedApplicationPrompt, ResumeFact, ResumeProfile, ResumeProfileReview } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { CheckCircle2, Copy, Loader2, Plus, RefreshCw, Trash2, Upload } from "lucide-react";
import styles from "./settings.module.css";
import { toPromptEditor, fromPromptEditor } from "@/lib/application-prompt-editor";
import { OutreachPrompt } from "./outreach-prompt";

const MAX_BYTES = 10 * 1024 * 1024;
const EMPTY_APPLICATION_SETTINGS: ApplicationPromptSettings = {
  hr_email_template: "",
  followup_template: "",
  cold_dm_template: "",
  prompt_template: "",
  automation_rules: "",
  submission_authorization: "",
  total_work_experience: "1 year",
  skill_experience: "1 year",
  onsite_any_location: "Yes",
  notice_period: "",
  current_ctc: "",
  expected_ctc: "",
  expected_start_date: "",
  current_location: "",
  relocation_preference: "",
};
const evidence = (item: ResumeFact) => item.evidence?.map((e) => e.excerpt).filter(Boolean).join(" · ") || "User review required";

function toReview(profile: ResumeProfile): ResumeProfileReview {
  const f = profile.facts || {};
  return {
    skills: (f.skills || []).map((x) => x.name || "").filter(Boolean),
    certifications: (f.certifications || []).map((x) => x.name || "").filter(Boolean),
    experience: (f.experience || []).map((x) => ({ id: x.id, label: x.label, role: x.role, company: x.company, start: x.start, end: x.end })),
    education: (f.education || []).map((x) => ({ id: x.id, level: x.level || "bachelor", credential: x.credential || "", field: x.field, institution: x.institution })),
    review_notes: "",
  };
}

export default function SettingsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [pending, setPending] = useState<ResumeProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [excludedCompaniesText, setExcludedCompaniesText] = useState("");
  const [exclusionsLoaded, setExclusionsLoaded] = useState(false);
  const [exclusionsDirty, setExclusionsDirty] = useState(false);
  const [savingExclusions, setSavingExclusions] = useState(false);
  const [active, setActive] = useState<ResumeProfile | null>(null);
  const [candidate, setCandidate] = useState<ResumeProfile | null>(null);
  const [review, setReview] = useState<ResumeProfileReview | null>(null);
  const [applicationSettings, setApplicationSettings] = useState<ApplicationPromptSettings>(EMPTY_APPLICATION_SETTINGS);
  const [savingApplicationSettings, setSavingApplicationSettings] = useState(false);
  const [promptEditor, setPromptEditor] = useState("");
  const [promptDirty, setPromptDirty] = useState(false);
  const [renderedPrompt, setRenderedPrompt] = useState<RenderedApplicationPrompt | null>(null);
  const [renderingPrompt, setRenderingPrompt] = useState(false);

  async function refreshRenderedPrompt() {
    setRenderingPrompt(true);
    try {
      const pageUrl = `${window.location.origin}/tonight`;
      setRenderedPrompt(await getRenderedApplicationPrompt(pageUrl));
    } catch (e) {
      setRenderedPrompt(null);
      toast.error(e instanceof Error ? e.message : "Ready Codex prompt could not be generated");
    } finally {
      setRenderingPrompt(false);
    }
  }

  useEffect(() => {
    getCompanyExclusions().then(({ companies }) => {
      setExcludedCompaniesText(companies.join("\n"));
      setExclusionsLoaded(true);
    }).catch(() => toast.error("Could not load excluded companies. Retry Settings before saving changes."));
  }, []);

  useEffect(() => {
    Promise.all([
      getResumeProfileStatus(),
      getApplicationPromptSettings(),
      getRenderedApplicationPrompt(`${window.location.origin}/tonight`).catch(() => null),
    ]).then(([s, settings, readyPrompt]) => {
      setActive(s.active);
      const latest = s.latest?.status === "pending_review" ? s.latest : null;
      setPending(latest);
      setCandidate(latest);
      if (latest) setReview(toReview(latest));
      setApplicationSettings(settings);
      setPromptEditor(toPromptEditor(settings));
      setRenderedPrompt(readyPrompt);
    }).catch(() => { setLoadError(true); toast.error("Failed to load resume status"); }).finally(() => setLoading(false));
  }, []);

  function choose(next?: File) {
    if (!next) return;
    if (next.type !== "application/pdf" || !next.name.toLowerCase().endsWith(".pdf")) return toast.error("Only PDF resume uploads are supported");
    if (next.size > MAX_BYTES) return toast.error("Resume PDF must be 10 MB or smaller");
    setFile(next);
  }

  async function upload() {
    if (!file) return;
    setBusy(true);
    try {
      const next = await uploadResumePdf(file); setCandidate(next); setPending(next.status === "pending_review" ? next : pending); setReview(toReview(next));
      toast.success("PDF replaced and extracted. Review every fact before activating it.");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Resume upload failed"); }
    finally { setBusy(false); }
  }

  async function activate() {
    if (!candidate || !review) return;
    setBusy(true);
    try {
      const saved = await activateResumeProfile(candidate.id, review);
      setActive(saved); if (pending?.id === saved.id) setPending(null); setCandidate(null); setReview(null); setFile(null);
      toast.success(`Profile v${saved.version} is active; earlier analysis is stale and will be rescored.`);
    } catch (e) { toast.error(e instanceof Error ? e.message : "Profile activation failed"); }
    finally { setBusy(false); }
  }

  async function saveApplicationSettings() {
    setSavingApplicationSettings(true);
    try {
      const edited = fromPromptEditor(promptEditor, applicationSettings);
      const saved = await updateApplicationPromptSettings(Object.fromEntries(
        Object.entries(edited).filter(([key]) => key === "prompt_template" || !key.endsWith("_template")),
      ));
      setApplicationSettings(saved);
      setPromptEditor(toPromptEditor(saved));
      setPromptDirty(false);
      await refreshRenderedPrompt();
      toast.success("Application prompt details saved for every browser and device.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Application prompt details could not be saved");
    } finally {
      setSavingApplicationSettings(false);
    }
  }

  async function saveCompanyExclusions() {
    const companies = excludedCompaniesText.split(/\r?\n/).map((name) => name.trim()).filter(Boolean);
    if (companies.length > 100 || companies.some((name) => name.length > 120)) {
      toast.error("Use at most 100 company names, one per line, each up to 120 characters.");
      return;
    }
    setSavingExclusions(true);
    try {
      const saved = await updateCompanyExclusions(companies);
      setExcludedCompaniesText(saved.companies.join("\n"));
      setExclusionsDirty(false);
      toast.success("Company exclusions saved for the next Claude scraper run.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not save company exclusions");
    } finally {
      setSavingExclusions(false);
    }
  }

  if (loading) return <div className="flex h-[60vh] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  return <div className={`${styles.settings} mx-auto w-full min-w-0 max-w-5xl space-y-6`}>
    <div><h1 className="text-2xl font-bold">Resume profile</h1><p className="mt-1 text-sm text-muted-foreground">Upload a text-based PDF, then verify extracted facts and evidence. DOCX, text, and LaTeX input are not accepted.</p></div>
    {loadError && <div role="alert" className="rounded border border-destructive p-4 text-sm">Could not load the backend resume. This does not mean your resume is missing. <Button variant="outline" onClick={() => window.location.reload()}>Retry</Button></div>}
    {active ? <Card>
      <CardHeader><CardTitle className="flex items-center gap-2"><CheckCircle2 className="h-5 w-5 text-emerald-600" />Active backend resume</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <p className="font-medium">{active.source_filename} · Version {active.version}</p>
        <p className="text-sm text-muted-foreground">This is the active profile returned to the backend scraper and drafting code used by the Claude routine. An already-running job may still hold its earlier snapshot.</p>
        <p className="text-xs text-muted-foreground">Last activated: {active.activated_at ? new Date(active.activated_at).toLocaleString() : "Not recorded"} · {active.readability.status || "Unknown readability"}</p>
        <p className="break-all text-xs text-muted-foreground">PDF fingerprint: {active.source_sha256}</p>
        <label htmlFor="backend-resume-context" className="block text-sm font-medium">Resume context used by the backend</label>
        <Textarea id="backend-resume-context" readOnly value={active.backend_text || "Backend text unavailable. Refresh after the backend update finishes."} rows={16} />
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy} onClick={() => { setCandidate(active); setReview(toReview(active)); }}>Edit active profile</Button>
          <Button variant="outline" disabled={!active.backend_text} onClick={async () => { try { await navigator.clipboard.writeText(active.backend_text || ""); toast.success("Backend resume text copied"); } catch { toast.error("Select and copy the text above."); } }}>Copy backend text</Button>
        </div>
        <p className="text-xs text-muted-foreground">Edit the verified facts below, then save to update future backend reads. To replace source text, projects or contact details, upload and activate an updated PDF. The source PDF text stays unchanged as evidence.</p>
        <p className="text-xs text-muted-foreground">Today Todo automatically uses the latest PDF uploaded here on every browser and device.</p>
      </CardContent>
    </Card> : !loadError && <p className="rounded border p-4 text-sm">No active backend resume. Upload a PDF and confirm its extracted facts to activate it.</p>}
    {pending && pending.id !== active?.id && <div className="flex flex-wrap items-center justify-between gap-3 rounded border p-4 text-sm"><span>Awaiting review: {pending.source_filename} · v{pending.version}. The backend still uses the active profile above.</span><Button variant="outline" disabled={busy} onClick={() => { setCandidate(pending); setReview(toReview(pending)); }}>Review uploaded PDF</Button></div>}
    <Card>
      <CardHeader>
        <CardTitle>Today Todo application prompt</CardTitle>
        <p className="text-sm text-muted-foreground">Applications only. Edit automation rules, instructions, and answers together. HR emails, follow-ups and cold DMs have separate prompts below.</p>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <div className="md:col-span-2 overflow-hidden rounded-lg border p-3">
          <div role="toolbar" aria-label="Prompt actions" className="mb-3 flex flex-wrap gap-2">
          <Button disabled={savingApplicationSettings || renderingPrompt || loadError} onClick={saveApplicationSettings}>
            {savingApplicationSettings && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Today Todo prompt
          </Button>
            <Button variant="outline" disabled={renderingPrompt || savingApplicationSettings || promptDirty || loadError} onClick={refreshRenderedPrompt}>
              {renderingPrompt ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
              Generate current batch
            </Button>
            <Button disabled={!renderedPrompt?.ready || promptDirty || savingApplicationSettings || renderingPrompt || loadError} onClick={async () => { try { await navigator.clipboard.writeText(renderedPrompt!.prompt); toast.success("Complete Codex prompt copied"); } catch { toast.error("Open the generated preview below to select and copy."); } }}>
              <Copy className="mr-2 h-4 w-4" />Copy complete prompt for Codex
            </Button>
          </div>
          {promptDirty && <p role="status" className="mb-2 text-sm text-amber-600">Unsaved changes — save before generating or copying.</p>}
          <label htmlFor="application-prompt-template" className="text-sm font-medium">Editable prompt and application answers</label>
          <Textarea
            id="application-prompt-template"
            value={promptEditor}
            disabled={savingApplicationSettings || loadError}
            rows={18}
            onChange={(event) => { setPromptEditor(event.target.value); setPromptDirty(true); }}
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Edit the AUTOMATION RULES (authoritative) text at the top. Keep both section markers and the answer labels; edit values after each colon and leave unknown answers blank. Clear the rules text between its markers to restore the defaults. Dynamic placeholders: {"{{application_answers}}"}, {"{{page_url}}"}, {"{{resume_filename}}"}, {"{{resume_url}}"}, {"{{resume_sha256}}"}, and {"{{batch_jobs}}"}.
          </p>
        </div>
        <div className="md:col-span-2 space-y-3 border-t pt-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="font-medium">Ready-to-paste Codex prompt</h3>
              <p className="text-xs text-muted-foreground">Generated from jobs that passed backend screening, saved answers, and the latest Settings PDF. Screening results are omitted from job JSON.</p>
            </div>

          </div>
          {renderedPrompt && <>
            <details><summary className="cursor-pointer text-sm">View generated prompt{promptDirty ? " (previously saved version)" : ""}</summary><Textarea readOnly value={renderedPrompt.prompt} rows={18} aria-label="Ready-to-paste Codex prompt" /></details>
            <p className="text-xs text-muted-foreground">Fixed batch: {renderedPrompt.job_count} job{renderedPrompt.job_count === 1 ? "" : "s"}. Generate again to pick up changed jobs, answers, or resume.</p>
            {renderedPrompt.issues.length > 0 && <div role="alert" className="rounded border border-amber-500/40 bg-amber-500/5 p-3 text-sm"><p className="font-medium">Resolve before copying:</p><ul className="mt-1 list-disc pl-5">{renderedPrompt.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul></div>}

          </>}
        </div>
      </CardContent>
    </Card>
    {!loadError && <>
      <OutreachPrompt kind="hr_email" title="Initial HR email prompt" description="Send through your Gmail. Use Dashboard’s HR todos; verify recipients and research official hiring contacts if Claude’s address is invalid or unverified." initialValue={applicationSettings.hr_email_template} />
      <OutreachPrompt kind="followup" title="HR follow-up email prompt" description="Use your Gmail and Dashboard’s Follow-ups Due queue. Check recipient evidence, dates, Sent history and bounces before sending." initialValue={applicationSettings.followup_template} />
      <OutreachPrompt kind="cold_dm" title="Cold DM prompt" description="Generate a fixed batch of eligible due jobs with their saved Cold DM text. Verify each job is still due before sending a LinkedIn connection note; record a confirmed send to advance its existing follow-up schedule." initialValue={applicationSettings.cold_dm_template} />
    </>}
    <Card>
      <CardHeader><CardTitle>Exclude companies from scraped jobs</CardTitle><p className="text-sm text-muted-foreground">Enter one employer per line. The Claude hourly scraper skips new jobs from these companies before saving or including them in digests. Existing Tracker jobs and history stay intact.</p></CardHeader>
      <CardContent className="space-y-3">
        <label htmlFor="excluded-company-names" className="text-sm font-medium">Company names to skip</label>
        <Textarea id="excluded-company-names" value={excludedCompaniesText} rows={8} disabled={!exclusionsLoaded || savingExclusions} onChange={(event) => { setExcludedCompaniesText(event.target.value); setExclusionsDirty(true); }} placeholder="Example Company\nAnother Company" />
        <p className="text-xs text-muted-foreground">Matches the employer name after normalizing punctuation and common legal suffixes. It does not match companies merely mentioned in the job description. Existing large-company and experience filters still apply.</p>
        <Button type="button" disabled={!exclusionsLoaded || !exclusionsDirty || savingExclusions} onClick={saveCompanyExclusions}>{savingExclusions && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Save excluded companies</Button>
        {!exclusionsLoaded && <p role="status" className="text-xs text-amber-600">Company list unavailable. Reload Settings to retry.</p>}
      </CardContent>
    </Card>
    <div>
      <Card><CardHeader><CardTitle>Resume PDF</CardTitle></CardHeader><CardContent className="space-y-4">
        <input ref={inputRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={(e) => choose(e.target.files?.[0])} />
        <button type="button" onClick={() => inputRef.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); choose(e.dataTransfer.files?.[0]); }} className="flex min-h-40 w-full flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center"><Upload className="mb-3 h-8 w-8 text-muted-foreground" /><span className="font-medium">{file?.name || "Choose or drop a PDF"}</span><span className="text-xs text-muted-foreground">PDF only · 10 MB · 30 pages</span></button>
        <Button className="w-full" disabled={!file || busy} onClick={upload}>{busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}Extract for review</Button>
        <p className="text-xs text-muted-foreground">Uploading a valid PDF replaces the prior application PDF in cloud storage. Uploads are available only from Settings.</p>
      </CardContent></Card>
    </div>
    {candidate && review && <Card><CardHeader><CardTitle>{candidate.id === active?.id ? "Edit active profile" : "Review uploaded profile"} · v{candidate.version}</CardTitle><p className="text-sm text-muted-foreground">Corrections remain separate; the extracted PDF text and hash never change.</p></CardHeader><CardContent className="space-y-6">
      <div><label className="text-sm font-medium">Skills (comma separated)</label><Textarea value={review.skills.join(", ")} onChange={(e) => setReview({ ...review, skills: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })} /><p className="mt-1 text-xs text-muted-foreground">Evidence: {(candidate.facts.skills || []).map(evidence).join(" · ") || "None extracted"}</p></div>
      <div><label className="text-sm font-medium">Certifications (comma separated)</label><Textarea value={review.certifications.join(", ")} onChange={(e) => setReview({ ...review, certifications: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })} /><p className="mt-1 text-xs text-muted-foreground">Evidence: {(candidate.facts.certifications || []).map(evidence).join(" · ") || "None extracted"}</p></div>
      <div className="space-y-3"><div className="flex items-center justify-between"><h3 className="font-medium">Experience</h3><Button type="button" variant="outline" size="sm" onClick={() => setReview({ ...review, experience: [...review.experience, { id: "", label: "", role: "", company: "", start: "", end: "" }] })}><Plus className="mr-1 h-3.5 w-3.5" />Add verified entry</Button></div>{review.experience.length === 0 && <p className="text-sm text-amber-600">No dated experience was extracted. Experience eligibility will remain unknown unless you add and verify an entry.</p>}{review.experience.map((item, i) => <div key={item.id || `new-experience-${i}`} className="grid gap-2 rounded border p-3 sm:grid-cols-2">
        {(["role", "company", "start", "end"] as const).map((key) => <Input key={key} value={item[key] || ""} placeholder={key === "start" ? "YYYY-MM" : key === "end" ? "YYYY-MM or present" : key} onChange={(e) => { const experience = [...review.experience]; experience[i] = { ...item, [key]: e.target.value }; setReview({ ...review, experience }); }} />)}
        <p className="text-xs text-muted-foreground">Evidence: {evidence((candidate.facts.experience || []).find((fact) => fact.id === item.id) || {})}</p><Button type="button" variant="ghost" size="sm" className="justify-self-end text-red-500" onClick={() => setReview({ ...review, experience: review.experience.filter((_, index) => index !== i) })}><Trash2 className="mr-1 h-3.5 w-3.5" />Remove</Button>
      </div>)}</div>
      <div className="space-y-3"><div className="flex items-center justify-between"><h3 className="font-medium">Education</h3><Button type="button" variant="outline" size="sm" onClick={() => setReview({ ...review, education: [...review.education, { id: "", level: "bachelor", credential: "", field: "", institution: "" }] })}><Plus className="mr-1 h-3.5 w-3.5" />Add verified entry</Button></div>{review.education.map((item, i) => <div key={item.id || `new-education-${i}`} className="grid gap-2 rounded border p-3 sm:grid-cols-2">
        {(["level", "credential", "field", "institution"] as const).map((key) => <Input key={key} value={item[key] || ""} placeholder={key} onChange={(e) => { const education = [...review.education]; education[i] = { ...item, [key]: e.target.value }; setReview({ ...review, education }); }} />)}
        <p className="text-xs text-muted-foreground">Evidence: {evidence((candidate.facts.education || []).find((fact) => fact.id === item.id) || {})}</p><Button type="button" variant="ghost" size="sm" className="justify-self-end text-red-500" onClick={() => setReview({ ...review, education: review.education.filter((_, index) => index !== i) })}><Trash2 className="mr-1 h-3.5 w-3.5" />Remove</Button>
      </div>)}</div>
      <div><label className="text-sm font-medium">Review notes</label><Textarea value={review.review_notes || ""} onChange={(e) => setReview({ ...review, review_notes: e.target.value })} /></div>
      <Button disabled={busy} onClick={activate}>{busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{candidate.id === active?.id ? "Save active profile changes" : `Confirm facts and activate v${candidate.version}`}</Button>
      <Button variant="outline" disabled={busy} onClick={() => { setCandidate(null); setReview(null); }}>Cancel editing</Button>
    </CardContent></Card>}
  </div>;
}
