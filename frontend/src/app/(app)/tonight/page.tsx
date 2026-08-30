"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getRankedScrapedJobs, createApplication, markScrapedJob, deleteScrapedJob } from "@/lib/api";
import type { ScrapedJob } from "@/lib/types";

import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
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
import {
  Loader2,
  ExternalLink,
  ClipboardPlus,
  Building2,
  MapPin,
  RefreshCw,
  Trash2,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function bestScoreColor(score: number) {
  if (score >= 70) return "bg-emerald-600 text-white";
  if (score >= 50) return "bg-yellow-500 text-black";
  return "bg-muted text-muted-foreground";
}

function workModeBadgeColor(mode: string | undefined) {
  const m = (mode ?? "").toLowerCase();
  if (m === "remote") return "bg-emerald-600/15 text-emerald-400 border-emerald-600/30";
  if (m === "hybrid") return "bg-blue-600/15 text-blue-400 border-blue-600/30";
  return "bg-orange-600/15 text-orange-400 border-orange-600/30";
}

// ---------------------------------------------------------------------------
// SwipeableCard — gestures over a scraped-job card:
//   • tap / click            → onTap   (apply)
//   • swipe LEFT past thresh → onRemove (delete)
//   • swipe RIGHT past thresh→ onLog    (log to tracker)
// A "Remove" (red, right side) or "Log" (green, left side) backdrop is
// revealed as the card slides; it snaps back if released before the
// threshold. Gestures that start on a button/link are ignored so those
// controls keep working normally.
// ---------------------------------------------------------------------------
const SWIPE_THRESHOLD = 96; // px of horizontal drag needed to trigger an action
const TAP_SLOP = 8; // px of movement under which a gesture counts as a tap

function SwipeableCard({
  onTap,
  onLog,
  onRemove,
  children,
}: {
  onTap: () => void;
  onLog: () => void;
  onRemove: () => void;
  children: React.ReactNode;
}) {
  const [dx, setDx] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const startX = useRef<number | null>(null);
  const startY = useRef<number | null>(null);
  const horizontal = useRef(false);
  const moved = useRef(false);
  const ignore = useRef(false);

  const begin = (x: number, y: number, target: EventTarget | null) => {
    // Let buttons/links handle their own taps — don't hijack them.
    if (target instanceof Element && target.closest("button, a")) {
      ignore.current = true;
      return;
    }
    ignore.current = false;
    startX.current = x;
    startY.current = y;
    horizontal.current = false;
    moved.current = false;
    setDragging(true);
  };

  const move = (x: number, y: number) => {
    if (ignore.current || startX.current === null || startY.current === null) return;
    const deltaX = x - startX.current;
    const deltaY = y - startY.current;
    if (Math.abs(deltaX) > TAP_SLOP || Math.abs(deltaY) > TAP_SLOP) {
      moved.current = true;
    }
    // Lock to a horizontal gesture only once it clearly beats vertical scroll.
    if (!horizontal.current) {
      if (Math.abs(deltaX) > 10 && Math.abs(deltaX) > Math.abs(deltaY)) {
        horizontal.current = true;
      } else if (Math.abs(deltaY) > 10) {
        // vertical scroll — abandon this gesture
        startX.current = null;
        setDragging(false);
        setDx(0);
        return;
      }
    }
    if (horizontal.current) {
      setDx(deltaX); // travel both directions
    }
  };

  const end = () => {
    if (ignore.current) {
      ignore.current = false;
      return;
    }
    setDragging(false);
    const started = startX.current !== null;
    startX.current = null;
    startY.current = null;
    if (!started) {
      setDx(0);
      return;
    }
    if (dx <= -SWIPE_THRESHOLD) {
      setLeaving(true);
      setDx(-window.innerWidth);
      setTimeout(onRemove, 180); // let the slide-out play, then drop the row
    } else if (dx >= SWIPE_THRESHOLD) {
      setLeaving(true);
      setDx(window.innerWidth);
      setTimeout(onLog, 180);
    } else if (!moved.current) {
      // A clean tap — treat as apply.
      setDx(0);
      onTap();
    } else {
      setDx(0);
    }
  };

  const removeProgress = Math.min(Math.abs(Math.min(dx, 0)) / SWIPE_THRESHOLD, 1);
  const logProgress = Math.min(Math.max(dx, 0) / SWIPE_THRESHOLD, 1);

  return (
    <div className="relative select-none overflow-hidden rounded-xl">
      {/* Green "Log" backdrop, revealed as the card slides right */}
      <div
        className="absolute inset-0 flex items-center justify-start rounded-xl bg-emerald-600/90 pl-6 text-white"
        style={{ opacity: logProgress }}
        aria-hidden
      >
        <span className="flex items-center gap-2 text-sm font-medium">
          <ClipboardPlus className="h-4 w-4" />
          Log to tracker
        </span>
      </div>

      {/* Red "Remove" backdrop, revealed as the card slides left */}
      <div
        className="absolute inset-0 flex items-center justify-end rounded-xl bg-red-600/90 pr-6 text-white"
        style={{ opacity: removeProgress }}
        aria-hidden
      >
        <span className="flex items-center gap-2 text-sm font-medium">
          <Trash2 className="h-4 w-4" />
          Remove
        </span>
      </div>

      <div
        className="cursor-pointer"
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onTap();
          }
        }}
        style={{
          transform: `translateX(${dx}px)`,
          transition: dragging ? "none" : "transform 0.18s ease-out",
        }}
        onTouchStart={(e) =>
          begin(e.touches[0].clientX, e.touches[0].clientY, e.target)
        }
        onTouchMove={(e) => move(e.touches[0].clientX, e.touches[0].clientY)}
        onTouchEnd={end}
        onMouseDown={(e) => begin(e.clientX, e.clientY, e.target)}
        onMouseMove={(e) => {
          if (dragging) move(e.clientX, e.clientY);
        }}
        onMouseUp={end}
        onMouseLeave={() => {
          if (dragging) end();
        }}
      >
        <div className={cn("transition-opacity", leaving && "opacity-0")}>
          {children}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------
