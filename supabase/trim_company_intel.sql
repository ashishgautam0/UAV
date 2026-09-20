-- Retain official company websites and verified hiring contacts only.
-- Existing descriptions, news, and technology signals are intentionally removed.
alter table public.company_research_cache
    drop column if exists description,
    drop column if exists recent_news,
    drop column if exists tech_signals;