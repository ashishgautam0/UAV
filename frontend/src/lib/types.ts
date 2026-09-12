// ---- Applications ----
export interface Application {
  id: number;
  company: string;
  role: string;
  type: string;
  platform: string;
  url: string;
  noc_compatible: string;
  conversion: string;
  salary: string;
  notes: string;
  status: string;
  date_applied?: string;
  follow_up_date?: string;
  follow_up_count?: number;
}

export interface AddApplicationRequest {
  company: string;
  role: string;
  job_type?: string;
  platform?: string;
  url?: string;
  noc_compatible?: string;
  conversion?: string;
  salary?: string;
  notes?: string;
}

// ---- Dashboard / Stats ----
export interface DashboardStats {
  total: number;
  applied: number;
  interview: number;
  offer: number;
  rejected: number;
  this_week: number;
  [key: string]: number;
}

export interface FollowUp {
  id: number;
  company: string;
  role: string;
  follow_up_date: string;
  status: string;
  platform?: string;
  follow_up_count?: number;
}

export interface FollowUpDraft {
  entity_id: number;
  status: "pending" | "ready" | null;
  content: string | null;
  request_id?: number;
  follow_up_number?: number;
}

export interface FollowUpHistory {
  id: number;
  entity_type: "application";
  entity_id: number;
  message_content: string;
  channel: string;
  follow_up_number: number;
  follow_up_outcome: "pending" | "responded" | "no_response";
  sent_at: string;
}

export interface FollowUpEffectiveness {
  by_channel: { channel: string; total: number; responded: number; rate: number }[];
  by_number: { follow_up_number: number; total: number; responded: number; rate: number }[];
  overall: { total: number; responded: number; rate: number };
}

export interface LogFollowUpRequest {
  entity_type: string;
  entity_id: number;
  message_content?: string;
  channel?: string;
}

export interface WeeklyTrend {
  week: string;
  Job?: number;
  Internship?: number;
  total: number;
  [key: string]: string | number | undefined;
}

export interface PlatformEffectiveness {
  platform: string;
  applications: number;
  responses: number;
  response_rate: number;
}

export interface StatusFunnel {
  [status: string]: number;
}

export interface RoleAnalysis {
  role_keyword: string;
  applied: number;
  responses: number;
  response_rate: number;
}

// ---- Scraped Jobs ----
export interface ScrapedJob {
  id?: number;
  title: string;
  company: string;
  location: string;
  source: string;
  url: string;
  description: string;
  score: number;
  work_mode?: string;
  llm_reason?: string;
  verdict?: string;
  ats_score?: number;
  skill_match?: number;
  noc_verdict?: string;
  applied?: number;
  bestscore?: number;
  bestscore_breakdown?: {
    fit: number;
    fit_source: string;
    freshness: number;
    ease: number;
    aws?: number;
    score: number;
  };
}

export interface JobMessage {
  job_id: number;
  message_type: string;
  content: string | null;
  generated_by?: string;
  generated_at?: string;
}

// ---- Company Research ----
export interface CompanyIntel {
  description?: string;
  recent_news?: string;
  tech_signals?: string[];
  hiring_contact?: {
    name?: string;
    title?: string;
    linkedin?: string;
  };
  product_url?: string;
  [key: string]: unknown;
}

export interface CachedCompanyIntel {
  found: boolean;
  company_name?: string;
  description?: string;
  recent_news?: string;
  tech_signals?: string[] | string;
  product_url?: string;
  hiring_contact_name?: string;
  hiring_contact_title?: string;
  hiring_contact_linkedin?: string;
  researched_at?: string;
}

export type EmailStatus =
  | "valid"
  | "catch_all"
  | "invalid"
  | "pattern"
  | "no_mx";

export interface EmailCandidate {
  email: string;
  status: EmailStatus;
}

export interface RecruiterContact {
  name: string;
  candidates: EmailCandidate[];
}

export interface RecruiterEmailReport {
  ok: boolean;
  reason?: string;
  message?: string;
  domain?: string;
  mx_ok?: boolean;
  smtp_checked?: boolean;
  catch_all?: boolean | null;
  email_pattern?: string | null;
  contacts?: RecruiterContact[];
}

// ---- Profile ----
export interface ProjectEntry {
  name: string;
  description: string;
  keywords: string[];
}

export interface ExperienceEntry {
  role: string;
  company: string;
  period: string;
  description: string;
}

export interface UserProfile {
  id?: number;
  username: string;
  full_name: string;
  bio: string;
  skills: string[];
  projects: ProjectEntry[];
  experience: ExperienceEntry[];
  education: string;
  location_preference: string;
  target_roles: string[];
  resume_text: string;
  scoring_weights: Record<string, unknown>;
  updated_at?: string;
}

export interface UserProfileUpdate {
  full_name?: string;
  bio?: string;
  skills?: string[];
  projects?: ProjectEntry[];
  experience?: ExperienceEntry[];
  education?: string;
  location_preference?: string;
  target_roles?: string[];
  resume_text?: string;
  scoring_weights?: Record<string, unknown>;
}

// ---- Notifications ----
export interface AppNotification {
  id: number;
  title: string;
  body: string;
  type: string;
  metadata: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

// ---- 28-Day Prep ----
export interface Prep28State {
  start?: string | null;
  dayOverride?: number | null;
  sess?: string | null;
  done?: Record<string, boolean>;
}
