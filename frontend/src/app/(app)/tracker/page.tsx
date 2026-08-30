"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  getApplications,
  createApplication,
  updateApplicationStatus,
  updateApplicationNotes,
  deleteApplication,
  getFollowUpDraft,
  getFollowUpHistory,
  getJobMessage,
  lookupScrapedJob,
  updateFollowUpOutcome,
} from "@/lib/api";
import type { Application, FollowUpDraft, FollowUpHistory } from "@/lib/types";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";
import {
  ClipboardList,
  MessageSquareText,
  Plus,
  ChevronDown,
  Trash2,
  Loader2,
  ExternalLink,
  Pencil,
  MessageSquare,
  Mail,
  Check,
  X as XIcon,
  History,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PLATFORMS = [
  "LinkedIn",
  "Wellfound",
  "YC WaaS",
  "Internshala",
  "Instahyre",
  "Naukri",
  "Indeed",
  "HasJob",
  "Direct",
  "Referral",
  "Other",
] as const;

const STATUSES = [
  "Applied",
  "Follow-up Sent",
  "Assignment Submitted",
  "Interview",
  "Offer",
  "Rejected",
  "Ghosted",
  "Not Interested",
] as const;

const STATUS_COLORS: Record<string, string> = {
  Applied: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  "Follow-up Sent": "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  "Assignment Submitted": "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  Interview: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  Offer: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  Rejected: "bg-red-500/15 text-red-400 border-red-500/30",
  Ghosted: "bg-gray-500/15 text-gray-400 border-gray-500/30",
  "Not Interested": "bg-orange-500/15 text-orange-400 border-orange-500/30",
};


// ---------------------------------------------------------------------------
// Helper: status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(STATUS_COLORS[status] || "border-border")}
    >
      {status}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function TrackerPage() {
  const router = useRouter();

  // ---- Applications state ----
  const [applications, setApplications] = useState<Application[]>([]);
  const [appPage, setAppPage] = useState(1);
  const APPS_PER_PAGE = 10;
  const [appsLoading, setAppsLoading] = useState(true);

  // ---- Add application form ----
  const [addOpen, setAddOpen] = useState(false);
  const [addForm, setAddForm] = useState({
    company: "",
    role: "",
    job_type: "Job",
    platform: "LinkedIn",
    url: "",
    conversion: "N/A",
    salary: "",
    notes: "",
  });
  const [addLoading, setAddLoading] = useState(false);

  // ---- Filters ----
  const [filterStatus, setFilterStatus] = useState("All");
  const [filterType, setFilterType] = useState("All");
  const [filterPlatform, setFilterPlatform] = useState("All");

  // ---- Application status update ----
  const [statusUpdates, setStatusUpdates] = useState<Record<number, string>>(
    {}
  );
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [fuDrafts, setFuDrafts] = useState<Record<number, FollowUpDraft>>({});
  const [fuDraftOpen, setFuDraftOpen] = useState<Set<number>>(new Set());
  const [fuDraftLoading, setFuDraftLoading] = useState<number | null>(null);
  const [dmByApp, setDmByApp] = useState<Record<number, string | null>>({});
  const [dmOpen, setDmOpen] = useState<Set<number>>(new Set());
  const [dmLoading, setDmLoading] = useState<number | null>(null);

  const toggleColdDm = async (app: Application) => {
    const id = app.id;
    if (dmOpen.has(id)) {
      setDmOpen((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      return;
    }
    if (!(id in dmByApp)) {
      if (!app.url) {
        toast.info("No job posting URL saved for this application.");
        return;
      }
      setDmLoading(id);
      try {
        const { id: jobId } = await lookupScrapedJob(app.url);
        const content = jobId
          ? (await getJobMessage(jobId)).content
          : null;
        setDmByApp((prev) => ({ ...prev, [id]: content }));
        if (!content) {
          toast.info("No cold DM stored for this application's job.");
          return;
        }
      } catch {
        toast.error("Failed to load the cold DM");
        return;
      } finally {
        setDmLoading(null);
      }
    } else if (!dmByApp[id]) {
      toast.info("No cold DM stored for this application's job.");
      return;
    }
    setDmOpen((prev) => new Set(prev).add(id));
  };

  const openJobPage = async (app: Application) => {
    if (!app.url) {
      toast.info("No job posting URL saved for this application.");
      return;
    }
    try {
      const { id } = await lookupScrapedJob(app.url);
      if (id) {
        router.push(`/jobs/${id}`);
      } else {
        toast.info(
          "No job page for this application — it wasn't scraped, or was deleted."
        );
      }
    } catch {
      toast.error("Failed to look up the job page");
    }
  };

  const toggleFuDraft = async (appId: number) => {
    if (fuDraftOpen.has(appId)) {
      setFuDraftOpen((prev) => {
        const next = new Set(prev);
        next.delete(appId);
        return next;
      });
      return;
    }
    let draft = fuDrafts[appId];
    if (!draft) {
      setFuDraftLoading(appId);
      try {
        draft = await getFollowUpDraft(appId);
        setFuDrafts((prev) => ({ ...prev, [appId]: draft }));
      } catch {
        toast.error("Failed to load the follow-up draft");
        return;
      } finally {
        setFuDraftLoading(null);
      }
    }
    if (draft.status === "ready" && draft.content) {
      setFuDraftOpen((prev) => new Set(prev).add(appId));
    } else if (draft.status === "pending") {
      toast.info("Queued — the next hourly run writes this follow-up.");
    } else {
      toast.info(
        "No draft yet — the hourly run queues one once the follow-up date arrives."
      );
    }
  };

  // ---- Delete dialog ----
  const [deleteTarget, setDeleteTarget] = useState<Application | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // ---- Notes editing ----
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [noteText, setNoteText] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  // ---- Follow-up history ----
  const [historyAppId, setHistoryAppId] = useState<number | null>(null);
  const [historyRecords, setHistoryRecords] = useState<FollowUpHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  async function toggleHistory(appId: number) {
    if (historyAppId === appId) {
      setHistoryAppId(null);
      setHistoryRecords([]);
      return;
    }
    setHistoryAppId(appId);
    setHistoryLoading(true);
    try {
      const records = await getFollowUpHistory("application", appId);
      setHistoryRecords(records);
    } catch {
      toast.error("Failed to load follow-up history");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleOutcomeChange(historyId: number, outcome: string) {
    try {
      await updateFollowUpOutcome(historyId, outcome);
      setHistoryRecords((prev) =>
        prev.map((r) =>
          r.id === historyId ? { ...r, follow_up_outcome: outcome as FollowUpHistory["follow_up_outcome"] } : r
        )
      );
      toast.success("Outcome updated");
    } catch {
      toast.error("Failed to update outcome");
    }
  }

  // ---- Fetch helpers ----
  const fetchApplications = useCallback(async () => {
    setAppsLoading(true);
    try {
      const filters: { status?: string; type?: string; platform?: string } = {};
      if (filterStatus !== "All") filters.status = filterStatus;
      if (filterType !== "All") filters.type = filterType;
      if (filterPlatform !== "All") filters.platform = filterPlatform;
      const data = await getApplications(filters);
      setApplications(data);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to load applications"
      );
    } finally {
      setAppsLoading(false);
    }
  }, [filterStatus, filterType, filterPlatform]);

  // ---- Load on mount + filter change ----
  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  // Back to the first page whenever the filters change
  useEffect(() => {
    setAppPage(1);
  }, [filterStatus, filterType, filterPlatform]);

  const appTotalPages = Math.max(
    1,
    Math.ceil(applications.length / APPS_PER_PAGE)
  );
  const appSafePage = Math.min(appPage, appTotalPages);
  const pagedApplications = applications.slice(
    (appSafePage - 1) * APPS_PER_PAGE,
    appSafePage * APPS_PER_PAGE
  );

  // ---- Handlers: Applications ----
  async function handleAddApplication() {
    if (!addForm.company.trim() || !addForm.role.trim()) return;
    setAddLoading(true);
    try {
      await createApplication({
        company: addForm.company.trim(),
        role: addForm.role.trim(),
        job_type: addForm.job_type,
        platform: addForm.platform,
        url: addForm.url.trim() || undefined,
        conversion: addForm.conversion,
        salary: addForm.salary.trim() || undefined,
        notes: addForm.notes.trim() || undefined,
      });
      toast.success("Application logged successfully");
      setAddForm({
        company: "",
        role: "",
        job_type: "Job",
        platform: "LinkedIn",
        url: "",
        conversion: "N/A",
        salary: "",
        notes: "",
      });
      setAddOpen(false);
      await fetchApplications();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to add application"
      );
    } finally {
      setAddLoading(false);
    }
  }

  async function handleUpdateStatus(id: number) {
    const newStatus = statusUpdates[id];
    if (!newStatus) return;
    setUpdatingId(id);
    try {
      await updateApplicationStatus(id, newStatus);
      toast.success("Status updated");
      await fetchApplications();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to update status"
      );
    } finally {
      setUpdatingId(null);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteApplication(deleteTarget.id);
      toast.success("Application deleted");
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await fetchApplications();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to delete application"
      );
    } finally {
      setDeleting(false);
    }
  }

  // ---- Render ----
  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-3">
          <ClipboardList className="h-8 w-8" />
          Application Tracker
        </h1>
        <p className="text-muted-foreground mt-1">
          Track your job applications in one place.
        </p>
      </div>

      {/* ================================================================== */}
      {/* Toolbar: Add button + Filters (compact row)                       */}
      {/* ================================================================== */}
      <div className="flex flex-wrap items-end gap-3">
        {/* Add Application Dialog */}
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add Application
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Log New Application</DialogTitle>
              <DialogDescription>
                Fill in the details of your job application.
              </DialogDescription>
            </DialogHeader>
            <div className="grid grid-cols-1 gap-4 py-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="app-company">Company *</Label>
                <Input
                  id="app-company"
                  placeholder="e.g. Shopify"
                  value={addForm.company}
                  onChange={(e) =>
                    setAddForm((p) => ({ ...p, company: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="app-role">Role *</Label>
                <Input
                  id="app-role"
                  placeholder="e.g. Full-Stack Developer"
                  value={addForm.role}
                  onChange={(e) =>
                    setAddForm((p) => ({ ...p, role: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Type</Label>
                <Select
                  value={addForm.job_type}
                  onValueChange={(v) =>
                    setAddForm((p) => ({ ...p, job_type: v }))
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Job">Job</SelectItem>
                    <SelectItem value="Internship">Internship</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Platform</Label>
                <Select
                  value={addForm.platform}
                  onValueChange={(v) =>
                    setAddForm((p) => ({ ...p, platform: v }))
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PLATFORMS.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="app-url">URL</Label>
                <Input
                  id="app-url"
                  placeholder="https://..."
                  value={addForm.url}
                  onChange={(e) =>
                    setAddForm((p) => ({ ...p, url: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Conversion Potential</Label>
                <Select
                  value={addForm.conversion}
                  onValueChange={(v) =>
                    setAddForm((p) => ({ ...p, conversion: v }))
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="N/A">N/A</SelectItem>
                    <SelectItem value="Likely">Likely</SelectItem>
                    <SelectItem value="Unlikely">Unlikely</SelectItem>
                    <SelectItem value="Unknown">Unknown</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="app-salary">Salary</Label>
                <Input
                  id="app-salary"
                  placeholder="e.g. $80,000"
                  value={addForm.salary}
                  onChange={(e) =>
                    setAddForm((p) => ({ ...p, salary: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-2 col-span-2">
                <Label htmlFor="app-notes">Notes</Label>
                <Textarea
                  id="app-notes"
                  placeholder="Any additional notes..."
                  value={addForm.notes}
                  onChange={(e) =>
                    setAddForm((p) => ({ ...p, notes: e.target.value }))
                  }
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                onClick={handleAddApplication}
                disabled={
                  addLoading ||
                  !addForm.company.trim() ||
                  !addForm.role.trim()
                }
                className="w-full"
              >
                {addLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                {addLoading ? "Logging..." : "Log Application"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Compact Filters */}
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All Statuses</SelectItem>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-[130px]">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All Types</SelectItem>
            <SelectItem value="Job">Job</SelectItem>
            <SelectItem value="Internship">Internship</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filterPlatform} onValueChange={setFilterPlatform}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Platform" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All Platforms</SelectItem>
            {PLATFORMS.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <span className="text-muted-foreground text-sm ml-auto">
          {applications.length} application{applications.length !== 1 && "s"}
        </span>
      </div>

      {/* ================================================================== */}
      {/* Applications List                                                  */}
      {/* ================================================================== */}
      <div className="space-y-3">

        {appsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : applications.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No applications found. Add one above to get started.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {pagedApplications.map((app) => (
              <Card key={app.id}>
                <Collapsible>
                  <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors pb-3 pt-3">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                      {/* Inline status dropdown */}
                      <div onClick={(e) => e.stopPropagation()} onPointerDown={(e) => e.stopPropagation()}>
                        <Select
                          value={app.status}
                          onValueChange={async (v) => {
                            setUpdatingId(app.id);
                            try {
                              await updateApplicationStatus(app.id, v);
                              toast.success(`Status → ${v}`);
                              await fetchApplications();
                            } catch {
                              toast.error("Failed to update status");
                            } finally {
                              setUpdatingId(null);
                            }
                          }}
                        >
                          <SelectTrigger
                            className={cn(
                              "w-[130px] h-7 text-xs font-medium",
                              STATUS_COLORS[app.status] || "border-border"
                            )}
                          >
                            {updatingId === app.id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <SelectValue />
                            )}
                          </SelectTrigger>
                          <SelectContent>
                            {STATUSES.map((s) => (
                              <SelectItem key={s} value={s}>
                                {s}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div
                        className="order-first w-full min-w-0 cursor-pointer sm:order-none sm:w-auto sm:flex-1"
                        onClick={() => openJobPage(app)}
                      >
                          <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
                            <span className="font-bold truncate hover:underline">{app.company}</span>
                            <span className="text-muted-foreground text-sm sm:text-base truncate">
                              {app.role}
                            </span>
                            <span className="flex flex-wrap items-center gap-1.5 shrink-0">
                              <Badge variant="secondary">{app.platform}</Badge>
                              {(app.follow_up_count ?? 0) > 0 && (
                                <Badge variant="outline" className="text-xs bg-amber-500/10 text-amber-400 border-amber-500/30">
                                  {app.follow_up_count}/3 follow-ups
                                </Badge>
                              )}
                            </span>
                          </div>
                      </div>

                      {/* Quick action buttons */}
                      <TooltipProvider delayDuration={300}>
                        <div className="ml-auto flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()} onPointerDown={(e) => e.stopPropagation()}>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => {
                                  const params = new URLSearchParams({
                                    company: app.company,
                                    role: app.role,
                                    type: "follow-up",
                                  });
                                  router.push(`/messages?${params.toString()}`);
                                }}
                              >
                                <MessageSquare className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Follow-up</TooltipContent>
                          </Tooltip>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => {
                                  const params = new URLSearchParams({
                                    company: app.company,
                                    role: app.role,
                                    type: "cold-dm",
                                  });
                                  router.push(`/messages?${params.toString()}`);
                                }}
                              >
                                <Mail className="h-3.5 w-3.5" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Cold DM</TooltipContent>
                          </Tooltip>
                          <CollapsibleTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-7 w-7">
                              <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            </Button>
                          </CollapsibleTrigger>
                        </div>
                      </TooltipProvider>
                    </div>
                  </CardHeader>

                  <CollapsibleContent>
                    <CardContent className="pt-0 space-y-4">
                      <Separator />

                      {/* Details grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                        {app.date_applied && (
                          <div>
                            <p className="text-muted-foreground">
                              Date Applied
                            </p>
                            <p className="font-medium">{app.date_applied}</p>
                          </div>
                        )}
                        {app.follow_up_date && (
                          <div>
                            <p className="text-muted-foreground">
                              Follow-up Date
                            </p>
                            <p className="font-medium">{app.follow_up_date}</p>
                          </div>
                        )}
                        {app.url && (
                          <div>
                            <p className="text-muted-foreground">URL</p>
                            <a
                              href={app.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-blue-400 hover:underline"
                            >
                              View Listing
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        )}
                        <div>
                          <p className="text-muted-foreground">Conversion</p>
                          <p className="font-medium">{app.conversion}</p>
                        </div>
                        {app.salary && (
                          <div>
                            <p className="text-muted-foreground">Salary</p>
                            <p className="font-medium">{app.salary}</p>
                          </div>
                        )}
                      </div>

                      {/* Cold DM for this application's job */}
                      {app.url && (
                        <div className="space-y-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={dmLoading === app.id}
                            onClick={() => toggleColdDm(app)}
                          >
                            {dmLoading === app.id ? (
                              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <MessageSquareText className="mr-1.5 h-3.5 w-3.5" />
                            )}
                            {dmOpen.has(app.id) ? "Hide Cold DM" : "View Cold DM"}
                          </Button>
                          {dmOpen.has(app.id) && dmByApp[app.id] && (
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
                                    navigator.clipboard.writeText(dmByApp[app.id] || "");
                                    toast.success("DM copied to clipboard");
                                  }}
                                >
                                  Copy
                                </Button>
                              </div>
                              <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                                {dmByApp[app.id]}
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Auto-written follow-up draft */}
                      {app.follow_up_date && (
                        <div className="space-y-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={fuDraftLoading === app.id}
                            onClick={() => toggleFuDraft(app.id)}
                          >
                            {fuDraftLoading === app.id ? (
                              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <MessageSquare className="mr-1.5 h-3.5 w-3.5" />
                            )}
                            {fuDraftOpen.has(app.id)
                              ? "Hide Follow-up Draft"
                              : "View Follow-up Draft"}
                          </Button>
                          {fuDraftOpen.has(app.id) && fuDrafts[app.id]?.content && (
                            <div className="rounded-md border border-emerald-600/30 bg-emerald-600/5 p-3 space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-medium text-emerald-400">
                                  Follow-up #{fuDrafts[app.id]?.follow_up_number ?? 1}{" "}
                                  (auto-written)
                                </span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-2 text-xs"
                                  onClick={() => {
                                    navigator.clipboard.writeText(
                                      fuDrafts[app.id]?.content || ""
                                    );
                                    toast.success("Follow-up copied to clipboard");
                                  }}
                                >
                                  Copy
                                </Button>
                              </div>
                              <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                                {fuDrafts[app.id]?.content}
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Notes section */}
                      <div className="text-sm">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="text-muted-foreground">Notes</p>
                          {editingNoteId !== app.id && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => {
                                setEditingNoteId(app.id);
                                setNoteText(app.notes || "");
                              }}
                            >
                              <Pencil className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                        {editingNoteId === app.id ? (
                          <div className="space-y-2">
                            <Textarea
                              value={noteText}
                              onChange={(e) => setNoteText(e.target.value)}
                              placeholder="Add a note..."
                              className="min-h-[80px]"
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                disabled={savingNote}
                                onClick={async () => {
                                  setSavingNote(true);
                                  try {
                                    await updateApplicationNotes(app.id, noteText.trim());
                                    toast.success("Note saved");
                                    setEditingNoteId(null);
                                    await fetchApplications();
                                  } catch {
                                    toast.error("Failed to save note");
                                  } finally {
                                    setSavingNote(false);
                                  }
                                }}
                              >
                                {savingNote ? (
                                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                                ) : (
                                  <Check className="mr-1 h-3 w-3" />
                                )}
                                Save
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setEditingNoteId(null)}
                              >
                                <XIcon className="mr-1 h-3 w-3" />
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : app.notes ? (
                          <p className="font-medium whitespace-pre-wrap break-words">
                            {app.notes}
                          </p>
                        ) : (
                          <p className="text-muted-foreground/50 italic">No notes yet</p>
                        )}
                      </div>

                      {/* Follow-up History */}
                      <div className="text-sm">
                        <div className="flex items-center gap-2 mb-2">
                          <p className="text-muted-foreground">Follow-up History</p>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs"
                            onClick={() => toggleHistory(app.id)}
                          >
                            <History className="h-3 w-3 mr-1" />
                            {historyAppId === app.id ? "Hide" : "Show"}
                          </Button>
                        </div>
                        {historyAppId === app.id && (
                          <div className="space-y-2">
                            {historyLoading ? (
                              <div className="flex items-center gap-2 py-2">
                                <Loader2 className="h-3 w-3 animate-spin" />
                                <span className="text-muted-foreground text-xs">Loading...</span>
                              </div>
                            ) : historyRecords.length === 0 ? (
                              <p className="text-muted-foreground/50 italic text-xs">No follow-ups sent yet</p>
                            ) : (
                              <div className="rounded-md border">
                                <Table>
                                  <TableHeader>
                                    <TableRow>
                                      <TableHead className="text-xs h-8">#</TableHead>
                                      <TableHead className="text-xs h-8">Channel</TableHead>
                                      <TableHead className="text-xs h-8">Sent</TableHead>
                                      <TableHead className="text-xs h-8">Message</TableHead>
                                      <TableHead className="text-xs h-8">Outcome</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {historyRecords.map((rec) => (
                                      <TableRow key={rec.id}>
                                        <TableCell className="text-xs py-1.5">{rec.follow_up_number}</TableCell>
                                        <TableCell className="text-xs py-1.5">{rec.channel || "—"}</TableCell>
                                        <TableCell className="text-xs py-1.5">
                                          {new Date(rec.sent_at).toLocaleDateString()}
                                        </TableCell>
                                        <TableCell className="text-xs py-1.5 max-w-[200px] truncate" title={rec.message_content}>
                                          {rec.message_content ? rec.message_content.slice(0, 60) + (rec.message_content.length > 60 ? "..." : "") : "—"}
                                        </TableCell>
                                        <TableCell className="text-xs py-1.5">
                                          <Select
                                            value={rec.follow_up_outcome}
                                            onValueChange={(v) => handleOutcomeChange(rec.id, v)}
                                          >
                                            <SelectTrigger className="h-6 w-[110px] text-xs">
                                              <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                              <SelectItem value="pending">Pending</SelectItem>
                                              <SelectItem value="responded">Responded</SelectItem>
                                              <SelectItem value="no_response">No Response</SelectItem>
                                            </SelectContent>
                                          </Select>
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      <Separator />

                      {/* Actions row */}
                      <div className="flex items-center gap-3 flex-wrap">
                        <Dialog
                          open={
                            deleteDialogOpen &&
                            deleteTarget?.id === app.id
                          }
                          onOpenChange={(open) => {
                            setDeleteDialogOpen(open);
                            if (!open) setDeleteTarget(null);
                          }}
                        >
                          <DialogTrigger asChild>
                            <Button
                              size="sm"
                              variant="destructive"
                              className="ml-auto"
                              onClick={() => setDeleteTarget(app)}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Delete
                            </Button>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Confirm Deletion</DialogTitle>
                              <DialogDescription>
                                Are you sure you want to delete the application
                                for{" "}
                                <span className="font-semibold">
                                  {app.role}
                                </span>{" "}
                                at{" "}
                                <span className="font-semibold">
                                  {app.company}
                                </span>
                                ? This action cannot be undone.
                              </DialogDescription>
                            </DialogHeader>
                            <DialogFooter>
                              <Button
                                variant="outline"
                                onClick={() => {
                                  setDeleteDialogOpen(false);
                                  setDeleteTarget(null);
                                }}
                              >
                                Cancel
                              </Button>
                              <Button
                                variant="destructive"
                                onClick={handleDelete}
                                disabled={deleting}
                              >
                                {deleting ? (
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                  <Trash2 className="mr-2 h-4 w-4" />
                                )}
                                {deleting ? "Deleting..." : "Delete"}
                              </Button>
                            </DialogFooter>
                          </DialogContent>
                        </Dialog>
                      </div>
                    </CardContent>
                  </CollapsibleContent>
                </Collapsible>
              </Card>
            ))}

            {/* Pagination */}
            {appTotalPages > 1 && (
              <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={appSafePage <= 1}
                  onClick={() => setAppPage(appSafePage - 1)}
                >
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground tabular-nums">
                  Page {appSafePage} of {appTotalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={appSafePage >= appTotalPages}
                  onClick={() => setAppPage(appSafePage + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
