-- ─────────────────────────  EXTENSIONS  ─────────────────────────
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";   -- for gen_random_uuid()

-- ─────────────────────────  THREADS  ────────────────────────────
create table if not exists threads (
    id           uuid primary key default gen_random_uuid(),
    project_id   uuid references projects(id) on delete cascade,
    title        text,
    created_at   timestamptz default now(),
    updated_at   timestamptz default now()
);

-- keep updated_at fresh on any change to the row
create or replace function _set_updated_at() returns trigger
language plpgsql as
$$ begin new.updated_at := now(); return new; end $$;

drop trigger if exists trg_threads_updated on threads;
create  trigger trg_threads_updated
before  update on threads
for each row execute procedure _set_updated_at();

-- ─────────────────────  THREAD PARTICIPANTS  ────────────────────
create table if not exists thread_participants (
    thread_id uuid references threads(id) on delete cascade,
    user_id   uuid references users(id)   on delete cascade,
    role      text not null check (role in ('homeowner','contractor','system')),
    primary key (thread_id, user_id)
);

create index if not exists idx_tp_user   on thread_participants(user_id);
create index if not exists idx_tp_thread on thread_participants(thread_id);

-- ─────────────────────────  MESSAGES  ───────────────────────────
create table if not exists messages (
    id          uuid primary key default gen_random_uuid(),
    thread_id   uuid references threads(id) on delete cascade,
    sender_id   uuid references users(id)   on delete cascade,
    content     text not null,
    message_type text  default 'text',          -- future‑proof (image, system, …)
    metadata     jsonb default '{}'::jsonb,
    created_at  timestamptz default now()
);

create index if not exists idx_msg_thread       on messages(thread_id);
create index if not exists idx_msg_sender_time  on messages(sender_id, created_at);

-- ────────────────────────  RLS POLICIES  ────────────────────────
-- Enable RLS on all three tables
alter table threads             enable row level security;
alter table thread_participants enable row level security;
alter table messages            enable row level security;

-- Homeowner / contractor can see threads they participate in
create policy "read own threads"
on threads for select
using (exists (
        select 1 from thread_participants tp
        where tp.thread_id = threads.id
          and tp.user_id   = auth.uid()
));

-- Participants can insert messages into their threads
create policy "send messages in participant thread"
on messages for insert
with check (exists (
        select 1 from thread_participants tp
        where tp.thread_id = messages.thread_id
          and tp.user_id   = auth.uid()
));

-- Participants can read messages in their threads
create policy "read messages in participant thread"
on messages for select
using (exists (
        select 1 from thread_participants tp
        where tp.thread_id = messages.thread_id
          and tp.user_id   = auth.uid()
));

-- Thread participants table itself – users can read their rows
create policy "read my participant rows"
on thread_participants for select
using (user_id = auth.uid());

-- ───────────────────────  DONE  ────────────────────────────────
comment on table threads             is 'Conversation threads between homeowner & contractors';
comment on table thread_participants is 'Junction table listing participants per thread';
comment on table messages            is 'Messages (chat) linked to threads';
