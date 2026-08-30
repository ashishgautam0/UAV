"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  PLAN,
  SESSION_NAMES,
  recallPrompt,
  recallAll,
  type BlockKey,
} from "@/lib/prep28";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { GraduationCap, Check, ExternalLink, Copy, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "prep28";

interface PrepState {
  start?: string | null;
  dayOverride?: number | null;
  sess?: BlockKey | null;
  done?: Record<string, boolean>;
}

function readState(): PrepState {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}
function writeState(s: PrepState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    /* private mode / blocked storage — ignore */
  }
}

const tid = (d: number, blk: BlockKey, i: number) => `${d}-${blk}-${i}`;

function autoSession(): BlockKey {
  const h = new Date().getHours();
  if (h >= 20 || h < 5) return "r";
  if (h < 9.5 && h >= 5) return "a";
  return "b";
}

function computeDay(s: PrepState): number {
  if (s.dayOverride) return s.dayOverride;
  if (!s.start) return 1;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.floor((today.getTime() - new Date(s.start).getTime()) / 86400000) + 1;
  return Math.min(28, Math.max(1, diff));
}

const BLOCK_ACCENT: Record<BlockKey, string> = {
  a: "text-primary",
  b: "text-emerald-400",
  r: "text-violet-400",
};

export default function Prep28Page() {
  const [mounted, setMounted] = useState(false);
  const [state, setState] = useState<PrepState>({});
  const [sess, setSess] = useState<BlockKey>("a");
  const [showStart, setShowStart] = useState(false);
  const [startInput, setStartInput] = useState(() =>
    new Date().toISOString().slice(0, 10)
  );

  useEffect(() => {
    const s = readState();
    setState(s);
    setSess(s.sess || autoSession());
    if (!s.start) setShowStart(true);
    setMounted(true);
  }, []);

  const day = useMemo(() => computeDay(state), [state]);
  const done = state.done || {};
  const isDone = useCallback((id: string) => Boolean(done[id]), [done]);

  function persist(next: PrepState) {
    setState(next);
    writeState(next);
  }

  function toggle(id: string) {
    const nextDone = { ...(state.done || {}), [id]: !isDone(id) };
    persist({ ...state, done: nextDone });
  }

  function pickDay(value: string) {
    persist({ ...state, dayOverride: value === "auto" ? null : Number(value) });
  }

  function pickSession(value: string) {
    // Manual pick is session-only; on reload it auto-detects again (matches
    // the original behaviour), so clear the stored session.
    setSess(value as BlockKey);
    persist({ ...state, sess: null });
  }

  function confirmStart() {
    persist({ ...state, start: startInput });
    setShowStart(false);
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Copied — paste it to Claude");
    } catch {
      toast.error("Copy failed");
    }
  }

  // ---- progress (identical maths to the original) ----
  const progress = useMemo(() => {
    let doneCount = 0;
    let total = 0;
    let tdone = 0;
    PLAN.forEach((p, di) => {
      (["a", "b", "r"] as BlockKey[]).forEach((b) => {
        const n = (b === "r" ? p.r : p[b]).length;
        total += n;
        for (let i = 0; i < n; i++) {
          if (done[tid(di + 1, b, i)]) {
            doneCount++;
            if (di + 1 === day) tdone++;
          }
        }
      });
    });
    const cur = PLAN[day - 1];
    const todayN = cur.a.length + cur.b.length + cur.r.length;
    return {
      pct: total ? (100 * doneCount) / total : 0,
      doneCount,
      total,
      tdone,
      todayN,
    };
  }, [done, day]);

  if (!mounted) return null;

  const cur = PLAN[day - 1];
  const footnote =
    sess === "r"
      ? "No screen after copying — paste the prompt to Claude, put the phone face-down, and answer out loud."
      : sess === "a"
        ? "Attempt before revealing. 25-minute cap on mediums — then read the solution and weak-list it."
        : "Interviews eat Block B, never Block A.";

  // carried tasks (a/b): unchecked from all previous days, this block
  const carried =
    sess === "r"
      ? []
      : Array.from({ length: day - 1 }, (_, k) => k + 1).flatMap((d) =>
          PLAN[d - 1][sess]
            .map((t, i) => ({ ...t, day: d, id: tid(d, sess, i) }))
            .filter((t) => !isDone(t.id))
        );

  // carried recall: unchecked from yesterday only
  const carriedRecall =
    sess === "r" && day > 1
      ? PLAN[day - 2].r
          .map((t, i) => ({ t, id: tid(day - 1, "r", i) }))
          .filter((x) => !isDone(x.id))
      : [];

  const todaysAB =
    sess === "r"
      ? []
      : PLAN[day - 1][sess].map((t, i) => ({ ...t, day, id: tid(day, sess, i) }));
  const abAllDone = todaysAB.length > 0 && todaysAB.every((t) => isDone(t.id));

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* First-run start-date prompt */}
      {showStart && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <Card className="w-full max-w-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <GraduationCap className="h-4 w-4 text-primary" />
                Start your 28-day plan
              </CardTitle>
              <CardDescription>
                Pick the day you began (or begin today). Day 1 counts from here.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                type="date"
                value={startInput}
                onChange={(e) => setStartInput(e.target.value)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              <Button className="w-full" onClick={confirmStart}>
                Start
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Header */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="flex items-center gap-2 text-2xl sm:text-3xl font-bold tracking-tight">
            <GraduationCap className="h-6 w-6 text-primary" />
            Day {day}
            <span className="text-muted-foreground text-base font-normal">
              of 28
            </span>
          </h1>
          <div className="flex gap-2">
            <Select
              value={state.dayOverride ? String(day) : "auto"}
              onValueChange={pickDay}
            >
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Day: auto</SelectItem>
                {Array.from({ length: 28 }, (_, i) => (
                  <SelectItem key={i + 1} value={String(i + 1)}>
                    Day {i + 1}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={sess} onValueChange={pickSession}>
              <SelectTrigger className="w-[130px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="a">Block A · Coding</SelectItem>
                <SelectItem value="b">Block B · ML/GenAI</SelectItem>
                <SelectItem value="r">Recall</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <p className={cn("text-sm font-medium", BLOCK_ACCENT[sess])}>
          {SESSION_NAMES[sess]} · {cur.tag}
        </p>

        {/* Progress */}
        <div className="space-y-1.5">
          <Progress value={progress.pct} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>today {progress.tdone}/{progress.todayN}</span>
            <span>
              plan {progress.doneCount}/{progress.total} ·{" "}
              {Math.round(progress.pct)}%
            </span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-3">
        {sess === "r" ? (
          <>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => copy(recallAll(cur.r, day))}
            >
              <Sparkles className="mr-2 h-4 w-4" />
              Copy tonight&apos;s full recall prompt
            </Button>

            {carriedRecall.length > 0 && (
              <>
                <p className="pt-1 text-xs font-semibold uppercase tracking-wide text-amber-400">
                  Blanked yesterday — revise first
                </p>
                {carriedRecall.map((x) => (
                  <RecallCard
                    key={x.id}
                    topic={x.t}
                    done={isDone(x.id)}
                    fromDay={day - 1}
                    onToggle={() => toggle(x.id)}
                    onCopy={() => copy(recallPrompt(x.t, day))}
                  />
                ))}
              </>
            )}

            <p className="pt-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Tonight · Day {day}
            </p>
            {cur.r.map((topic, i) => {
              const id = tid(day, "r", i);
              return (
                <RecallCard
                  key={id}
                  topic={topic}
                  done={isDone(id)}
                  onToggle={() => toggle(id)}
                  onCopy={() => copy(recallPrompt(topic, day))}
                />
              );
            })}
          </>
        ) : (
          <>
            {carried.length > 0 && (
              <>
                <p className="pt-1 text-xs font-semibold uppercase tracking-wide text-amber-400">
                  Carried over ({carried.length})
                </p>
                {carried.map((t) => (
                  <TaskCard
                    key={t.id}
                    task={t}
                    done={isDone(t.id)}
                    fromDay={t.day}
                    onToggle={() => toggle(t.id)}
                  />
                ))}
              </>
            )}

            <p className="pt-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Today · Day {day}
            </p>
            {abAllDone && (
              <p className="rounded-md border border-emerald-600/30 bg-emerald-600/5 p-3 text-sm text-emerald-400">
                Block complete. Close the app.
              </p>
            )}
            {todaysAB.map((t) => (
              <TaskCard
                key={t.id}
                task={t}
                done={isDone(t.id)}
                onToggle={() => toggle(t.id)}
              />
            ))}
          </>
        )}

        <p className="pt-2 text-xs italic text-muted-foreground">{footnote}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
function CheckButton({ done, onToggle }: { done: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      aria-label={done ? "mark not done" : "mark done"}
      className={cn(
        "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-colors",
        done
          ? "border-primary bg-primary text-primary-foreground"
          : "border-muted-foreground/40 hover:border-primary"
      )}
    >
      {done && <Check className="h-3.5 w-3.5" />}
    </button>
  );
}

function TaskCard({
  task,
  done,
  fromDay,
  onToggle,
}: {
  task: { t: string; d: string; u: string };
  done: boolean;
  fromDay?: number;
  onToggle: () => void;
}) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border bg-card p-3 shadow-sm transition-opacity",
        done && "opacity-55"
      )}
    >
      <CheckButton done={done} onToggle={onToggle} />
      <div className="min-w-0 flex-1 space-y-1">
        <p className={cn("text-sm font-medium leading-snug", done && "line-through")}>
          {task.t}
        </p>
        <p className="text-xs leading-relaxed text-muted-foreground">{task.d}</p>
        {fromDay !== undefined && (
          <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-500/30">
            from Day {fromDay}
          </Badge>
        )}
        <a
          href={task.u}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-0.5 inline-flex items-center gap-1 text-xs text-sky-400 hover:underline"
        >
          Open on Educative
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>
    </div>
  );
}

function RecallCard({
  topic,
  done,
  fromDay,
  onToggle,
  onCopy,
}: {
  topic: string;
  done: boolean;
  fromDay?: number;
  onToggle: () => void;
  onCopy: () => void;
}) {
  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border bg-card p-3 shadow-sm transition-opacity",
        done && "opacity-55"
      )}
    >
      <CheckButton done={done} onToggle={onToggle} />
      <div className="min-w-0 flex-1 space-y-1.5">
        <p className={cn("text-sm leading-snug", done && "line-through")}>{topic}</p>
        {fromDay !== undefined && (
          <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-500/30">
            from Day {fromDay}
          </Badge>
        )}
        <Button variant="outline" size="sm" className="h-7 text-xs" onClick={onCopy}>
          <Copy className="mr-1.5 h-3 w-3" />
          Copy prompt for Claude
        </Button>
      </div>
    </div>
  );
}
