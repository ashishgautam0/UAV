"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getApplicationPromptSettings,
  getApplicationResumePdfUrl,
  getApplicationResumeStatus,
} from "@/lib/api";
import type { ApplicationPromptSettings, ApplicationResumeStatus, ScrapedJob } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

function renderPrompt(template: string, values: Record<string, string>) {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.split(`{{${key}}}`).join(value),
    template,
  );
}

export function ApplyWithCodex({ jobs, disabled }: { jobs: ScrapedJob[]; disabled: boolean }) {
  const [resume, setResume] = useState<ApplicationResumeStatus | null>(null);
  const [applicationSettings, setApplicationSettings] = useState<ApplicationPromptSettings | null>(null);
  const [resumeLoading, setResumeLoading] = useState(true);
  const [resumeError, setResumeError] = useState(false);
  const [pageUrl, setPageUrl] = useState("");

  useEffect(() => {
    const currentUrl = window.location.href;
    Promise.all([getApplicationResumeStatus(), getApplicationPromptSettings()])
      .then(([saved, settings]) => {
        setPageUrl(currentUrl);
        setResume(saved.available ? saved : null);
        setApplicationSettings(settings);
        setResumeError(false);
      })
      .catch(() => setResumeError(true))
      .finally(() => setResumeLoading(false));
  }, []);

  const downloadUrl = resume ? getApplicationResumePdfUrl() : "";
  const batch = jobs.map(j => ({ id: j.id, company: j.company, title: j.title, url: j.url }));
  const suppliedAnswers = applicationSettings ? [
    applicationSettings.submission_authorization,
    applicationSettings.notice_period && `Notice period: ${applicationSettings.notice_period}`,
    applicationSettings.current_ctc && `Current compensation: ${applicationSettings.current_ctc}`,
    applicationSettings.expected_ctc && `Expected compensation: ${applicationSettings.expected_ctc}`,
    applicationSettings.expected_start_date && `Expected start date: ${applicationSettings.expected_start_date}`,
    applicationSettings.current_location && `Current location: ${applicationSettings.current_location}`,
    applicationSettings.relocation_preference && `Relocation preference: ${applicationSettings.relocation_preference}`,
  ].filter(Boolean) : [];
  const hasSuppliedAnswers = suppliedAnswers.length > 0;
  const applicationAnswers = hasSuppliedAnswers
    ? [
      "Application-form answers supplied by me in Settings:",
      ...suppliedAnswers,
    ].join("\n")
    : "No additional application-form answers are saved. Ask me when a mandatory form answer is not supported by the resume.";
  const prompt = applicationSettings ? renderPrompt(applicationSettings.prompt_template, {
    application_answers: applicationAnswers,
    page_url: pageUrl,
    resume_filename: resume?.filename || "Resume.pdf",
    resume_url: downloadUrl,
    resume_sha256: resume?.sha256 || "",
    batch_jobs: JSON.stringify(batch, null, 2),
  }) : "";

  return (
    <Card>
      <CardHeader><CardTitle>Apply with Codex</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Your latest Settings PDF is loaded automatically. Copy this prompt into Codex with browser access.
          It covers the {jobs.length} currently displayed Best Matches. Copying does not start a run.
        </p>
        <p className="text-xs text-muted-foreground">
          The resume and editable prompt template come from Settings, so they work in private browsing and on your other devices.
          Upload or replace the PDF and edit the prompt only in Settings. Keep the prompt private.
        </p>
        {resumeLoading && <p role="status" className="text-sm">Loading the latest resume…</p>}
        {resumeError && <p role="alert" className="text-sm text-destructive">Could not load the saved resume. Refresh this page before copying the prompt.</p>}
        {!resumeLoading && !resumeError && !resume && <p className="text-sm">No saved PDF is available. <Link href="/settings" className="text-primary underline">Upload it in Settings</Link>.</p>}
        {resume && (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span>{resume.filename} · {resume.size ? `${Math.ceil(resume.size / 1024)} KB · ` : ""}Version {resume.version}</span>
            <a href={downloadUrl} target="_blank" rel="noreferrer" className="text-primary underline">Download resume</a>
            {resume.profile_status === "pending_review" && <span className="text-xs text-amber-600">Awaiting fact review in Settings</span>}
          </div>
        )}
        {!resumeLoading && !resumeError && !hasSuppliedAnswers && (
          <p className="text-sm text-amber-600">
            No application-form answers are saved. <Link href="/settings" className="underline">Add them in Settings</Link> so they appear on every device.
          </p>
        )}
        <textarea readOnly aria-label="Codex application prompt" value={resume ? prompt : "Upload your PDF in Settings to prepare the application prompt."}
          rows={8} className="w-full rounded-md border bg-background p-3 text-sm" />
        <Button disabled={!resume || resumeLoading || resumeError || disabled || jobs.length === 0}
          onClick={async () => {
            try { await navigator.clipboard.writeText(prompt); toast.success("Prompt copied — paste into Codex"); }
            catch { toast.error("Could not copy. Select and copy the prompt above."); }
          }}>Copy prompt for {jobs.length} jobs</Button>
      </CardContent>
    </Card>
  );
}
