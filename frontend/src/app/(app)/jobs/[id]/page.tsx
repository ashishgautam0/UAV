"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  API_URL,
  getScrapedJob,
  getJobMessage,
  getCachedCompanyIntel,
  findRecruiterEmails,
  lookupApplication,
  snoozeFollowUp,
  getFollowUpHistory,
} from "@/lib/api";
import type {
  Application,
  CachedCompanyIntel,
  FollowUpHistory,
  JobMessage,
  RecruiterEmailReport,
  ScrapedJob,
} from "@/lib/types";

import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  Building2,
  Gauge,
  Landmark,
  Check,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  MessageSquareText,
  Mail,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const SECTIONS = [
  {
    type: "cover_letter",
    title: "Cover letter draft",
    description: "Generated only for a verified eligible job with a 90+ resume match.",
    icon: FileText,
  },
  {
    type: "cold_dm",
    title: "Cold DM",
    description: "Short LinkedIn message for a recruiter at this company.",
    icon: MessageSquareText,
  },
  {
    type: "hr_email",
    title: "Email to Company HR",
    description: "A fuller email you can send to the company's HR inbox.",
    icon: Mail,
  },
  {
    type: "resume_points",
    title: "Resume Customization",
    description:
      "Tailored bullet rewrites and keywords for this specific job.",
    icon: FileText,
  },
] as const;

// Pull "FIT SCORE: 4.2 / 5 — ..." out of the evaluation's first line.
function parseFitScore(text: string | null): number | null {
  if (!text) return null;
  const m = text.match(/fit\s*score:\s*([\d.]+)/i);
  if (!m) return null;
  const n = parseFloat(m[1]);
  return Number.isFinite(n) ? n : null;
}

