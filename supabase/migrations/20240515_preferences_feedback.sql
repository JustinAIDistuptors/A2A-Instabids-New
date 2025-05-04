-- Migration to add user feedback table with row level security
create table if not exists user_feedback (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references users(id),
  rating int check (rating between 1 and 5),
  comments text,
  created_at timestamptz default now()
);

-- Enable row level security for user feedback
alter table user_feedback enable row level security;

-- Create policy to ensure users can only access their own feedback
create policy "user owns feedback" on user_feedback
  for all using (auth.uid() = user_id);