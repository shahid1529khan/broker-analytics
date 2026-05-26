-- supabase/schema.sql
-- COMPLETE POSTGRESQL SCHEMA FOR YIELD COMMISSION ANALYSIS PLATFORM

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. ORGANISATIONS TABLE
create table public.organisations (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. USERS (STAFF) TABLE
-- Linked to Supabase auth.users
create table public.users (
    id uuid primary key default uuid_generate_v4(),
    auth_id uuid references auth.users(id) on delete cascade not null,
    email text not null unique,
    organisation_id uuid references public.organisations(id) on delete cascade not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. AGGREGATORS TABLE
create table public.aggregators (
    id uuid primary key default uuid_generate_v4(),
    name text not null unique, -- E.g. 'Connective', 'FAST', 'AFG', 'Finsure', 'Vow Financial'
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 4. BROKER CLIENTS TABLE
create table public.broker_clients (
    id uuid primary key default uuid_generate_v4(),
    organisation_id uuid references public.organisations(id) on delete cascade not null,
    name text not null,
    contact_name text,
    contact_email text,
    contact_phone text,
    status text not null default 'active' check (status in ('active', 'archived', 'pending documents', 'under offer', 'sold')),
    notes text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 5. STATEMENT UPLOADS TABLE
create table public.statement_uploads (
    id uuid primary key default uuid_generate_v4(),
    client_id uuid references public.broker_clients(id) on delete cascade not null,
    aggregator_id uuid references public.aggregators(id) on delete cascade not null,
    period_month text not null check (period_month ~ '^\d{4}-\d{2}$'), -- Format: 'YYYY-MM'
    status text not null default 'pending' check (status in ('pending', 'processing', 'completed', 'failed', 'review_required')),
    file_name text not null,
    file_path text not null, -- Supabase Storage link
    row_count integer default 0,
    flagged_row_count integer default 0,
    error_message text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 6. LOAN ROWS TABLE (NORMALISED DATA - CORE INTEL ENGINE)
-- Linked to statements and broker clients
create table public.loan_rows (
    id uuid primary key default uuid_generate_v4(),
    upload_id uuid references public.statement_uploads(id) on delete cascade not null,
    client_id uuid references public.broker_clients(id) on delete cascade not null,
    loan_id text, -- Can be null or ref
    borrower_reference text, -- Anonymised descriptor or ID
    lender_name text not null, -- E.g. CBA, Westpac, ANZ
    settlement_date date, -- Formatted YYYY-MM-DD
    loan_amount_original numeric(15,2),
    outstanding_balance numeric(15,2) not null check (outstanding_balance >= 0),
    trail_rate_percent numeric(8,4), -- E.g. 0.1500
    trail_income_this_period numeric(15,2) not null,
    upfront_commission numeric(15,2) default 0.00,
    period_month text not null check (period_month ~ '^\d{4}-\d{2}$'),
    aggregator_name text not null,
    raw_row_index integer not null,
    is_flagged boolean default false not null,
    validation_notes text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 7. AGGREGATOR SCHEMAS TABLE
-- Stores column mappings detected per aggregator
create table public.aggregator_schemas (
    id uuid primary key default uuid_generate_v4(),
    aggregator_id uuid references public.aggregators(id) on delete cascade not null unique,
    column_mapping jsonb not null, -- Map raw sheet names -> target database cols
    is_verified boolean default false not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);


-- TRIGGER FOR UPDATED_AT MUTATIVE UPDATES
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger set_organisations_updated_at before update on public.organisations for each row execute procedure public.handle_updated_at();
create trigger set_users_updated_at before update on public.users for each row execute procedure public.handle_updated_at();
create trigger set_aggregators_updated_at before update on public.aggregators for each row execute procedure public.handle_updated_at();
create trigger set_broker_clients_updated_at before update on public.broker_clients for each row execute procedure public.handle_updated_at();
create trigger set_statement_uploads_updated_at before update on public.statement_uploads for each row execute procedure public.handle_updated_at();
create trigger set_loan_rows_updated_at before update on public.loan_rows for each row execute procedure public.handle_updated_at();
create trigger set_aggregator_schemas_updated_at before update on public.aggregator_schemas for each row execute procedure public.handle_updated_at();


-- INDEXES FOR SPEEDY ANALYTICS IN MODULE 2 (HIGHLY FREQUENT READ CONSTRAINTS)
create index idx_broker_clients_org on public.broker_clients(organisation_id);
create index idx_statement_uploads_client on public.statement_uploads(client_id);
create index idx_loan_rows_client on public.loan_rows(client_id);
create index idx_loan_rows_period on public.loan_rows(period_month);
create index idx_loan_rows_lender on public.loan_rows(lender_name);
create index idx_loan_rows_settlement on public.loan_rows(settlement_date);
create index idx_loan_rows_client_period on public.loan_rows(client_id, period_month);


-- ROW LEVEL SECURITY (RLS) POLICIES
-- Enforces absolute multi-tenant tenant/broker isolation.

alter table public.organisations enable row_level_security;
alter table public.users enable row_level_security;
alter table public.aggregators enable row_level_security;
alter table public.broker_clients enable row_level_security;
alter table public.statement_uploads enable row_level_security;
alter table public.loan_rows enable row_level_security;
alter table public.aggregator_schemas enable row_level_security;

-- Helper Function to resolve current user's organisation_id
create or replace function public.get_user_org_id()
returns uuid as $$
declare
    org_id uuid;
begin
    select organisation_id into org_id
    from public.users
    where auth_id = auth.uid()
    limit 1;
    
    return org_id;
end;
$$ language plpgsql security definer;


-- Policies for public.organisations
create policy "Users can read their own organisation details"
    on public.organisations
    for select
    using (id = public.get_user_org_id());

-- Policies for public.users
create policy "Users can read administrative users inside their organisation"
    on public.users
    for select
    using (organisation_id = public.get_user_org_id());

-- Policies for public.broker_clients (Strict cross-client protection)
create policy "Users can read clients in their organisation"
    on public.broker_clients
    for select
    using (organisation_id = public.get_user_org_id());

create policy "Users can edit clients in their organisation"
    on public.broker_clients
    for all
    using (organisation_id = public.get_user_org_id())
    with check (organisation_id = public.get_user_org_id());

-- Policies for public.statement_uploads (Linked to clients)
create policy "Users can read statement uploads for their organization clients"
    on public.statement_uploads
    for select
    using (
        client_id in (
            select id from public.broker_clients where organisation_id = public.get_user_org_id()
        )
    );

create policy "Users can manage statement uploads of their clients"
    on public.statement_uploads
    for all
    using (
        client_id in (
            select id from public.broker_clients where organisation_id = public.get_user_org_id()
        )
    )
    with check (
        client_id in (
            select id from public.broker_clients where organisation_id = public.get_user_org_id()
        )
    );

-- Policies for public.loan_rows
create policy "Users can read loan rows for their organization clients"
    on public.loan_rows
    for select
    using (
        client_id in (
            select id from public.broker_clients where organisation_id = public.get_user_org_id()
        )
    );

create policy "Users can manage loan rows of their clients"
    on public.loan_rows
    for all
    using (
        client_id in (
            select id from public.broker_clients where organisation_id = public.get_user_org_id()
        )
    )
    with check (
        client_id in (
            select id from public.broker_clients where organisation_id = public.get_user_org_id()
        )
    );

-- Policies for public.aggregator_schemas (Global database mapping registry)
create policy "Aggregator schemas are globally readable by authenticated staff"
    on public.aggregator_schemas
    for select
    using (auth.role() = 'authenticated');

create policy "Staff users can update mappings"
    on public.aggregator_schemas
    for all
    using (auth.role() = 'authenticated')
    with check (auth.role() = 'authenticated');

-- Policies for public.aggregators
create policy "Aggregators are readable by authenticated staff"
    on public.aggregators
    for select
    using (auth.role() = 'authenticated');

create policy "Staff can manage aggregators"
    on public.aggregators
    for all
    using (auth.role() = 'authenticated')
    with check (auth.role() = 'authenticated');
