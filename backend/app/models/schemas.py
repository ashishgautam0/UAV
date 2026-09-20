from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date


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
    model_config = ConfigDict(extra="forbid")
    full_name: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[list[str]] = None
    projects: Optional[list[ProjectEntry]] = None
    experience: Optional[list[ExperienceEntry]] = None
    education: Optional[str] = None
    location_preference: Optional[str] = None
    target_roles: Optional[list[str]] = None
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


class ApplicationPromptSettings(BaseModel):
    """User-supplied application answers stored with the backend profile."""
    model_config = ConfigDict(extra="forbid")
    submission_authorization: str = Field(default="", max_length=500)
    notice_period: str = Field(default="", max_length=500)
    current_ctc: str = Field(default="", max_length=500)
    expected_ctc: str = Field(default="", max_length=500)
    expected_start_date: str = Field(default="", max_length=500)
    current_location: str = Field(default="", max_length=500)
    relocation_preference: str = Field(default="", max_length=500)


class ReviewedExperienceEntry(BaseModel):
    id: str = ""
    label: str = ""
    role: str = ""
    company: str = ""
    start: str = ""
    end: str = ""


class ReviewedEducationEntry(BaseModel):
    id: str = ""
    level: str
    credential: str
    field: str = ""
    institution: str = ""


class ResumeProfileReviewRequest(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience: list[ReviewedExperienceEntry] = Field(default_factory=list)
    education: list[ReviewedEducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    review_notes: str = ""


class ResumeProfileResponse(BaseModel):
    backend_text: str = ""
    id: int
    username: str
    version: int
    source_kind: str
    source_filename: str
    source_sha256: str
    extraction_method: str
    facts: dict = Field(default_factory=dict)
    extracted_facts: dict = Field(default_factory=dict)
    evidence: dict = Field(default_factory=dict)
    readability: dict = Field(default_factory=dict)
    status: str
    created_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    activated_at: Optional[str] = None


class ResumeProfileStatusResponse(BaseModel):
    active: Optional[ResumeProfileResponse] = None
    latest: Optional[ResumeProfileResponse] = None


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
    new_date: date


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
    # Missed coding problems on the spaced-repetition ladder, keyed by task id.
    review: dict = {}
    # Plan version the progress was recorded against; the frontend resets
    # progress when it no longer matches the plan it is rendering.
    v: Optional[int] = None


class Prep28Response(BaseModel):
    start: Optional[str] = None
    dayOverride: Optional[int] = None
    sess: Optional[str] = None
    done: dict = {}
    review: dict = {}
    v: Optional[int] = None
