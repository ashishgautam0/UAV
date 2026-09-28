-- Retire the 28-day interview prep feature. Its API, page and data layer are
-- gone from the codebase; this drops the table they used.
--
-- Run this only when you no longer want the recorded progress: the drop cannot
-- be undone. Nothing in the app reads this table any more, so leaving it in
-- place is harmless if you would rather keep the history.
drop table if exists public.prep28_progress;

-- The "prep28-pdfs" storage bucket is NOT dropped: the resume PDF upload in
-- Settings still writes there. Renaming or deleting it would orphan every
-- resume already uploaded.
