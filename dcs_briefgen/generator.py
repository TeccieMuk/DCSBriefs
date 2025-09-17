import zipfile
import os

def create_briefing(miz_path, selected_groups, out_zip, flights=None, situation="", blue_task=""):
    """
    Create a briefing ZIP.

    :param miz_path: path to the .miz file (not used yet, could include maps)
    :param selected_groups: list of group names selected by user
    :param out_zip: path to the output ZIP
    :param flights: list of all flight dicts from parser
    :param situation: Situation text
    :param blue_task: Blue Task text
    """
    # Prepare briefing text
    briefing_lines = []
    briefing_lines.append("=== Situation ===")
    briefing_lines.append(situation or "No situation provided.")
    briefing_lines.append("\n=== Blue Task ===")
    briefing_lines.append(blue_task or "No blue task provided.")
    briefing_lines.append("\n=== Selected Flights ===")

    if flights:
        for group_name in selected_groups:
            group_units = [f for f in flights if f['group_name'] == group_name]
            briefing_lines.append(f"\nGroup: {group_name} ({len(group_units)} units)")
            for u in group_units:
                briefing_lines.append(f" - {u['unit_name']} ({u['type']})")
    else:
        briefing_lines.append("No flight info available.")

    briefing_text = "\n".join(briefing_lines)

    # Write briefing to zip
    with zipfile.ZipFile(out_zip, 'w') as z:
        z.writestr("briefing.txt", briefing_text)
