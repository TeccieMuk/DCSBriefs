import calendar
import datetime
import math
import zipfile
from slpp import slpp as lua

from dcs_briefgen.projection import active_map, miz_to_ll

def parse_miz(miz_path):
    flights = []
    situation = ""
    blue_task = ""

    caucasus_conf = {
        "central_meridian": 33, 
        "scale_factor": 0.9996, 
        "false_easting": -99516.9999999732, 
        "false_northing": -4998114.999999984
    }

    active_map(caucasus_conf)

    with zipfile.ZipFile(miz_path, 'r') as z:
        # ---- Parse mission file for flights ----
        with z.open('mission') as f:
            mission_text = f.read().decode('utf-8')

        if mission_text.strip().startswith("mission ="):
            mission_text = mission_text[len("mission ="):].strip()

        mission_data = lua.decode(mission_text)
        mission_epoch = parse_start_epoch(mission_data)

        map = mission_data.get('map')
        center_x = map.get('centerY')
        center_y = map.get('centerX')
        center_lat = 41 + 41.274 / 60     # 41.6879 approx
        center_lon = 41 + 26.656 / 60     # 41.4443 approx

        blue = mission_data.get('coalition', {}).get('blue', {})
        blue_coalition = parse_coalition(blue, center_x, center_y, center_lat, center_lon)
        red = mission_data.get('coalition', {}).get('red', {})
        red_coalition = parse_coalition(red, center_x, center_y, center_lat, center_lon)

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
                blue_coalition['task'] = blue_task.replace("\\\n", "\n")  # remove Lua-style backslash line breaks

    return {
        "situation": situation.replace("\\\n", "\n"),  # remove Lua-style backslash line breaks
        "start_epoch": mission_epoch,
        "blue_coalition": blue_coalition,
        "red_coalition": red_coalition
    }

def parse_coalition(coalition, center_x, center_y, center_lat, center_lon):
    bullseye_miz = coalition.get("bullseye", {})
    bullseye = {'lat': 0, 'lon': 0}
    if bullseye_miz:
        y = bullseye_miz.get("y")
        x = bullseye_miz.get("x")
        # convert to lat/lon
        lat, lon = miz_to_ll(y, x)
        bullseye['lat'] = lat
        bullseye['lon'] = lon

    countries = coalition.get('country', [])
    if isinstance(countries, dict):
        countries = list(countries.values())

    flights = []
    ships = []
    statics = []
    helicopters = []
    vehicles = []
    for c in countries:
        plane_data = c.get('plane', {})
        ship_data = c.get('ship', {})
        static_data = c.get('static', {})
        helicopter_data = c.get('helicopter')
        vehicle_data = c.get('vehicle')

        if plane_data:
            flights.extend(parse_unit_type(plane_data))
        if ship_data:
            ships.extend(parse_unit_type(ship_data))
        if static_data:
            statics.extend(parse_unit_type(static_data))
        if helicopter_data:
            helicopters.extend(parse_unit_type(helicopter_data))
        if vehicle_data:
            vehicles.extend(parse_unit_type(vehicle_data))
    return {
        "flights": flights,
        "ships": ships,
        "static": statics,
        "helicopters": helicopters,
        "vehicles": vehicles,
        "bullseye": bullseye
    }


def parse_unit_type(unit_type):
    groups = []
    groups_raw = unit_type.get('group', [])
    if isinstance(groups_raw, dict):
        groups_raw = list(groups_raw.values())
    for g in groups_raw:
        units = g.get('units', [])
        if isinstance(units, dict):
            units = parse_units(list(units.values()))

        group = {
            "name": g.get('name', 'Unknown'),
            "frequency": g.get('frequency', 'Unknown'),
            "is_awacs": g.get('task', 'Unknown') == "AWACS",
            "is_tanker": g.get('task', 'Unknown') == "Refueling",
            "units": units,
        }
        waypoints = extract_waypoints(g, group)
        group["waypoints"] = waypoints
        groups.append(group)
    return groups


def parse_units(units_raw):
    units = []
    for u in units_raw:

        frequency = u.get('frequency')
        if frequency:
            frequency = frequency / 1000000
        else:
            frequency = 'Unknown'
        units.append({
            "type": u.get('type', 'Unknown'),
            "radios": extract_radio_channels(u),
            "unit_id": u.get('unitId'),
            "name": u.get('name'),
            "frequency": frequency,
            "tacan_channels": []
        })
    return units



