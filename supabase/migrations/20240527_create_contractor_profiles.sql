-- Enable UUIDs once per DB
create extension if not exists "uuid-ossp";

create table if not exists contractor_profiles (
  id               uuid primary key default uuid_generate_v4(),
  user_id          uuid references users(id) on delete cascade unique,
  display_name     text not null,
  bio              text,
  trade            text not null,
  location         text,
  license_number   text,
  insurance_cert   text,
  google_reviews   jsonb default '[]'::jsonb,
  internal_rating  float default 0,
  created_at       timestamptz default now(),
  updated_at       timestamptz default now()
);

-- updated_at trigger
create or replace function trg_set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end; $$ language plpgsql;

create trigger t_contractor_profiles_u
before update on contractor_profiles
for each row execute procedure trg_set_updated_at();

-- RLS
alter table contractor_profiles enable row level security;
-- Contractor full access to own row
create policy "contractor self-access" on contractor_profiles
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
-- Admin role shortcut (role check done in supabase)
create policy "admin read" on contractor_profiles
  for select using (auth.role() = 'service_role');

-- Indexes
create index if not exists idx_contractor_trade on contractor_profiles(trade);
create index if not exists idx_contractor_location on contractor_profiles(location);
