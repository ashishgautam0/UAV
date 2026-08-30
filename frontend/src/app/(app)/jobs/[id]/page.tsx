"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  API_URL,
  getScrapedJob,
  getJobMessage,
  getCachedCompanyIntel,
  findRecruiterEmails,
  deleteScrapedJob,
  createApplication,
  markScrapedJob,
} from "@/lib/api";
import type {
  CachedCompanyIntel,
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
  ClipboardPlus,
  Copy,
  ExternalLink,
  FileText,
  Loader2,
  MapPin,
  MessageSquareText,
  Mail,
  Rocket,
  XCircle,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const SECTIONS = [
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
  const [intel, setIntel] = useState<CachedCompanyIntel | null>(null);
  const [evaluation, setEvaluation] = useState<string | null>(null);
  const [demoReady, setDemoReady] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [logged, setLogged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [emailReport, setEmailReport] = useState<RecruiterEmailReport | null>(
    null
  );
  const [emailLoading, setEmailLoading] = useState(false);
  const [extraName, setExtraName] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const j = await getScrapedJob(jobId);
      setJob(j);
      const results = await Promise.all(
        SECTIONS.map((s) =>
          getJobMessage(jobId, s.type).catch(() => ({ content: null }))
        )
      );
      const next: Record<string, string | null> = {};
      SECTIONS.forEach((s, i) => {
        next[s.type] = results[i]?.content ?? null;
      });
      setMessages(next);
      if (j.company) {
        getCachedCompanyIntel(j.company)
          .then(setIntel)
          .catch(() => setIntel({ found: false }));
      }
      getJobMessage(jobId, "evaluation")
        .then((r) => setEvaluation(r.content))
        .catch(() => setEvaluation(null));
      getJobMessage(jobId, "demo_html")
        .then((r) => setDemoReady(Boolean(r.content)))
        .catch(() => setDemoReady(false));
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

  async function handleLog() {
    if (!job) return;
    setBusy(true);
    try {
      await createApplication({
        company: job.company,
        role: job.title,
        platform: job.source,
        url: job.url,
      });
      await markScrapedJob(jobId, "applied");
      setLogged(true);
      toast.success(`Logged ${job.company} — ${job.title} to tracker`);
    } catch {
      toast.error("Failed to log application");
    } finally {
      setBusy(false);
    }
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

  async function handleDismiss() {
    setBusy(true);
    try {
      await deleteScrapedJob(jobId);
      toast.success("Job deleted");
      router.push("/tonight");
    } catch {
      toast.error("Failed to delete job");
      setBusy(false);
    }
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
          <span className="flex items-center gap-1.5">
            <MapPin className="h-4 w-4" />
            {job.location || "Not specified"}
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {job.verdict === "EASY_APPLY" && (
            <Badge className="text-xs bg-emerald-600/15 text-emerald-400 border-emerald-600/30">
              <Zap className="mr-1 h-3 w-3" />
              Easy Apply
            </Badge>
          )}
          {job.verdict === "EXTERNAL" && (
            <Badge
              variant="outline"
              className="text-xs text-sky-400 border-sky-500/30"
            >
              <ExternalLink className="mr-1 h-3 w-3" />
              External apply
            </Badge>
          )}
          {job.work_mode && (
            <Badge variant="outline" className="text-xs">
              {job.work_mode}
            </Badge>
          )}
          <Badge variant="secondary" className="text-xs">
            {job.source}
          </Badge>
        </div>

        {/* Primary actions */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button size="sm" asChild>
            <a href={job.url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
              Apply
            </a>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const p = new URLSearchParams({
                title: job.title,
                jd_text: (job.description || "").slice(0, 2000),
              });
              router.push(`/resume-tailor?${p.toString()}`);
            }}
          >
            <FileText className="mr-1.5 h-3.5 w-3.5" />
            Full Resume Tailor
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={busy || logged}
            onClick={handleLog}
          >
            {logged ? (
              <Check className="mr-1.5 h-3.5 w-3.5" />
            ) : (
              <ClipboardPlus className="mr-1.5 h-3.5 w-3.5" />
            )}
            {logged ? "Logged" : "Log to Tracker"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-red-400"
            disabled={busy}
            onClick={handleDismiss}
          >
            <XCircle className="mr-1.5 h-3.5 w-3.5" />
            Dismiss &amp; Delete
          </Button>
        </div>
      </div>

      {/* Apply Kit — everything needed to apply, in one place */}
      {(() => {
        const kit = [
          { key: "cold_dm", label: "Cold DM", ready: Boolean(messages["cold_dm"]) },
          { key: "hr_email", label: "Email + recipient", ready: Boolean(messages["hr_email"]) },
          { key: "resume_points", label: "Tailored resume notes", ready: Boolean(messages["resume_points"]) },
          { key: "demo", label: "Live demo", ready: demoReady },
        ];
        const readyCount = kit.filter((k) => k.ready).length;
        return (
          <Card className="border-primary/30">
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0 pb-2">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Rocket className="h-4 w-4 text-primary" />
                  Apply Kit
                </CardTitle>
                <CardDescription>
                  Apply in ~30 seconds — grab each piece, then hit apply.
                </CardDescription>
              </div>
              <Badge variant="outline" className="tabular-nums">
                {readyCount}/{kit.length} ready
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                <Button size="sm" asChild>
                  <a href={job.url} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                    Apply on {job.source || "LinkedIn"}
                  </a>
                </Button>
                {messages["cold_dm"] && (
                  <Button variant="outline" size="sm" onClick={() => handleCopy("cold_dm")}>
                    {copied === "cold_dm" ? <Check className="mr-1.5 h-3.5 w-3.5" /> : <MessageSquareText className="mr-1.5 h-3.5 w-3.5" />}
                    Copy DM
                  </Button>
                )}
                {messages["hr_email"] && (
                  <Button variant="outline" size="sm" onClick={() => handleCopy("hr_email")}>
                    {copied === "hr_email" ? <Check className="mr-1.5 h-3.5 w-3.5" /> : <Mail className="mr-1.5 h-3.5 w-3.5" />}
                    Copy email
                  </Button>
                )}
                {messages["resume_points"] && (
                  <Button variant="outline" size="sm" onClick={() => handleCopy("resume_points")}>
                    {copied === "resume_points" ? <Check className="mr-1.5 h-3.5 w-3.5" /> : <FileText className="mr-1.5 h-3.5 w-3.5" />}
                    Copy resume notes
                  </Button>
                )}
                {demoReady && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(`${API_URL}/api/demo/${jobId}`);
                      toast.success("Demo link copied");
                    }}
                  >
                    <Copy className="mr-1.5 h-3.5 w-3.5" />
                    Copy demo link
                  </Button>
                )}
              </div>
              {readyCount < kit.length && (
                <p className="text-xs text-muted-foreground">
                  {job.applied
                    ? "Remaining pieces are written by the hourly routine — check back shortly."
                    : "Log this job to the tracker and the next hourly run writes the rest."}
                </p>
              )}
            </CardContent>
          </Card>
        );
      })()}

      {/* Description */}
      {job.description && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Job Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed whitespace-pre-wrap break-words text-muted-foreground">
              {job.description}
            </p>
          </CardContent>
        </Card>
      )}

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
              Scored only for jobs you&apos;ve logged to the tracker — hit
              &quot;Log to Tracker&quot; above and the next hourly run will
              evaluate it.
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
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleCopy(s.type)}
              >
                {copied === s.type ? (
                  <Check className="mr-1.5 h-3.5 w-3.5" />
                ) : (
                  <Copy className="mr-1.5 h-3.5 w-3.5" />
                )}
                {copied === s.type ? "Copied" : "Copy"}
              </Button>
            )}
          </CardHeader>
          <CardContent>
            {messages[s.type] ? (
              <p className="rounded-md border bg-muted/40 p-3 text-sm leading-relaxed whitespace-pre-wrap break-words">
                {messages[s.type]}
              </p>
            ) : job.applied ? (
              <p className="text-sm italic text-muted-foreground">
                Not written yet — this job is in your tracker, so the hourly
                routine will write it on an upcoming run.
              </p>
            ) : (
              <p className="text-sm italic text-muted-foreground">
                Written only for jobs you&apos;ve logged to the tracker — hit
                &quot;Log to Tracker&quot; above and the next hourly run will
                write it.
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
              Demos are built only for jobs you&apos;ve logged to the
              tracker — hit &quot;Log to Tracker&quot; above and the next
              hourly run will build one for this job.
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