def parse_start_epoch(mission_data):
    """Extract start date+time from mission data and return as epoch (UTC)."""
    date = mission_data.get("date", {})
    start_seconds = mission_data.get("start_time", 0)

    year = date.get("Year", 1970)
    month = date.get("Month", 1)
    day = date.get("Day", 1)

    # Base date at midnight
    dt = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)

    # Add seconds since midnight
    dt = dt + datetime.timedelta(seconds=start_seconds)

    # Convert to Unix epoch
    epoch = calendar.timegm(dt.utctimetuple())
    return epoch


def distance_m(p1, p2):
    dx = p2["x"] - p1["x"]
    dy = p2["y"] - p1["y"]
    return math.sqrt(dx**2 + dy**2)

def heading_deg(wp1, wp2):
    """
    Compute heading from wp1 to wp2 in degrees.
    Assumes wp1 and wp2 have 'lat' and 'lon' keys in decimal degrees.
    Returns 0 = north, 90 = east, etc.
    """
    dx = wp2["lon"] - wp1["lon"]
    dy = wp2["lat"] - wp1["lat"]

    head = math.atan2(dx, dy) * 180 / math.pi
    if head < 0:
        head += 360

    return head

def extract_waypoints(group_data, group):
    route = group_data.get("route", {})
    points = route.get("points", {})

    waypoints = []
    prev_wp = None

    for i, key in enumerate(sorted(points.keys()), start=1):
        p = points[key]
        speed_mps = p.get("speed", 0)
        alt_m = p.get("alt", 0)

        wp = {
            "#": i,
            "name": p.get("name", f"WP{i}"),
            "x": p.get("x"),
            "y": p.get("y"),
            "speed": speed_mps * 1.94384,
            "alt": round(alt_m * 3.28084),           # feet
            "time": p.get("ETA")
        }

        # Check take-off group
        if i==1 and wp["alt"] == 0:
            linked_unit = p.get("linkUnit", None)
            if linked_unit:
                group["linked_takeoff_unit"] = linked_unit
        else:
            linked_unit = extract_task_link(p)
            if linked_unit:
                group["linked_takeoff_unit"] = linked_unit


        # convert coords
        wp["lat"], wp["lon"] = miz_to_ll(p.get("y"), p.get("x"))
        # distance & heading from previous point
        if prev_wp:
            dist = distance_m(prev_wp, wp) / 1852  # nm
            head = heading_deg(prev_wp, wp)
        else:
            dist = 0
            head = 0

        wp["dist"] = round(dist, 1)
        wp["head"] = round(head)
        channels = extract_tacan_info(p)

        if channels:
            for channel_info in channels:
                channel = channel_info["channel"]
                mode = channel_info["mode"]
                unit_id = channel_info["unit_id"]
                unit = None
                if len(group["units"]) == 1:
                    unit = group["units"][0]
                else:
                    unit = next((u for u in group["units"] if u.get("unit_id") == unit_id), None)
                if unit is not None:
                    unit.setdefault("tacan_channels", []).append({
                        "channel": channel,
                        "mode": mode
                    })

        waypoints.append(wp)
        prev_wp = wp

    return waypoints

def extract_tacan_info(waypoint):
    """
    Extract frequency and modeChannel from a waypoint's tasks if ActivateBeacon is present.
    Returns (channel, mode, unit_id) or (None, None, None).
    """
    tacan_channels = []
    try:
        task = waypoint.get("task", {})
        if task.get("id") != "ComboTask":
            return None

        tasks_dict = task.get("params", {}).get("tasks", {})
        for t in tasks_dict.values():  # <- use .values() to get the actual task dicts
            if t.get("id") == "WrappedAction":
                action = t.get("params", {}).get("action", {})
                if action.get("id") == "ActivateBeacon":
                    params = action.get("params", {})
                    channel = params.get("channel")
                    mode = params.get("modeChannel")
                    unit_id = params.get("unitId")  # sometimes missing
                    tacan_channels.append({"channel": channel, "mode": mode, "unit_id": unit_id})
    except Exception:
        pass
    return tacan_channels

def extract_task_link(waypoint):
    try:
        task = waypoint.get("task", {})
        if task.get("id") != "ComboTask":
            return None

        tasks_dict = task.get("params", {}).get("tasks", {})
        for t in tasks_dict.values():  # <- use .values() to get the actual task dicts
            task_name = t.get("name", None)
            if task_name and task_name.upper().startswith("LAND@"):
                number = int(task_name.split("@")[1])
                return number

    except Exception:
        pass
    return None


def extract_radio_channels(unit):
    radios = unit.get("Radio", {})
    all_channels = []

    for radio_id, radio_data in radios.items():
        channels = radio_data.get("channels", {})
        # Collect all channels as a sorted list of (index, value) tuples
        channels_list = sorted(channels.items())
        all_channels.append({
            "radio_id": radio_id,
            "channels": [ch for idx, ch in channels_list]
        })

    return all_channels
