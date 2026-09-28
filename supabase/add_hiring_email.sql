-- Cache the hiring address the company-research agent finds, so the HR email
-- agent reuses one search per employer instead of repeating it per posting.
-- Safe to run more than once.
alter table public.company_research_cache
    add column if not exists hiring_email        text not null default '',
    add column if not exists hiring_email_source text not null default '';

-- Existing rows keep their researched_at: adding a column is not a re-research,
-- and re-stamping them would hide how old the cached website and contact are.