export default function TonightPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState<ScrapedJob[]>([]);
  const [filterMode, setFilterMode] = useState<"all" | "remote" | "hybrid" | "onsite">("all");

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
      // Ranked best-first by BestScore (fit × freshness × ease).
      setJobs(await getRankedScrapedJobs());
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ------- Apply handler (open the posting) -------
  const handleApply = useCallback((job: ScrapedJob) => {
    if (job.url) window.open(job.url, "_blank", "noopener,noreferrer");
  }, []);

  // ------- Log to tracker handler -------
  const handleLog = useCallback(async (job: ScrapedJob) => {
    // Drop it from the list immediately so the swipe feels instant.
    setJobs((prev) => prev.filter((j) => j.id !== job.id));
    try {
      await createApplication({
        company: job.company,
        role: job.title,
        platform: job.source,
        url: job.url,
      });
      if (job.id) await markScrapedJob(job.id, "applied");
      toast.success(`Logged ${job.company} - ${job.title} to tracker`);
    } catch {
      toast.error("Failed to log application");
      loadData(); // restore the card if the log failed server-side
    }
  }, [loadData]);

  // ------- Remove handler (permanently deletes the job) -------
  const handleDismiss = useCallback(async (job: ScrapedJob) => {
    // Drop it from the list immediately so the swipe feels instant.
    setJobs((prev) => prev.filter((j) => j.id !== job.id));
    try {
      if (job.id) await deleteScrapedJob(job.id);
      toast.success(`Removed ${job.company} - ${job.title}`);
    } catch {
      toast.error("Failed to remove job");
      // Re-fetch to restore anything that failed to delete server-side.
      loadData();
    }
  }, [loadData]);

  return (
    <div className="space-y-8">
      {/* ---- Page Header ---- */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
            Today Todo
          </h1>
          <p className="text-muted-foreground mt-1">
            Ranked best-first by match, freshness &amp; ease. Tap to apply · swipe right to log · swipe left to remove.
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
          {/* ---- Scraped Jobs ---- */}
          <div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
              <h2 className="text-2xl font-semibold tracking-tight">
                Best Matches
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
                  return (
                    <SwipeableCard
                      key={job.id ?? idx}
                      onTap={() => handleApply(job)}
                      onLog={() => handleLog(job)}
                      onRemove={() => handleDismiss(job)}
                    >
                      <Card className="flex h-full flex-col">
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
                            {typeof job.bestscore === "number" && (
                              <Badge
                                title={
                                  job.bestscore_breakdown
                                    ? `fit ${Math.round(job.bestscore_breakdown.fit * 100)}% (${job.bestscore_breakdown.fit_source}) · freshness ${Math.round(job.bestscore_breakdown.freshness * 100)}%`
                                    : "BestScore"
                                }
                                className={cn(
                                  "shrink-0 tabular-nums",
                                  bestScoreColor(job.bestscore)
                                )}
                              >
                                {Math.round(job.bestscore)}
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

                          {/* Spacer */}
                          <div className="flex-1" />
                        </CardContent>
                      </Card>
                    </SwipeableCard>
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
