# Roaming Zones

Roaming zones let you define a driving route or a radius around a city, and plugsmith
will find matching repeaters from your cached state data and generate a named zone in
your codeplug on the next build.

## When to use roaming zones

- Planning a road trip from city A to city B and want a zone of I-corridor repeaters
- Visiting a city and want a zone of local repeaters within 50 miles
- Keeping a "day trip" zone for a nearby area you visit regularly

## Accessing the Roaming tab

Press **Ctrl+G** or click the **Roaming** tab in the main interface.

---

## Two input modes

### Route mode

Finds repeaters within a corridor along a driving route between two cities.

- Geocodes both endpoints via Nominatim (or accepts raw `lat,lon`)
- Fetches the driving route geometry from the OSRM public routing API
- Returns all repeaters within `corridor_miles` of the route, ordered along it

### Radius mode

Finds all repeaters within a circle around a single location.

- Geocodes the center location (or accepts raw `lat,lon`)
- Returns all repeaters within `radius_miles`, sorted by distance

---

## Adding a roaming zone in the UI

1. Open the **Roaming** tab (`Ctrl+G`)
2. Click **Add Route** or **Add Radius Zone**
3. Fill in the location(s) and distance
4. Optionally adjust the zone name, FM, and DMR toggles
5. Click **Save** — the zone is written to `config.yaml` immediately
6. Run **Build** — the zone appears in your codeplug

---

## Config.yaml reference

Roaming zones are stored under the `roaming_zones` key in `config.yaml`.

```yaml
roaming_zones:
  - name: "Chicago → St. Louis"
    mode: route
    waypoints:
      - "Chicago, IL"          # or "41.85,-87.65"
      - "St. Louis, MO"        # or "38.62,-90.19"
    corridor_miles: 25         # half-width of corridor in miles
    include_fm: true
    include_dmr: true

  - name: "Sullivan 50mi"
    mode: radius
    center: "Sullivan, MO"     # or "38.2085,-91.1604"
    radius_miles: 50
    include_fm: true
    include_dmr: true
    max_channels: 80           # optional; defaults to radio's max per zone
```

### Field reference

| Field | Mode | Type | Default | Description |
|-------|------|------|---------|-------------|
| `name` | both | string | required | Zone name shown in radio |
| `mode` | both | `route` \| `radius` | required | Zone type |
| `waypoints` | route | list of strings | required | Start and end locations |
| `corridor_miles` | route | number | `25` | Half-width of route corridor |
| `center` | radius | string | required | Center location |
| `radius_miles` | radius | number | `50` | Search radius |
| `include_fm` | both | bool | `true` | Include analog FM channels |
| `include_dmr` | both | bool | `true` | Include DMR digital channels |
| `max_channels` | both | int | radio max | Optional per-zone cap |

---

## Location strings

All location fields accept either a place name or raw coordinates:

```yaml
center: "Sullivan, MO"          # geocoded via Nominatim
center: "38.2085,-91.1604"      # parsed directly, no HTTP call
center: "38.2085 -91.1604"      # space-separated also works
```

Geocoding results are cached in `.rb_cache/geocode_cache.json` — subsequent builds
skip the Nominatim call.

---

## Routing

Route mode calls the [OSRM public routing server](https://router.project-osrm.org)
to get the actual driving route geometry. The result is cached in
`.rb_cache/route_{hash}.json`.

**If OSRM is unavailable** (no internet, server down), plugsmith falls back to
20 linearly interpolated points between the start and end coordinates. The fallback
still works — it just won't follow roads.

---

## State cache requirements

Roaming zones only search repeaters that are **already in your cache**. If a route
passes through a state not in your `states:` list, repeaters from that state won't
appear.

To add states: edit `states:` in `config.yaml` (Config tab), then rebuild. The new
states will be fetched and cached; your roaming zones will automatically pick them up.

---

## Channel budget

Roaming zones are appended **after** the main tiered zones. The builder tracks the
remaining channel budget and caps each roaming zone so the total never exceeds your
radio's `max_channels`. If the budget runs out, remaining roaming zone definitions
are skipped and logged.

---

## Limitations

- Only searches states already in `.rb_cache/` — see [State cache requirements](#state-cache-requirements)
- Route corridor is a straight-line distance from each waypoint, not road-aware per-segment
- Geocoding requires internet access on first use (results cached)
- OSRM public server has no rate limit guarantee; falls back to linear interpolation on failure
