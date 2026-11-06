create or replace function nearby_cheapest(
  user_lat double precision,
  user_lng double precision,
  fuel text,
  radius_km double precision default 10
)
returns table (
  name text, brand text, address text,
  latitude double precision, longitude double precision,
  price numeric, last_updated timestamp, distance_km double precision
)
language sql
stable
as $$
  with latest as (
    select distinct on (station_code, fuel_type)
      station_code, fuel_type, price, last_updated
    from prices
    where fuel_type = fuel
    order by station_code, fuel_type, last_updated desc
  ),
  with_distance as (
    select s.name, s.brand, s.address, s.latitude, s.longitude,
           l.price, l.last_updated,
           6371 * 2 * asin(sqrt(
             power(sin(radians(s.latitude - user_lat) / 2), 2) +
             cos(radians(user_lat)) * cos(radians(s.latitude)) *
             power(sin(radians(s.longitude - user_lng) / 2), 2)
           )) as distance_km
    from latest l
    join stations s on s.station_code = l.station_code
    where s.latitude is not null and s.longitude is not null
  )
  select * from with_distance
  where distance_km <= radius_km
  order by price, distance_km
  limit 10;
$$;