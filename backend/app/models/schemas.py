from pydantic import BaseModel
from typing import Optional


# ---- Profile ----

class ProjectEntry(BaseModel):
    name: str = ""
    description: str = ""
    keywords: list[str] = []


class ExperienceEntry(BaseModel):
    role: str = ""
    company: str = ""
    period: str = ""
    description: str = ""


class UserProfileRequest(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[list[str]] = None
    projects: Optional[list[ProjectEntry]] = None
    experience: Optional[list[ExperienceEntry]] = None
    education: Optional[str] = None
    location_preference: Optional[str] = None
    target_roles: Optional[list[str]] = None
    resume_text: Optional[str] = None
    scoring_weights: Optional[dict] = None


class UserProfileResponse(BaseModel):
    id: Optional[int] = None
    username: str = "subidh"
    full_name: str = ""
    bio: str = ""
    skills: list[str] = []
    projects: list[ProjectEntry] = []
    experience: list[ExperienceEntry] = []
    education: str = ""
    location_preference: str = ""
    target_roles: list[str] = []
    resume_text: str = ""
    scoring_weights: dict = {}
    updated_at: Optional[str] = None


# ---- Applications ----

class AddApplicationRequest(BaseModel):
    company: str
    role: str
    job_type: str = "Job"
    platform: str = ""
    url: str = ""
    noc_compatible: str = "Unknown"
    conversion: str = "N/A"
    salary: str = ""
    notes: str = ""


class UpdateStatusRequest(BaseModel):
    status: str


class UpdateNotesRequest(BaseModel):
    notes: str


class SnoozeRequest(BaseModel):
    new_date: str


# ---- Scraped Jobs ----

class MarkScrapedJobRequest(BaseModel):
    action: str  # "applied" or "dismissed"


# ---- Company Research ----

class CompanyResearchRequest(BaseModel):
    company_name: str


# ---- Follow-up History ----

class LogFollowUpRequest(BaseModel):
    entity_type: str   # "application"
    entity_id: int
    message_content: str = ""
    channel: str = ""


class UpdateFollowUpOutcomeRequest(BaseModel):
    outcome: str       # "pending", "responded", "no_response"


# ---- Mini Demos ----

class AddDemoRequest(BaseModel):
    company: str
    role: str
    demo_idea: str


class UpdateDemoRequest(BaseModel):
    status: Optional[str] = None
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    hours_spent: Optional[float] = None
    result: Optional[str] = None


# ---- Push Subscriptions ----

class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict


# ---- 28-Day Prep ----

class Prep28Request(BaseModel):
    """The mutable prep28 state. Freeform to match the frontend blob."""
    start: Optional[str] = None
    dayOverride: Optional[int] = None
    sess: Optional[str] = None
    done: dict = {}


class Prep28Response(BaseModel):
    start: Optional[str] = None
    dayOverride: Optional[int] = None
    sess: Optional[str] = None
    done: dict = {}
