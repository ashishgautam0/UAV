"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getScrapedJobs, getFollowUps, createApplication, markScrapedJob, getJobMessage, getFollowUpDraft, deleteScrapedJob } from "@/lib/api";
import type { ScrapedJob, FollowUp, FollowUpDraft } from "@/lib/types";

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
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Loader2,
  ExternalLink,
  ClipboardPlus,
  Building2,
  MapPin,
  AlertTriangle,
  Check,
  Copy,
  FileText,
  MessageSquare,
  MessageSquareText,
  RefreshCw,
  XCircle,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function scoreBadgeColor(score: number) {
  if (score >= 60) return "bg-emerald-600 text-white";
  if (score >= 30) return "bg-yellow-500 text-black";
  return "bg-red-600 text-white";
}

function workModeBadgeColor(mode: string | undefined) {
  const m = (mode ?? "").toLowerCase();
  if (m === "remote") return "bg-emerald-600/15 text-emerald-400 border-emerald-600/30";
  if (m === "hybrid") return "bg-blue-600/15 text-blue-400 border-blue-600/30";
  return "bg-orange-600/15 text-orange-400 border-orange-600/30";
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------
export default function TonightPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState<ScrapedJob[]>([]);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [loggedJobs, setLoggedJobs] = useState<Set<string>>(new Set());
  const [filterMode, setFilterMode] = useState<"all" | "remote" | "hybrid" | "onsite">("all");
  const [dmByJob, setDmByJob] = useState<Record<number, string | null>>({});
  const [dmOpen, setDmOpen] = useState<Set<number>>(new Set());
  const [dmLoading, setDmLoading] = useState<number | null>(null);
  const [fuDrafts, setFuDrafts] = useState<Record<number, FollowUpDraft>>({});
  const [fuOpen, setFuOpen] = useState<Set<number>>(new Set());
  const [fuLoading, setFuLoading] = useState<number | null>(null);

  // The API returns jobs newest-first (ordered by scraped_at desc) — keep
  // that order so the latest job is always on top.
  const filteredJobs = useMemo(() => {
    if (filterMode === "all") return jobs;
    return jobs.filter(
      (j) => (j.work_mode || "").toLowerCase() === filterMode
    );
  }, [jobs, filterMode]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [jobsData, followUpsData] = await Promise.all([
        getScrapedJobs(),
        getFollowUps(),
      ]);
      setJobs(jobsData);
      setFollowUps(followUpsData);
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ------- Log to tracker handler -------
  const handleLog = useCallback(async (job: ScrapedJob) => {
    const key = `${job.company}::${job.title}`;
    try {
      await createApplication({
        company: job.company,
        role: job.title,
        platform: job.source,
        url: job.url,
      });
      if (job.id) await markScrapedJob(job.id, "applied");
      setLoggedJobs((prev) => new Set(prev).add(key));
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      toast.success(`Logged ${job.company} - ${job.title} to tracker`);
    } catch {
      toast.error("Failed to log application");
    }
  }, []);

  // ------- View pre-written cold DM handler -------
  const handleToggleDm = useCallback(
    async (job: ScrapedJob) => {
      if (!job.id) return;
      const id = job.id;
      if (dmOpen.has(id)) {
        setDmOpen((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        return;
      }
      if (!(id in dmByJob)) {
        setDmLoading(id);
        try {
          const res = await getJobMessage(id);
          setDmByJob((prev) => ({ ...prev, [id]: res.content }));
          if (res.content === null) {
            toast.info(
              "No DM yet — DMs are written for jobs you log to the tracker."
            );
            return;
          }
        } catch {
          toast.error("Failed to load the DM");
          return;
        } finally {
          setDmLoading(null);
        }
      } else if (dmByJob[id] === null) {
        toast.info(
          "No DM yet — DMs are written for jobs you log to the tracker."
        );
        return;
      }
      setDmOpen((prev) => new Set(prev).add(id));
    },
    [dmOpen, dmByJob]
  );

  // ------- View pre-written follow-up draft handler -------
  const handleToggleFuDraft = useCallback(
    async (fu: FollowUp) => {
      const id = fu.id;
      if (fuOpen.has(id)) {
        setFuOpen((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        return;
      }
      let draft = fuDrafts[id];
      if (!draft) {
        setFuLoading(id);
        try {
          draft = await getFollowUpDraft(id);
          setFuDrafts((prev) => ({ ...prev, [id]: draft }));
        } catch {
          toast.error("Failed to load the follow-up draft");
          return;
        } finally {
          setFuLoading(null);
        }
      }
      if (draft.status === "ready" && draft.content) {
        setFuOpen((prev) => new Set(prev).add(id));
      } else if (draft.status === "pending") {
        toast.info("Queued — the next hourly run writes this follow-up.");
      } else {
        toast.info(
          "Not queued yet — the hourly run queues it now that the follow-up date is due."
        );
      }
    },
    [fuOpen, fuDrafts]
  );

  // ------- Dismiss handler (permanently deletes the job) -------
  const handleDismiss = useCallback(async (job: ScrapedJob) => {
    try {
      if (job.id) await deleteScrapedJob(job.id);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
      toast.success(`Deleted ${job.company} - ${job.title}`);
    } catch {
      toast.error("Failed to delete job");
    }
  }, []);

  return (
    <div className="space-y-8">
      {/* ---- Page Header ---- */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Today Todo
          </h1>
          <p className="text-muted-foreground mt-1">
            Latest scraped jobs and follow-ups for your application list.
          </p>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Refresh
        </Button>
      </div>

      {/* ---- Loading State ---- */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && (
        <>
          {/* ---- Section 1: Follow-ups Due ---- */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-400" />
                Follow-ups Due
              </CardTitle>
              <CardDescription>
                Applications that need a follow-up soon.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {followUps.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No follow-ups due. You&apos;re all caught up!
                </p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {followUps.map((fu) => (
                    <div
                      key={fu.id}
                      className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 space-y-2"
                    >
                      <p className="font-semibold">{fu.company}</p>
                      <p className="text-muted-foreground text-sm">
                        {fu.role}
                      </p>
                      <div className="flex items-center justify-between pt-1">
                        <span className="text-xs text-amber-400">
                          {fu.follow_up_date}
                        </span>
                        <span className="text-muted-foreground text-xs capitalize">
                          {fu.status}
                        </span>
                      </div>
                      {fuOpen.has(fu.id) && fuDrafts[fu.id]?.content && (
                        <div className="rounded-md border border-emerald-600/30 bg-emerald-600/5 p-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-emerald-400">
                              Follow-up #{fuDrafts[fu.id]?.follow_up_number ?? 1}{" "}
                              (auto-written)
                            </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 px-2 text-xs"
                              onClick={() => {
                                navigator.clipboard.writeText(
                                  fuDrafts[fu.id]?.content || ""
                                );
                                toast.success("Follow-up copied to clipboard");
                              }}
                            >
                              <Copy className="mr-1 h-3 w-3" />
                              Copy
                            </Button>
                          </div>
                          <p className="text-sm leading-relaxed whitespace-pre-wrap">
                            {fuDrafts[fu.id]?.content}
                          </p>
                        </div>
                      )}
                      <div className="flex gap-2 mt-1">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          disabled={fuLoading === fu.id}
                          onClick={() => handleToggleFuDraft(fu)}
                        >
                          {fuLoading === fu.id ? (
                            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <MessageSquareText className="mr-1.5 h-3.5 w-3.5" />
                          )}
                          {fuOpen.has(fu.id) ? "Hide Draft" : "View Draft"}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => {
                            const params = new URLSearchParams({
                              company: fu.company,
                              role: fu.role,
                              type: "follow-up",
                            });
                            router.push(`/messages?${params.toString()}`);
                          }}
                        >
                          <MessageSquare className="mr-1.5 h-3.5 w-3.5" />
                          Write
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Separator />

          {/* ---- Section 2: Scraped Jobs ---- */}
          <div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
              <h2 className="text-2xl font-semibold tracking-tight">
                Latest Scraped Jobs
                {jobs.length > 0 && (
                  <span className="text-muted-foreground text-base font-normal ml-2">
                    ({filteredJobs.length}{filterMode !== "all" ? ` of ${jobs.length}` : ""})
                  </span>
                )}
              </h2>
              {jobs.length > 0 && (
                <div className="flex gap-2">
                  <Select value={filterMode} onValueChange={(v) => setFilterMode(v as typeof filterMode)}>
                    <SelectTrigger className="w-[130px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Modes</SelectItem>
                      <SelectItem value="remote">Remote</SelectItem>
                      <SelectItem value="hybrid">Hybrid</SelectItem>
                      <SelectItem value="onsite">Onsite</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
            {jobs.length === 0 ? (
              <p className="text-muted-foreground text-sm">
                No scraped jobs yet. Jobs are fetched automatically every hour
                by the scheduled Claude routine.
              </p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {filteredJobs.map((job, idx) => {
                  const key = `${job.company}::${job.title}`;
                  const isLogged = loggedJobs.has(key);

                  return (
                    <Card key={job.id ?? idx} className="flex flex-col">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <CardTitle className="text-base leading-snug">
                              {job.title}
                            </CardTitle>
                            <div className="mt-1 flex items-center gap-1.5 text-sm font-semibold">
                              <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
                              {job.company}
                            </div>
                          </div>
                          {job.score > 0 && (
                            <Badge
                              className={cn(
                                "shrink-0 tabular-nums",
                                scoreBadgeColor(job.score)
                              )}
                            >
                              {job.score}
                            </Badge>
                          )}
                        </div>
                      </CardHeader>

                      <CardContent className="flex flex-1 flex-col gap-3 pt-0">
                        {/* Location */}
                        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                          <MapPin className="h-3.5 w-3.5 shrink-0" />
                          <span className="truncate">
                            {job.location || "Not specified"}
                          </span>
                        </div>

                        {/* Badges row */}
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
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                workModeBadgeColor(job.work_mode)
                              )}
                            >
                              {job.work_mode}
                            </Badge>
                          )}
                          <Badge variant="secondary" className="text-xs">
                            {job.source}
                          </Badge>
                        </div>

                        {/* LLM Reason */}
                        {job.llm_reason && (
                          <p className="text-muted-foreground text-xs italic leading-relaxed">
                            {job.llm_reason}
                          </p>
                        )}

                        {/* Pre-written cold DM (from the hourly Claude routine) */}
                        {job.id && dmOpen.has(job.id) && dmByJob[job.id] && (
                          <div className="rounded-md border border-emerald-600/30 bg-emerald-600/5 p-3 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-medium text-emerald-400">
                                Cold DM (auto-written)
                              </span>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 px-2 text-xs"
                                onClick={() => {
                                  navigator.clipboard.writeText(dmByJob[job.id!] || "");
                                  toast.success("DM copied to clipboard");
                                }}
                              >
                                <Copy className="mr-1 h-3 w-3" />
                                Copy
                              </Button>
                            </div>
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">
                              {dmByJob[job.id]}
                            </p>
                            <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-emerald-600/20 pt-2 text-xs">
                              <span className="text-muted-foreground">Send to:</span>
                              <a
                                href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${job.company} recruiter`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-sky-400 hover:underline"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Recruiters at {job.company}
                              </a>
                              <a
                                href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(`${job.company} hiring manager`)}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-sky-400 hover:underline"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Hiring managers
                              </a>
                            </div>
                          </div>
                        )}

                        {/* Spacer */}
                        <div className="flex-1" />

                        {/* Action buttons */}
                        <div className="flex flex-wrap items-center gap-2 pt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            asChild
                          >
                            <a
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                              Apply
                            </a>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const params = new URLSearchParams({
                                title: job.title,
                                jd_text: (job.description || "").slice(0, 2000),
                              });
                              router.push(`/resume-tailor?${params.toString()}`);
                            }}
                          >
                            <FileText className="mr-1.5 h-3.5 w-3.5" />
                            Tailor Resume
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={dmLoading === job.id}
                            onClick={() => handleToggleDm(job)}
                          >
                            {dmLoading === job.id ? (
                              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <MessageSquareText className="mr-1.5 h-3.5 w-3.5" />
                            )}
                            {job.id && dmOpen.has(job.id) ? "Hide DM" : "View DM"}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const params = new URLSearchParams({
                                company: job.company,
                                role: job.title,
                                type: "cold-dm",
                              });
                              router.push(`/messages?${params.toString()}`);
                            }}
                          >
                            <MessageSquare className="mr-1.5 h-3.5 w-3.5" />
                            Message
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={isLogged}
                            onClick={() => handleLog(job)}
                          >
                            {isLogged ? (
                              <Check className="mr-1.5 h-3.5 w-3.5" />
                            ) : (
                              <ClipboardPlus className="mr-1.5 h-3.5 w-3.5" />
                            )}
                            {isLogged ? "Logged" : "Log"}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-muted-foreground hover:text-red-400"
                            onClick={() => handleDismiss(job)}
                          >
                            <XCircle className="mr-1.5 h-3.5 w-3.5" />
                            Dismiss
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
