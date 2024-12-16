import re
import os
import json


def load_preset_json():
    json_file_path = os.path.join(os.path.dirname(__file__), 'preset.json')
    with open(json_file_path, "r") as file:
        data = json.load(file)
    return data


def sanitize_name(name):
    """
    Sanitize a string to allow only valid characters for filenames and folder names.
    """
    return re.sub(r"[^a-zA-Z0-9 #\-().]+", "", name)


def parse_filename(filename):
    """
    Parse the filename to extract the base name and key.
    """
    match = re.match(r"^(.*?)-(\d+)", filename, re.IGNORECASE)
    if not match:
        raise ValueError(f"Filename '{filename}' does not match the expected pattern.")

    base_name = sanitize_name(match.group(1))
    key = int(match.group(2))
    return base_name, key


def sample_metadata(frame_count, output_basename, hi_key, low_key, center):
    """
    Generate the JSON metadata for the given WAV file and key.
    """

    loop_start = frame_count // 4  # Arbitrary, first 25% of the sample
    loop_end = frame_count * 3 // 4  # Arbitrary, last 25% of the sample

    metadata = {
        "framecount": frame_count,
        "hikey": hi_key,
        "lokey": low_key,
        "loop.crossfade": 0,
        "loop.end": int(loop_end),
        "loop.onrelease": True,
        "loop.start": int(loop_start),
        "pitch.keycenter": center,
        "reverse": False,
        "sample": output_basename,
        "sample.end": int(frame_count),
        "tune": 0
    }
    return metadata