function scoreColor(score: number) {
  if (score >= 4) return "bg-emerald-600 text-white";
  if (score >= 3) return "bg-yellow-500 text-black";
  return "bg-red-600 text-white";
}

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const jobId = Number(params.id);

  const [job, setJob] = useState<ScrapedJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [messages, setMessages] = useState<Record<string, string | null>>({});
  const [messageRows, setMessageRows] = useState<Record<string, JobMessage>>({});
  const [intel, setIntel] = useState<CachedCompanyIntel | null>(null);
  const [evaluation, setEvaluation] = useState<string | null>(null);
  const [demoReady, setDemoReady] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [application, setApplication] = useState<Application | null>(null);
  const [history, setHistory] = useState<FollowUpHistory[]>([]);
  const [dateSaving, setDateSaving] = useState(false);
  const [emailReport, setEmailReport] = useState<RecruiterEmailReport | null>(
    null
  );
  const [emailLoading, setEmailLoading] = useState(false);
  const [extraName, setExtraName] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setNotFound(false);
    setHistory([]);
    try {
      const messagesPromise = Promise.all(
        SECTIONS.map((s) =>
          getJobMessage(jobId, s.type).catch(() => ({ content: null }))
        )
      );
      const evaluationPromise = getJobMessage(jobId, "evaluation").catch(() => ({ content: null }));
      const demoPromise = getJobMessage(jobId, "demo_html").catch(() => ({ content: null }));
      const j = await getScrapedJob(jobId);
      setJob(j);
      const trackedPromise = lookupApplication(j.url).catch(() => null);
      if (j.company) {
        getCachedCompanyIntel(j.company)
          .then(setIntel)
          .catch(() => setIntel({ found: false }));
      }
      const [tracked, results, evaluationRow, demoRow] = await Promise.all([
        trackedPromise, messagesPromise, evaluationPromise, demoPromise,
      ]);
      setApplication(tracked);
      if (tracked) {
        setHistory(await getFollowUpHistory("application", tracked.id).catch(() => []));
      }
      const next: Record<string, string | null> = {};
      const rows: Record<string, JobMessage> = {};
      SECTIONS.forEach((s, i) => {
        next[s.type] = results[i]?.content ?? null;
        rows[s.type] = results[i] as JobMessage;
      });
      setMessages(next);
      setMessageRows(rows);
      setEvaluation(evaluationRow.content);
      setDemoReady(Boolean(demoRow.content));
    } catch {
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (Number.isFinite(jobId)) load();
    else setNotFound(true);
  }, [jobId, load]);

  function handleCopy(type: string) {
    navigator.clipboard.writeText(messages[type] || "");
    setCopied(type);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopied(null), 2000);
  }

  function downloadCoverLetter() {
    const content = messages.cover_letter;
    if (!content) return;
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${job?.company || "company"}-${job?.title || "role"}-cover-letter.txt`.replace(/[^a-z0-9.-]+/gi, "-");
    link.click();
    URL.revokeObjectURL(url);
  }

  async function handleFindEmails() {
    if (!job?.company) return;
    setEmailLoading(true);
    try {
      const report = await findRecruiterEmails(job.company, extraName.trim());
      setEmailReport(report);
      if (!report.ok) {
        toast.message(report.message || "Nothing to search yet.");
      }
    } catch {
      toast.error("Email lookup failed");
    } finally {
      setEmailLoading(false);
    }
  }

  function handleCopyText(text: string, key: string) {
    navigator.clipboard.writeText(text);
    setCopied(key);
    toast.success("Copied");
    setTimeout(() => setCopied(null), 2000);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (notFound || !job) {
    return (
      <div className="space-y-4 py-8 text-center">
        <p className="text-muted-foreground">
          This job no longer exists (it may have been dismissed and deleted).
        </p>
        <Button variant="outline" onClick={() => router.push("/tonight")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Today Todo
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back */}
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2 text-muted-foreground"
        onClick={() => router.back()}
      >
        <ArrowLeft className="mr-1.5 h-4 w-4" />
        Back
      </Button>

      {/* Job header */}
      <div className="space-y-3">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          {job.title}
        </h1>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Building2 className="h-4 w-4" />
            {job.company}
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {job.work_mode && (
            <Badge variant="outline" className="text-xs">
              {job.work_mode}
            </Badge>
          )}
          <Badge variant="secondary" className="text-xs">
            {job.source}
          </Badge>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Follow-up schedule and recorded history</CardTitle><CardDescription>Scheduled dates are plans; the graph below contains only completed follow-ups recorded in the tracker.</CardDescription></CardHeader>
        <CardContent className="space-y-5">
          {application ? <>
            <div className="flex flex-wrap items-end gap-3">
              <label className="space-y-1 text-sm"><span className="text-muted-foreground">Next scheduled follow-up</span><input type="date" value={application.follow_up_date || ""} disabled={dateSaving} className="block h-9 rounded border bg-background px-3" onChange={async (e) => {
                const value = e.target.value; if (!value) return; setDateSaving(true);
                try { await snoozeFollowUp(application.id, value); setApplication({ ...application, follow_up_date: value }); toast.success("Follow-up date saved"); }
                catch { toast.error("Failed to save follow-up date"); }
                finally { setDateSaving(false); }
              }} /></label>
              {dateSaving && <Loader2 className="mb-2 h-4 w-4 animate-spin" />}
              <span className="mb-2 text-xs text-muted-foreground">Applied {application.date_applied || "date unknown"}</span>
            </div>
            {history.length ? <div className="space-y-3" aria-label="Recorded follow-up history graph">
              {history.map((event) => <div key={event.id} className="grid grid-cols-[11rem_1fr_6rem] items-center gap-3 text-sm">
                <span className="text-muted-foreground">{new Date(event.sent_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" })}</span>
                <div className="h-3 rounded bg-sky-500" title={`Follow-up #${event.follow_up_number} sent via ${event.channel || "unspecified channel"}`} />
                <Badge variant="outline" className="justify-center">{event.follow_up_outcome.replace("_", " ")}</Badge>
              </div>)}
              <p className="text-xs text-muted-foreground">Each bar is one recorded send event; bar length does not imply performance.</p>
            </div> : <p className="rounded border border-dashed p-4 text-sm text-muted-foreground">No completed follow-ups have been recorded for this tracker record.</p>}
          </> : <p className="text-sm text-muted-foreground">No tracker record matches this job URL, so there is no persisted follow-up schedule or history to display.</p>}
        </CardContent>
      </Card>

      {/* Company Intel */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Landmark className="h-4 w-4" />
            Company Intel — {job.company}
          </CardTitle>
          <CardDescription>
            Background and talking points, researched by the hourly routine.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {intel?.found ? (
            <>
              {intel.description && (
                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                  {intel.description}
                </p>
              )}
              {intel.recent_news && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    Recent direction
                  </p>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                    {intel.recent_news}
                  </p>
                </div>
              )}
              {(() => {
                let signals: string[] = [];
                const raw = intel.tech_signals;
                if (Array.isArray(raw)) signals = raw;
                else if (typeof raw === "string") {
                  try {
                    const parsed = JSON.parse(raw);
                    if (Array.isArray(parsed)) signals = parsed;
                  } catch {
                    /* not JSON — ignore */
                  }
                }
                return signals.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {signals.map((s) => (
                      <Badge key={s} variant="outline" className="text-xs">
                        {s}
                      </Badge>
                    ))}
                  </div>
                ) : null;
              })()}
              {intel.product_url && (
                <a
                  href={intel.product_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-sky-400 hover:underline"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Company website
                </a>
              )}
            </>
          ) : (
            <p className="text-sm italic text-muted-foreground">
              Not researched yet — the hourly routine writes intel for each
              new job&apos;s company; check back after the next run.
            </p>
          )}
        </CardContent>
      </Card>

      {/* A–H Fit Evaluation */}
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0 pb-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Gauge className="h-4 w-4" />
              A–H Fit Evaluation
            </CardTitle>
            <CardDescription>
              Structured scoring of this role against your profile, by the
              research agent.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {(() => {
              const score = parseFitScore(evaluation);
              return score !== null ? (
                <Badge className={cn("tabular-nums", scoreColor(score))}>
                  {score.toFixed(1)} / 5
                </Badge>
              ) : null;
            })()}
            {evaluation && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleCopyText(evaluation, "evaluation")}
              >
                {copied === "evaluation" ? (
                  <Check className="mr-1.5 h-3.5 w-3.5" />
                ) : (
                  <Copy className="mr-1.5 h-3.5 w-3.5" />
                )}
                {copied === "evaluation" ? "Copied" : "Copy"}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {evaluation ? (
            <p className="rounded-md border bg-muted/40 p-3 text-sm leading-relaxed whitespace-pre-wrap break-words">
              {evaluation}
            </p>
          ) : job.applied ? (
            <p className="text-sm italic text-muted-foreground">
              Not evaluated yet — this job is in your tracker, so the research
              agent will score it (A–H) on an upcoming run.
            </p>
          ) : (
            <p className="text-sm italic text-muted-foreground">
              No current evaluation is stored for this job.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Generated content sections */}
      {SECTIONS.map((s) => (
        <Card key={s.type}>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0 pb-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <s.icon className="h-4 w-4" />
                {s.title}
              </CardTitle>
              <CardDescription>{s.description}</CardDescription>
            </div>
            {messages[s.type] && (
              <div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => handleCopy(s.type)}>
                {copied === s.type ? (
                  <Check className="mr-1.5 h-3.5 w-3.5" />
                ) : (
                  <Copy className="mr-1.5 h-3.5 w-3.5" />
                )}
                {copied === s.type ? "Copied" : "Copy"}
              </Button>{s.type === "cover_letter" && <Button variant="outline" size="sm" onClick={downloadCoverLetter}><Download className="mr-1.5 h-3.5 w-3.5" />Download</Button>}</div>
            )}
          </CardHeader>
          <CardContent>
            {messages[s.type] ? (
              <div className="space-y-2"><p className="rounded-md border bg-muted/40 p-3 text-sm leading-relaxed whitespace-pre-wrap break-words">{messages[s.type]}</p>
                {s.type === "cover_letter" && <p className="text-xs text-muted-foreground">Resume v{messageRows[s.type]?.resume_version} · JD v{messageRows[s.type]?.jd_version} · match {messageRows[s.type]?.match_score}/100 · generated {messageRows[s.type]?.generated_at ? new Date(messageRows[s.type].generated_at!).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : "time unavailable"}</p>}
              </div>
            ) : job.applied ? (
              <p className="text-sm italic text-muted-foreground">
                No current draft is stored for this job. The hourly routine
                only creates eligible, profile-current drafts.
              </p>
            ) : (
              <p className="text-sm italic text-muted-foreground">
                No current draft is stored for this job.
              </p>
            )}
          </CardContent>
        </Card>
      ))}

      {/* Mini Demo */}
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0 pb-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Zap className="h-4 w-4" />
              Mini Demo
            </CardTitle>
            <CardDescription>
              A small live demo built for this job&apos;s requirements —
              link it in your DM or email.
            </CardDescription>
          </div>
          {demoReady && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(`${API_URL}/api/demo/${jobId}`);
                  toast.success("Demo link copied");
                }}
              >
                <Copy className="mr-1.5 h-3.5 w-3.5" />
                Copy link
              </Button>
              <Button variant="outline" size="sm" asChild>
                <a
                  href={`${API_URL}/api/demo/${jobId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                  Open live
                </a>
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {demoReady ? (
            <iframe
              src={`${API_URL}/api/demo/${jobId}`}
              title="Mini demo preview"
              className="h-96 w-full rounded-md border bg-black"
            />
          ) : job.applied ? (
            <p className="text-sm italic text-muted-foreground">
              Not built yet — this job is in your tracker, so the hourly
              routine will build its demo on an upcoming run.
            </p>
          ) : (
            <p className="text-sm italic text-muted-foreground">
              No demo is stored for this job.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Recipient links + email finder */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Send it to</CardTitle>
          <CardDescription>
            Find the person on LinkedIn, or guess their work email below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <a
              href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${job.company} recruiter`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sky-400 hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Recruiters at {job.company}
            </a>
            <a
              href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${job.company} hiring manager`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sky-400 hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Hiring managers at {job.company}
            </a>
          </div>

          <div className="rounded-lg border bg-muted/30 p-3 space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Mail className="h-4 w-4" />
              Recruiter email finder
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                value={extraName}
                onChange={(e) => setExtraName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleFindEmails();
                }}
                placeholder="Recruiter name (optional — e.g. Priya Sharma)"
                className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <Button
                onClick={handleFindEmails}
                disabled={emailLoading}
                className="shrink-0"
              >
                {emailLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Mail className="h-4 w-4" />
                )}
                Find emails
              </Button>
            </div>

            {emailReport?.ok === false && (
              <p className="text-xs italic text-muted-foreground">
                {emailReport.reason === "no_domain"
                  ? "No company website known yet — the hourly routine adds it with company intel, or type a name and it will still guess once a domain is known."
                  : "Add a recruiter name above to search."}
              </p>
            )}

            {emailReport?.ok && (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Domain{" "}
                  <span className="font-mono">{emailReport.domain}</span>
                  {emailReport.mx_ok
                    ? " receives mail"
                    : " has no mail server"}
                  {emailReport.smtp_checked
                    ? emailReport.catch_all
                      ? " · accepts every address (can't confirm a single mailbox)"
                      : " · mailboxes verified live"
                    : " · guessed from the usual patterns (live verify unavailable here)"}
                  .
                </p>
                {(emailReport.contacts || []).map((c) => (
                  <div key={c.name} className="space-y-1.5">
                    <p className="text-sm font-medium">{c.name}</p>
                    <div className="space-y-1">
                      {c.candidates.map((cand) => (
                        <div
                          key={cand.email}
                          className="flex items-center justify-between gap-2 rounded-md border bg-background px-2.5 py-1.5"
                        >
                          <span className="truncate font-mono text-xs">
                            {cand.email}
                          </span>
                          <div className="flex shrink-0 items-center gap-1.5">
                            <Badge
                              variant={
                                cand.status === "valid"
                                  ? "default"
                                  : "outline"
                              }
                              className="text-[10px]"
                            >
                              {cand.status === "valid"
                                ? "verified"
                                : cand.status === "catch_all"
                                  ? "catch-all"
                                  : cand.status === "invalid"
                                    ? "invalid"
                                    : cand.status === "no_mx"
                                      ? "no mail"
                                      : "guess"}
                            </Badge>
                            <button
                              onClick={() =>
                                handleCopyText(cand.email, cand.email)
                              }
                              className="text-muted-foreground hover:text-foreground"
                              title="Copy"
                            >
                              {copied === cand.email ? (
                                <Check className="h-3.5 w-3.5" />
                              ) : (
                                <Copy className="h-3.5 w-3.5" />
                              )}
                            </button>
                            <a
                              href={`mailto:${cand.email}`}
                              className="text-sky-400 hover:text-sky-300"
                              title="Compose"
                            >
                              <Mail className="h-3.5 w-3.5" />
                            </a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                <p className="text-[11px] italic text-muted-foreground">
                  Guesses are the standard corporate patterns; confirm before
                  sending anything important.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
