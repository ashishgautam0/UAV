-- New tracker records get an immediate, one-time "Email company HR" todo.
-- Existing records are treated as already handled to avoid creating a backlog.
do $$
begin
    if not exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'applications'
          and column_name = 'hr_email_sent_at'
    ) then
        alter table public.applications
            add column hr_email_sent_at timestamptz;

        update public.applications
        set hr_email_sent_at = coalesce(created_at, now())
        where hr_email_sent_at is null;
    end if;
end
$$;

create index if not exists idx_applications_hr_email_todo
    on public.applications (created_at)
    where hr_email_sent_at is null;