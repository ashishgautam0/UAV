-- =============================================================================
-- Job Search HQ — Supabase (PostgreSQL) schema
--
-- Apply once to a new Supabase project:
--   Dashboard -> SQL Editor -> New query -> paste this file -> Run
--
-- Every table, column, default and index below is derived from the code that
-- reads or writes it (backend/modules/tracker.py, profile.py, hourly.py and
-- the routers under backend/app/routers/). Column names must match exactly —
-- the backend talks to PostgREST, which fails on unknown columns.
--
-- ACCESS MODEL
-- The Next.js frontend never talks to Supabase directly; it calls the FastAPI
-- backend, which holds the only Supabase credential. So RLS is enabled on every
-- table with NO policies: anon and authenticated get nothing, and only the
-- service_role key (which bypasses RLS) can read or write. Set SUPABASE_KEY to
-- the service_role key on the backend, and never expose it to the browser.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- applications — manually tracked job applications
-- ---------------------------------------------------------------------------
create table if not exists applications (
    id                    bigserial primary key,
    company               text        not null,
    role                  text        not null,
    type                  text        not null default 'Job',      -- 'Job' | 'Internship'
    platform              text        not null default '',
    url                   text        not null default '',
    date_applied          date        not null default current_date,
    follow_up_date        date,                                    -- null once terminal
    follow_up_count       integer     not null default 0,
    status                text        not null default 'Applied',
    noc_compatible        text        not null default 'Unknown',
    conversion_potential  text        not null default 'N/A',
    salary_range          text        not null default '',
    notes                 text        not null default '',
    created_at            timestamptz not null default now()
);

create index if not exists idx_applications_status         on applications (status);
create index if not exists idx_applications_follow_up_date on applications (follow_up_date);
create index if not exists idx_applications_date_applied   on applications (date_applied desc);


-- ---------------------------------------------------------------------------
-- scraped_jobs — LinkedIn scraper output
-- url is UNIQUE because save_scraped_job() upserts on_conflict="url".
-- ---------------------------------------------------------------------------
create table if not exists scraped_jobs (
    id           bigserial primary key,
    title        text        not null,
    company      text        not null default 'Unknown',
    location     text        not null default '',
    source       text        not null default '',
    url          text        not null unique,
    description  text        not null default '',
    score        integer     not null default 0,
    verdict      text        not null default '',
    ats_score    integer     not null default 0,
    skill_match  integer     not null default 0,
    noc_verdict  text        not null default '',
    work_mode    text,   -- rendered by the Tonight page; no writer yet
    llm_reason   text,   -- rendered by the Tonight page; no writer yet
    dismissed    smallint    not null default 0,   -- 0/1, not boolean: code filters .eq("dismissed", 0)
    applied      smallint    not null default 0,   -- 0/1, set by mark_scraped_job()
    scraped_at   timestamptz not null default now()
);

create index if not exists idx_scraped_jobs_inbox      on scraped_jobs (dismissed, applied);
create index if not exists idx_scraped_jobs_scraped_at on scraped_jobs (scraped_at desc);
create index if not exists idx_scraped_jobs_source     on scraped_jobs (source);


-- ---------------------------------------------------------------------------
-- referrals — warm contacts and their follow-up cadence
-- ---------------------------------------------------------------------------
create table if not exists referrals (
    id               bigserial primary key,
    contact_name     text        not null,
    company          text        not null,
    contact_role     text        not null default '',
    relationship     text        not null default '',
    linkedin_url     text        not null default '',
    email            text        not null default '',
    status           text        not null default 'Identified',
    last_contacted   date,
    follow_up_date   date,
    follow_up_count  integer     not null default 0,
    notes            text        not null default '',
    created_at       timestamptz not null default now()
);

create index if not exists idx_referrals_status         on referrals (status);
create index if not exists idx_referrals_follow_up_date on referrals (follow_up_date);
create index if not exists idx_referrals_company        on referrals (company);


-- ---------------------------------------------------------------------------
-- follow_up_history — one row per follow-up message sent
-- entity_type is 'application' or 'referral'; entity_id points at that table.
-- Deliberately not a foreign key: one history table serves two parents.
-- ---------------------------------------------------------------------------
create table if not exists follow_up_history (
    id                 bigserial primary key,
    entity_type        text        not null,
    entity_id          bigint      not null,
    message_content    text        not null default '',
    channel            text        not null default '',
    follow_up_number   integer     not null default 1,
    follow_up_outcome  text        not null default 'pending',  -- pending | responded | no_response
    sent_at            timestamptz not null default now()
);

create index if not exists idx_follow_up_history_entity  on follow_up_history (entity_type, entity_id);
create index if not exists idx_follow_up_history_outcome on follow_up_history (follow_up_outcome);


