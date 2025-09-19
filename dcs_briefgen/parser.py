import math
import zipfile
from slpp import slpp as lua

def parse_miz(miz_path):
    flights = []
    situation = ""
    blue_task = ""

    with zipfile.ZipFile(miz_path, 'r') as z:
        # ---- Parse mission file for flights ----
        with z.open('mission') as f:
            mission_text = f.read().decode('utf-8')

        if mission_text.strip().startswith("mission ="):
            mission_text = mission_text[len("mission ="):].strip()

        mission_data = lua.decode(mission_text)

        map = mission_data.get('map')
        center_x = map.get('centerX')
        center_y = map.get('centerY')
        center_lat = 41 + 41.274 / 60     # 41.6879 approx
        center_lon = 41 + 26.656 / 60     # 41.4443 approx

        blue = mission_data.get('coalition', {}).get('blue', {})
        countries = blue.get('country', [])
        if isinstance(countries, dict):
            countries = list(countries.values())

        for c in countries:
            plane_data = c.get('plane', {})
            groups = plane_data.get('group', [])
            if isinstance(groups, dict):
                groups = list(groups.values())
            for g in groups:
                units = g.get('units', [])
                if isinstance(units, dict):
                    units = list(units.values())

                # Use just the first unit to get aircraft type
                u = units[0] if units else {}
                flights.append({
                    "group_name": g.get('name', 'Unknown'),
                    "unit_name": u.get('name', 'Unknown'),
                    "callsign": u.get('callsign', {}).get('name', 'Unknown'),  # optional callsign
                    "type": u.get('type', 'Unknown'),
                    "waypoints": extract_waypoints(g, center_x, center_y, center_lat, center_lon)
                })

        # ---- Parse l10n/DEFAULT/dictionary for briefing text ----
        if 'l10n/DEFAULT/dictionary' in z.namelist():
            with z.open('l10n/DEFAULT/dictionary') as f:
                dict_text = f.read().decode('utf-8')
                # Remove leading assignment if present
                if dict_text.strip().startswith("dictionary ="):
                    dict_text = dict_text.strip()[len("dictionary ="):].strip()
                dict_data = lua.decode(dict_text)
                if dict_data is None:
                    dict_data = {}

                # Some missions wrap everything under a 'dictionary' key
                if 'dictionary' in dict_data:
                    dict_data = dict_data['dictionary']

                situation = dict_data.get('DictKey_descriptionText_1', "")
                blue_task = dict_data.get('DictKey_descriptionBlueTask_3', "")

    return {
        "flights": flights,
        "situation": situation,
        "blue_task": blue_task
    }


def extract_waypoints(group, center_x_m, center_y_m, center_lat, center_lon):
    """
    Returns a list of dicts for the waypoints with x/y/alt/speed.
    """
    route = group.get("route", {})
    points = route.get("points", [])

    waypoints = []

    for p in points.values():
        
        wp = {
            "x": p.get("x"),
            "y": p.get("y"),
            "name": p.get("name"),
            "alt": p.get("alt", 0),
            "speed": p.get("speed", 0),
            "type": p.get("type", ""),
            "action": p.get("action", "")
        }

        wp["lat"], wp["lon"] = meters_to_latlon(
            wp["x"], wp["y"], center_x_m, center_y_m, center_lat, center_lon
        )

        waypoints.append(wp)
    return waypoints

def meters_to_latlon(x, y, center_x_m, center_y_m, center_lat, center_lon):
    """
    Convert DCS x/y (meters) relative to map center to decimal degrees lat/lon.
    """
    dx = x - center_x_m  # east offset
    dy = y - center_y_m  # north offset

    meters_per_deg_lat = 111320
    meters_per_deg_lon = 111320 * math.cos(math.radians(center_lat))

    lat = center_lat + (dx / meters_per_deg_lat)
    lon = center_lon + (dy / meters_per_deg_lon)
    return lat, lon