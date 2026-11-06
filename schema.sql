create table stations (
  station_code integer primary key,
  name text,
  brand text,
  address text,
  latitude double precision,
  longitude double precision,
  state text
);

create table prices (
  station_code integer references stations(station_code),
  fuel_type text,
  price numeric(6,1),
  last_updated timestamp,
  fetched_at timestamptz default now(),
  primary key (station_code, fuel_type, last_updated)
);

alter table stations enable row level security;
alter table prices enable row level security;