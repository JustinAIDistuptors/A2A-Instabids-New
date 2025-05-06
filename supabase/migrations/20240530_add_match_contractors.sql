-- 20240530_add_match_contractors.sql

-- ───────────── EXTENSIONS ─────────────
-- these give us distance helpers in Postgres
CREATE EXTENSION IF NOT EXISTS cube;
CREATE EXTENSION IF NOT EXISTS earthdistance;

-- ──────────── MATCHING FUNCTION ────────────
-- Returns up to 25 contractors ordered by:
--   1) same category (bonus 100)
--   2) proximity (miles)
--   3) contractor rating
CREATE OR REPLACE FUNCTION match_contractors(p_project UUID)
RETURNS TABLE (
  contractor_id UUID,
  distance_miles NUMERIC,
  rating         NUMERIC,
  match_score    NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  _lat NUMERIC;
  _lon NUMERIC;
  _cat TEXT;
BEGIN
  -- fetch project’s lat,lon,category
  SELECT
    (location->>'lat')::NUMERIC,
    (location->>'lon')::NUMERIC,
    category
  INTO _lat, _lon, _cat
  FROM projects
  WHERE id = p_project;

  RETURN QUERY
  SELECT
    c.user_id                   AS contractor_id,
    earth_distance(
      ll_to_earth(_lat, _lon),
      ll_to_earth((c.location->>'lat')::NUMERIC, (c.location->>'lon')::NUMERIC)
    ) / 1609.34                 AS distance_miles,
    COALESCE(c.rating, 0)       AS rating,
    (
      (CASE WHEN _cat = ANY(c.service_categories) THEN 100 ELSE 0 END)
      - (earth_distance(
            ll_to_earth(_lat, _lon),
            ll_to_earth((c.location->>'lat')::NUMERIC, (c.location->>'lon')::NUMERIC)
         ) / 1609.34)
      + COALESCE(c.rating, 0)
    )                            AS match_score
  FROM contractor_profiles c
  WHERE c.enabled IS TRUE
    AND earth_box(
          ll_to_earth(_lat, _lon),
          80467                      -- ~50 mi in metres
        ) @> ll_to_earth(
              (c.location->>'lat')::NUMERIC,
              (c.location->>'lon')::NUMERIC
            )
  ORDER BY match_score DESC
  LIMIT 25;
END;
$$;

-- Let your anon & authenticated roles call it (RLS still applies)
GRANT EXECUTE ON FUNCTION match_contractors(UUID) TO anon, authenticated;


-- helper RPC: rank contractors by simple rule
create or replace function match_contractors_rule(p_category text, p_lat float8, p_lng float8)
returns table (
    id uuid,
    score float4
) language plpgsql as $$
begin
  return query
  select cp.id,
         ( 0.55 * (1 - (cp.category_vector <=> (select category_vector from bid_cards where category = p_category limit 1)))  -- cosine sim
         + 0.25 * (case when p_lat is null then 0.5 else greatest(0,1 - ( _haversine_km(cp.lat, cp.lng, p_lat, p_lng) / 75 )) end)
         + 0.1  * (1 - cp.active_jobs::float / greatest(1,cp.max_concurrent))
         + 0.1  * cp.accept_rate_30d
         ) as score
  from contractor_profiles cp
  where cp.is_active;
end $$;
