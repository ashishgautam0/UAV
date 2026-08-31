import type {
  AddApplicationRequest,
  AddReferralRequest,
  AnalysisResult,
  Application,
  ATSCheckRequest,
  ATSResult,
  CachedCompanyIntel,
  ColdDMRequest,
  CoverLetterRequest,
  DashboardStats,
  DemoOutreachRequest,
  FollowUp,
  FollowUpDraft,
  FollowUpEffectiveness,
  FollowUpHistory,
  FollowUpRequest,
  FullAnalyzeRequest,
  JobMessage,
  LogFollowUpRequest,
  MessageRequest,
  MessageResponse,
  PlatformEffectiveness,
  Referral,
  ReferralRequestBody,
  ReferralStats,
  RoleAnalysis,
  ScrapedJob,
  StatusFunnel,
  ThankYouRequest,
  UserProfile,
  UserProfileUpdate,
  WeeklyTrend,
  AppNotification,
  UnreadCountResponse,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Request failed: ${res.status}`);
  }

  return res.json();
}

// ---- Applications ----
export async function getApplications(filters?: {
  status?: string;
  type?: string;
  platform?: string;
}): Promise<Application[]> {
  const params = new URLSearchParams();
  if (filters?.status) params.set("status", filters.status);
  if (filters?.type) params.set("type", filters.type);
  if (filters?.platform) params.set("platform", filters.platform);
  const qs = params.toString();
  return apiFetch<Application[]>(`/api/applications${qs ? `?${qs}` : ""}`);
}

export async function createApplication(data: AddApplicationRequest) {
  return apiFetch<{ success: boolean }>("/api/applications", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateApplicationStatus(id: number, status: string) {
  return apiFetch<{ success: boolean }>(`/api/applications/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function updateApplicationNotes(id: number, notes: string) {
  return apiFetch<{ success: boolean }>(`/api/applications/${id}/notes`, {
    method: "PATCH",
    body: JSON.stringify({ notes }),
  });
}

export async function deleteApplication(id: number) {
  return apiFetch<{ success: boolean }>(`/api/applications/${id}`, {
    method: "DELETE",
  });
}

export async function snoozeFollowUp(id: number, newDate: string) {
  return apiFetch<{ success: boolean }>(`/api/applications/${id}/snooze`, {
    method: "PATCH",
    body: JSON.stringify({ new_date: newDate }),
  });
}

// ---- Stats ----
export async function getDashboard(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/api/stats/dashboard");
}

export async function getFollowUps(): Promise<FollowUp[]> {
  return apiFetch<FollowUp[]>("/api/stats/follow-ups");
}

export async function getWeeklyTrend(): Promise<WeeklyTrend[]> {
  return apiFetch<WeeklyTrend[]>("/api/stats/weekly-trend");
}

export async function getPlatformEffectiveness(): Promise<PlatformEffectiveness[]> {
  return apiFetch<PlatformEffectiveness[]>("/api/stats/platform-effectiveness");
}

export async function getStatusFunnel(): Promise<StatusFunnel> {
  return apiFetch<StatusFunnel>("/api/stats/status-funnel");
}

export async function getRoleAnalysis(): Promise<RoleAnalysis[]> {
  return apiFetch<RoleAnalysis[]>("/api/stats/role-analysis");
}

// ---- Scraper ----
export async function getRankedScrapedJobs(
  limit = 200
): Promise<ScrapedJob[]> {
  return apiFetch<ScrapedJob[]>(`/api/scraped-jobs/ranked?limit=${limit}`);
}

export async function markScrapedJob(id: number, action: string) {
  return apiFetch<{ success: boolean }>(`/api/scraped-jobs/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ action }),
  });
}

export async function getCachedCompanyIntel(
  name: string
): Promise<CachedCompanyIntel> {
  return apiFetch<CachedCompanyIntel>(
    `/api/company-research/cached?name=${encodeURIComponent(name)}`
  );
}

export async function findRecruiterEmails(
  company: string,
  names = "",
  domain = ""
): Promise<import("./types").RecruiterEmailReport> {
  const q = new URLSearchParams({ company });
  if (names) q.set("names", names);
  if (domain) q.set("domain", domain);
  return apiFetch(`/api/company-research/recruiter-emails?${q.toString()}`);
}

export async function getScrapedJob(id: number): Promise<ScrapedJob> {
  return apiFetch<ScrapedJob>(`/api/scraped-jobs/${id}`);
}

export async function lookupScrapedJob(url: string): Promise<{ id: number | null }> {
  return apiFetch<{ id: number | null }>(
    `/api/scraped-jobs/lookup?url=${encodeURIComponent(url)}`
  );
}

export async function getFollowUpDraft(entityId: number): Promise<FollowUpDraft> {
  return apiFetch<FollowUpDraft>(`/api/follow-ups/draft?entity_id=${entityId}`);
}

export async function getJobMessage(
  id: number,
  type: string = "cold_dm"
): Promise<JobMessage> {
  return apiFetch<JobMessage>(
    `/api/scraped-jobs/${id}/message?type=${encodeURIComponent(type)}`
  );
}

// ---- Messages ----
export async function generateColdDM(data: ColdDMRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/cold-dm", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateFollowUp(data: FollowUpRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/follow-up", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateCoverLetter(data: CoverLetterRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/cover-letter", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateThankYou(data: ThankYouRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/thank-you", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateReferralRequest(data: ReferralRequestBody): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/referral-request", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function generateDemoOutreach(data: DemoOutreachRequest): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/messages/demo-outreach", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getMessageRequest(id: number): Promise<MessageRequest> {
  return apiFetch<MessageRequest>(`/api/messages/requests/${id}`);
}

// ---- JD Analyzer ----
export async function analyzeFullJD(data: FullAnalyzeRequest): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>("/api/analyze/full", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function checkATS(data: ATSCheckRequest): Promise<ATSResult> {
  return apiFetch<ATSResult>("/api/analyze/ats", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ---- Referrals ----
export async function getReferrals(company?: string): Promise<Referral[]> {
  const qs = company ? `?company=${encodeURIComponent(company)}` : "";
  return apiFetch<Referral[]>(`/api/referrals${qs}`);
}

export async function createReferral(data: AddReferralRequest) {
  return apiFetch<{ success: boolean }>("/api/referrals", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateReferralStatus(id: number, status: string) {
  return apiFetch<{ success: boolean }>(`/api/referrals/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function getReferralStats(): Promise<ReferralStats> {
  return apiFetch<ReferralStats>("/api/referrals/stats");
}

export async function getReferralFollowUps(): Promise<Referral[]> {
  return apiFetch<Referral[]>("/api/referrals/follow-ups");
}

// ---- Follow-up History ----
export async function logFollowUp(data: LogFollowUpRequest) {
  return apiFetch<{ success: boolean; follow_up_number: number }>("/api/follow-ups/log", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getFollowUpHistory(
  entityType: string,
  entityId: number,
): Promise<FollowUpHistory[]> {
  return apiFetch<FollowUpHistory[]>(
    `/api/follow-ups/history?entity_type=${entityType}&entity_id=${entityId}`,
  );
}

export async function updateFollowUpOutcome(historyId: number, outcome: string) {
  return apiFetch<{ success: boolean }>(`/api/follow-ups/${historyId}/outcome`, {
    method: "PATCH",
    body: JSON.stringify({ outcome }),
  });
}

export async function getFollowUpEffectiveness(): Promise<FollowUpEffectiveness> {
  return apiFetch<FollowUpEffectiveness>("/api/follow-ups/effectiveness");
}

// ---- Profile ----
export async function getProfile(): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/profile/");
}

export async function updateProfile(data: UserProfileUpdate): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/profile/", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

// ---- Notifications ----
export async function getNotifications(unreadOnly = false): Promise<AppNotification[]> {
  const qs = unreadOnly ? "?unread_only=true" : "";
  return apiFetch<AppNotification[]>(`/api/notifications${qs}`);
}

export async function getUnreadCount(): Promise<UnreadCountResponse> {
  return apiFetch<UnreadCountResponse>("/api/notifications/unread-count");
}

export async function markNotificationRead(id: number) {
  return apiFetch<{ success: boolean }>(`/api/notifications/${id}/read`, {
    method: "PATCH",
  });
}

export async function markAllNotificationsRead() {
  return apiFetch<{ success: boolean }>("/api/notifications/mark-all-read", {
    method: "POST",
  });
}

export async function getVapidPublicKey(): Promise<{ public_key: string }> {
  return apiFetch<{ public_key: string }>("/api/vapid-public-key");
}

export async function subscribePush(subscription: PushSubscriptionJSON) {
  return apiFetch<{ success: boolean }>("/api/notifications/push/subscribe", {
    method: "POST",
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      keys: subscription.keys,
    }),
  });
}

export async function unsubscribePush(subscription: PushSubscriptionJSON) {
  return apiFetch<{ success: boolean }>("/api/notifications/push/unsubscribe", {
    method: "POST",
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      keys: subscription.keys,
    }),
  });
}