-- ---------------------------------------------------------------------------
-- company_research_cache — 14-day cache of per-company research
-- ---------------------------------------------------------------------------
create table if not exists company_research_cache (
    id                       bigserial primary key,
    company_name             text        not null unique,
    description              text        not null default '',
    recent_news              text        not null default '',
    tech_signals             jsonb       not null default '[]'::jsonb,
    hiring_contact_name      text        not null default '',
    hiring_contact_title     text        not null default '',
    hiring_contact_linkedin  text        not null default '',
    product_url              text        not null default '',
    researched_at            timestamptz not null default now()
);

-- save_research_cache() never sets researched_at, so an upsert that UPDATEs an
-- existing row would leave the original timestamp in place. Once that row aged
-- past the 14-day staleness check in get_cached_research(), it would be treated
-- as stale forever and the cache would stop working. This trigger re-stamps it.
create or replace function touch_researched_at()
returns trigger
language plpgsql
as $$
begin
    new.researched_at = now();
    return new;
end;
$$;

drop trigger if exists trg_company_research_cache_touch on company_research_cache;
create trigger trg_company_research_cache_touch
    before update on company_research_cache
    for each row execute function touch_researched_at();


-- ---------------------------------------------------------------------------
-- mini_demos — small build-for-a-company projects
-- ---------------------------------------------------------------------------
create table if not exists mini_demos (
    id           bigserial primary key,
    company      text        not null,
    role         text        not null default '',
    demo_idea    text        not null default '',
    status       text        not null default 'Idea',   -- Idea | Building | Deployed | ...
    github_url   text        not null default '',
    demo_url     text        not null default '',
    hours_spent  numeric     not null default 0,
    result       text        not null default '',
    created_at   timestamptz not null default now()
);

create index if not exists idx_mini_demos_status     on mini_demos (status);
create index if not exists idx_mini_demos_created_at on mini_demos (created_at desc);


-- ---------------------------------------------------------------------------
-- email_logs — rendered job-alert emails, for replay in the UI
-- ---------------------------------------------------------------------------
create table if not exists email_logs (
    id                bigserial primary key,
    subject           text        not null,
    markdown_content  text        not null default '',
    html_content      text        not null default '',
    jobs_count        integer     not null default 0,
    sources_summary   jsonb       not null default '{}'::jsonb,
    email_sent        boolean     not null default false,
    created_at        timestamptz not null default now()
);

create index if not exists idx_email_logs_created_at on email_logs (created_at desc);


-- ---------------------------------------------------------------------------
-- notifications — in-app notification feed
-- Mirrors the CREATE TABLE that init_notifications_table() tries to run via an
-- exec_sql RPC. That RPC does not exist in a stock Supabase project, so the
-- call fails harmlessly and prints a note; applying this file is what actually
-- creates the table. Do NOT add an exec_sql RPC — it would expose arbitrary SQL.
-- ---------------------------------------------------------------------------
create table if not exists notifications (
    id          bigserial primary key,
    title       text        not null,
    body        text        not null,
    type        text        not null default 'job_alert',
    metadata    jsonb       not null default '{}'::jsonb,
    is_read     boolean     not null default false,
    created_at  timestamptz not null default now()
);

create index if not exists idx_notifications_is_read    on notifications (is_read);
create index if not exists idx_notifications_created_at on notifications (created_at desc);


-- ---------------------------------------------------------------------------
-- push_subscriptions — Web Push endpoints, upserted on_conflict="endpoint"
-- ---------------------------------------------------------------------------
create table if not exists push_subscriptions (
    id          bigserial primary key,
    endpoint    text        not null unique,
    keys_p256dh text        not null,
    keys_auth   text        not null,
    created_at  timestamptz not null default now()
);


-- ---------------------------------------------------------------------------
-- user_profile — single-user profile, upserted on_conflict="username"
-- The jsonb columns are written as real lists/dicts by upsert_profile(), so
-- they round-trip correctly and are queryable.
-- ---------------------------------------------------------------------------
create table if not exists user_profile (
    id                   bigserial primary key,
    username             text        not null unique,
    full_name            text        not null default '',
    bio                  text        not null default '',
    skills               jsonb       not null default '[]'::jsonb,
    projects             jsonb       not null default '[]'::jsonb,
    experience           jsonb       not null default '[]'::jsonb,
    education            text        not null default '',
    location_preference  text        not null default '',
    target_roles         jsonb       not null default '[]'::jsonb,
    resume_text          text        not null default '',
    blocked_companies    jsonb       not null default '[]'::jsonb,
    scoring_weights      jsonb       not null default '{}'::jsonb,
    updated_at           timestamptz not null default now()
);


-- ---------------------------------------------------------------------------
-- Row Level Security
-- Enabled with no policies: anon and authenticated are denied everything, and
-- only the service_role key reaches the data. See ACCESS MODEL at the top.
-- ---------------------------------------------------------------------------
alter table applications           enable row level security;
alter table scraped_jobs           enable row level security;
alter table referrals              enable row level security;
alter table follow_up_history      enable row level security;
alter table company_research_cache enable row level security;
alter table mini_demos             enable row level security;
alter table email_logs             enable row level security;
alter table notifications          enable row level security;
alter table push_subscriptions     enable row level security;
alter table user_profile           enable row level security;
