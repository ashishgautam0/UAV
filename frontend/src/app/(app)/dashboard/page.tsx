"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getDashboard,
  getFollowUps,
  getFollowUpDraft,
  getWeeklyTrend,
  getPlatformEffectiveness,
  getStatusFunnel,
  getRoleAnalysis,
  getFollowUpEffectiveness,
  snoozeFollowUp,
} from "@/lib/api";
import type {
  DashboardStats,
  FollowUp,
  FollowUpDraft,
  FollowUpEffectiveness,
  WeeklyTrend,
  PlatformEffectiveness,
  StatusFunnel,
  RoleAnalysis,
} from "@/lib/types";

import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Briefcase,
  Clock,
  Copy,
  GraduationCap,
  Loader2,
  MessageSquare,
  MessageSquareText,
  ThumbsUp,
  Trophy,
  XCircle,
  AlertTriangle,
  TrendingUp,
  Moon,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

// Tasks per day on the /prep28 page, as [blockA, blockB, recall] — used to
// read its localStorage progress ("prep28") for the widget below.
const PREP_COUNTS: [number, number, number][] = [
  [2,2,3],[2,2,3],[2,2,3],[2,3,3],[1,1,3],[2,2,3],[2,3,2],
  [1,2,3],[2,2,3],[2,2,3],[1,3,3],[2,3,3],[2,3,3],[2,3,3],
  [1,2,3],[1,2,3],[1,2,3],[1,2,3],[2,2,3],[2,2,3],[2,3,2],
  [1,2,3],[2,2,2],[1,2,2],[1,2,2],[1,2,2],[2,2,2],[1,2,2],
];
const PREP_TOTAL = PREP_COUNTS.reduce((s, [a, b, r]) => s + a + b + r, 0);

interface PrepState {
  started: boolean;
  day: number;
  planDone: number;
  todayDone: number;
  todayTotal: number;
}

function readPrepState(): PrepState | null {
  try {
    const raw = localStorage.getItem("prep28");
    if (!raw) return { started: false, day: 1, planDone: 0, todayDone: 0, todayTotal: 0 };
    const s = JSON.parse(raw);
    let day = 1;
    if (s.dayOverride) day = s.dayOverride;
    else if (s.start) {
      const t = new Date();
      t.setHours(0, 0, 0, 0);
      day = Math.min(28, Math.max(1, Math.floor((t.getTime() - new Date(s.start).getTime()) / 86400000) + 1));
    }
    const done = s.done || {};
    let planDone = 0;
    let todayDone = 0;
    for (const k of Object.keys(done)) {
      if (!done[k]) continue;
      planDone++;
      if (k.startsWith(day + "-")) todayDone++;
    }
    const [a, b, r] = PREP_COUNTS[day - 1];
    return { started: Boolean(s.start), day, planDone, todayDone, todayTotal: a + b + r };
  } catch {
    return null;
  }
}

