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
                for u in units:
                    flights.append({
                        "group_name": g.get('name', 'Unknown'),
                        "unit_name": u.get('name', 'Unknown'),
                        "type": u.get('type', 'Unknown')
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