const WEEKLY_TARGET = 50;

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const router = useRouter();
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [prep, setPrep] = useState<PrepState | null>(null);
  const [fuDrafts, setFuDrafts] = useState<Record<number, FollowUpDraft>>({});
  const [fuOpen, setFuOpen] = useState<Set<number>>(new Set());
  const [fuLoading, setFuLoading] = useState<number | null>(null);

  useEffect(() => {
    setPrep(readPrepState());
  }, []);

  const toggleFuDraft = async (fu: FollowUp) => {
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
  };
  const [weeklyTrend, setWeeklyTrend] = useState<WeeklyTrend[]>([]);
  const [platformData, setPlatformData] = useState<PlatformEffectiveness[]>([]);
  const [statusFunnel, setStatusFunnel] = useState<StatusFunnel | null>(null);
  const [roleAnalysis, setRoleAnalysis] = useState<RoleAnalysis[]>([]);
  const [effectiveness, setEffectiveness] = useState<FollowUpEffectiveness | null>(null);

  useEffect(() => {
    async function fetchAll() {
      try {
        const [
          dashboardRes,
          followUpsRes,
          weeklyTrendRes,
          platformRes,
          statusFunnelRes,
          roleAnalysisRes,
          effectivenessRes,
        ] = await Promise.allSettled([
          getDashboard(),
          getFollowUps(),
          getWeeklyTrend(),
          getPlatformEffectiveness(),
          getStatusFunnel(),
          getRoleAnalysis(),
          getFollowUpEffectiveness(),
        ]);

        if (dashboardRes.status === "fulfilled") setStats(dashboardRes.value);
        if (followUpsRes.status === "fulfilled") setFollowUps(Array.isArray(followUpsRes.value) ? followUpsRes.value : []);
        if (weeklyTrendRes.status === "fulfilled") setWeeklyTrend(Array.isArray(weeklyTrendRes.value) ? weeklyTrendRes.value : []);
        if (platformRes.status === "fulfilled") setPlatformData(Array.isArray(platformRes.value) ? platformRes.value : []);
        if (statusFunnelRes.status === "fulfilled" && statusFunnelRes.value && typeof statusFunnelRes.value === "object") setStatusFunnel(statusFunnelRes.value);
        if (roleAnalysisRes.status === "fulfilled") setRoleAnalysis(Array.isArray(roleAnalysisRes.value) ? roleAnalysisRes.value : []);
        if (effectivenessRes.status === "fulfilled") setEffectiveness(effectivenessRes.value);
      } catch (err) {
        console.error("Failed to load dashboard data", err);
      } finally {
        setLoading(false);
      }
    }

    fetchAll();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-muted-foreground text-lg">Loading...</p>
      </div>
    );
  }

  const statCards = [
    {
      label: "Total Applied",
      value: stats?.total ?? 0,
      icon: Briefcase,
      color: "text-blue-400",
    },
    {
      label: "Awaiting Response",
      value: stats?.applied ?? 0,
      icon: Clock,
      color: "text-yellow-400",
    },
    {
      label: "Interviews",
      value: stats?.interview ?? 0,
      icon: ThumbsUp,
      color: "text-emerald-400",
    },
    {
      label: "Offers",
      value: stats?.offer ?? 0,
      icon: Trophy,
      color: "text-purple-400",
    },
    {
      label: "Rejected",
      value: stats?.rejected ?? 0,
      icon: XCircle,
      color: "text-red-400",
    },
  ];

  const weeklyProgress = stats?.this_week ?? 0;
  const weeklyPct = Math.min(
    Math.round((weeklyProgress / WEEKLY_TARGET) * 100),
    100
  );

  return (
    <div className="space-y-8">
      {/* ---- Page Header ---- */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Your job search at a glance — stats, trends, and follow-ups.
        </p>
      </div>

      {/* ---- 28-Day Interview Prep ---- */}
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 space-y-0">
          <div>
            <CardTitle className="flex items-center gap-2">
              <GraduationCap className="h-5 w-5 text-sky-400" />
              28-Day Interview Prep
            </CardTitle>
            <CardDescription>
              {prep?.started
                ? `Day ${prep.day} of 28 — coding patterns, ML/GenAI depth, night recall`
                : "Your daily prep plan — pick a Day 1 to start the clock"}
            </CardDescription>
          </div>
          <Button size="sm" asChild>
            <Link href="/prep28">
              {prep?.started ? "Open today's plan" : "Start the 28 days"}
            </Link>
          </Button>
        </CardHeader>
        {prep?.started && (
          <CardContent className="space-y-2">
            <Progress
              value={Math.round((100 * prep.planDone) / PREP_TOTAL)}
              className="h-3"
            />
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>
                today {prep.todayDone}/{prep.todayTotal}
              </span>
              <span>
                plan {prep.planDone}/{PREP_TOTAL} ·{" "}
                {Math.round((100 * prep.planDone) / PREP_TOTAL)}%
              </span>
            </div>
          </CardContent>
        )}
      </Card>

      {/* ---- Empty State CTA ---- */}
      {stats?.total === 0 && (
        <Card className="border-dashed border-2">
          <CardContent className="flex flex-col items-center gap-4 pt-8 pb-8 text-center">
            <Moon className="h-12 w-12 text-muted-foreground" />
            <div>
              <p className="text-lg font-semibold">No applications yet</p>
              <p className="text-muted-foreground text-sm mt-1">
                Start by checking today&apos;s scraped jobs and logging your first application.
              </p>
            </div>
            <Button asChild>
              <Link href="/tonight">
                <Moon className="mr-2 h-4 w-4" />
                Go to Today Todo
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ---- Stat Cards ---- */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {statCards.map((s) => (
          <Card key={s.label}>
            <CardContent className="flex flex-col items-center gap-2 pt-6 text-center">
              <s.icon className={`h-6 w-6 ${s.color}`} />
              <p className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
                {s.label}
              </p>
              <p className="text-3xl font-bold">{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ---- Weekly Progress ---- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-emerald-400" />
            Weekly Progress
          </CardTitle>
          <CardDescription>
            {weeklyProgress} / {WEEKLY_TARGET} applications this week
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Progress value={weeklyPct} className="h-3" />
          <p className="text-muted-foreground text-right text-sm">
            {weeklyPct}%
          </p>
        </CardContent>
      </Card>

      {/* ---- Follow-ups Due ---- */}
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
              {followUps.map((fu) => {
                const today = new Date().toISOString().split("T")[0];
                const isOverdue = fu.follow_up_date < today;
                const isDueToday = fu.follow_up_date === today;
                const borderClass = isOverdue
                  ? "border-red-500/60 bg-red-500/5"
                  : isDueToday
                    ? "border-amber-500/60 bg-amber-500/10"
                    : "border-amber-500/40 bg-amber-500/5";
                const dateClass = isOverdue
                  ? "text-red-400 font-medium"
                  : isDueToday
                    ? "text-amber-400 font-medium"
                    : "text-amber-400";
                return (
                  <div
                    key={fu.id}
                    className={`rounded-lg border p-4 space-y-1 ${borderClass}`}
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-semibold">{fu.company}</p>
                      <div className="flex items-center gap-1.5">
                        {isOverdue && (
                          <Badge variant="outline" className="text-[10px] h-5 bg-red-500/10 text-red-400 border-red-500/30">
                            Overdue
                          </Badge>
                        )}
                        {isDueToday && (
                          <Badge variant="outline" className="text-[10px] h-5 bg-amber-500/10 text-amber-400 border-amber-500/30">
                            Today
                          </Badge>
                        )}
                        {(fu.follow_up_count ?? 0) > 0 && (
                          <Badge variant="outline" className="text-[10px] h-5 bg-amber-500/10 text-amber-400 border-amber-500/30">
                            #{(fu.follow_up_count ?? 0) + 1} of 3
                          </Badge>
                        )}
                      </div>
                    </div>
                    <p className="text-muted-foreground text-sm">{fu.role}</p>
                    <div className="flex items-center justify-between pt-1">
                      <span className={`text-xs ${dateClass}`}>
                        {fu.follow_up_date}
                      </span>
                      <div className="flex items-center gap-2">
                        <input
                          type="date"
                          className="h-6 w-[120px] rounded border border-border bg-background px-1 text-[10px] text-muted-foreground cursor-pointer"
                          min={new Date().toISOString().split("T")[0]}
                          onChange={async (e) => {
                            if (!e.target.value) return;
                            await snoozeFollowUp(fu.id, e.target.value);
                            setFollowUps((prev) =>
                              prev.map((f) =>
                                f.id === fu.id ? { ...f, follow_up_date: e.target.value } : f
                              )
                            );
                          }}
                          title="Snooze to a different date"
                        />
                        <span className="text-muted-foreground text-xs capitalize">
                          {fu.status}
                        </span>
                      </div>
                    </div>
                    {fuOpen.has(fu.id) && fuDrafts[fu.id]?.content && (
                      <div className="rounded-md border border-emerald-600/30 bg-emerald-600/5 p-3 space-y-2 mt-2">
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
                        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                          {fuDrafts[fu.id]?.content}
                        </p>
                      </div>
                    )}
                    <div className="flex gap-2 pt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        disabled={fuLoading === fu.id}
                        onClick={() => toggleFuDraft(fu)}
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
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ---- Follow-up Effectiveness ---- */}
      {effectiveness && effectiveness.overall.total > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-blue-400" />
              Follow-up Effectiveness
            </CardTitle>
            <CardDescription>
              Response rates from your follow-up messages.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-3xl font-bold">{effectiveness.overall.rate}%</p>
                <p className="text-xs text-muted-foreground">Response Rate</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold">{effectiveness.overall.total}</p>
                <p className="text-xs text-muted-foreground">Total Sent</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-emerald-400">{effectiveness.overall.responded}</p>
                <p className="text-xs text-muted-foreground">Responded</p>
              </div>
            </div>
            {effectiveness.by_channel.length > 1 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">By Channel</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {effectiveness.by_channel.map((ch) => (
                      <div key={ch.channel} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                        <span>{ch.channel}</span>
                        <span className="text-muted-foreground">{ch.responded}/{ch.total} ({ch.rate}%)</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
            {effectiveness.by_number.length > 1 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <p className="text-sm font-medium text-muted-foreground">By Attempt</p>
                  <div className="grid gap-2 sm:grid-cols-3">
                    {effectiveness.by_number.map((n) => (
                      <div key={n.follow_up_number} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                        <span>Follow-up #{n.follow_up_number}</span>
                        <span className="text-muted-foreground">{n.rate}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}

      <Separator />

      {/* ---- Platform Effectiveness ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Platform Effectiveness</CardTitle>
          <CardDescription>
            Response rates across different application platforms.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {platformData.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No platform data available yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Platform</TableHead>
                  <TableHead className="text-right">Applications</TableHead>
                  <TableHead className="text-right">Responses</TableHead>
                  <TableHead className="w-[200px]">Rate</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {platformData.map((p) => (
                  <TableRow key={p.platform}>
                    <TableCell className="font-medium">{p.platform}</TableCell>
                    <TableCell className="text-right">
                      {p.applications}
                    </TableCell>
                    <TableCell className="text-right">{p.responses}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress
                          value={p.response_rate ?? 0}
                          className="h-2 flex-1"
                        />
                        <span className="text-muted-foreground w-12 text-right text-xs">
                          {(p.response_rate ?? 0).toFixed(1)}%
                        </span>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ---- Status Funnel ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Status Funnel</CardTitle>
          <CardDescription>
            Breakdown of applications by current status.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!statusFunnel || Object.keys(statusFunnel).length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No status data available yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(statusFunnel).map(([status, count]) => (
                  <TableRow key={status}>
                    <TableCell className="font-medium capitalize">
                      {status}
                    </TableCell>
                    <TableCell className="text-right">{count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ---- Weekly Trend ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Weekly Trend</CardTitle>
          <CardDescription>
            Application volume over recent weeks.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {weeklyTrend.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No weekly trend data available yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Week</TableHead>
                  <TableHead className="text-right">Jobs</TableHead>
                  <TableHead className="text-right">Internships</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {weeklyTrend.map((w) => (
                  <TableRow key={w.week}>
                    <TableCell className="font-medium">{w.week}</TableCell>
                    <TableCell className="text-right">{w.Job ?? 0}</TableCell>
                    <TableCell className="text-right">
                      {w.Internship ?? 0}
                    </TableCell>
                    <TableCell className="text-right">{w.total}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ---- Role Analysis ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Role Analysis</CardTitle>
          <CardDescription>
            How different role keywords perform in your applications.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {roleAnalysis.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No role analysis data available yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Role Keyword</TableHead>
                  <TableHead className="text-right">Applied</TableHead>
                  <TableHead className="text-right">Responses</TableHead>
                  <TableHead className="text-right">Rate</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {roleAnalysis.map((r) => (
                  <TableRow key={r.role_keyword}>
                    <TableCell className="font-medium">
                      {r.role_keyword}
                    </TableCell>
                    <TableCell className="text-right">{r.applied}</TableCell>
                    <TableCell className="text-right">{r.responses}</TableCell>
                    <TableCell className="text-right">
                      {(r.response_rate ?? 0).toFixed(1)}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
