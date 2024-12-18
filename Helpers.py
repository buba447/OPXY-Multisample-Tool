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
    first_part, remainder = filename.split("-", 1)
    base_name = sanitize_name(first_part)
    # Regex to match a music note or the first number after the dash
    note_pattern = r'\b[A-G](?:b|#|-)?-?\d\b'
    number_pattern = r'\b\d+\b'

    # Try to find a note first
    note_match = re.search(note_pattern, remainder)
    if note_match:
        return base_name, note_string_to_midi_value(note_match.group())

    # If no note, find the first number
    number_match = re.search(number_pattern, remainder)
    if number_match:
        return base_name, int(number_match.group())

    raise ValueError(f"Filename '{filename}' does not match the expected pattern.")


def sample_metadata(frame_count, output_basename, hi_key, low_key, center, loop_crossfade=0, loop_start=None, loop_end=None):
    """
    Generate the JSON metadata for the given WAV file and key.
    """
    if loop_start is None:
        loop_start = frame_count // 4  # Arbitrary, first 25% of the sample
    if loop_end is None:
        loop_end = frame_count * 3 // 4  # Arbitrary, last 25% of the sample

    metadata = {
        "framecount": frame_count,
        "hikey": hi_key,
        "lokey": low_key,
        "loop.crossfade": loop_crossfade,
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


NOTE_OFFSET = [21, 23, 12, 14, 16, 17, 19]

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_note_to_string(value):
    import math
    octave = math.floor(value / 12)
    noteNumber = value - (octave * 12)
    return '%s%i' % (NOTE_NAMES[noteNumber], octave - 2)


def note_string_to_midi_value(note):
    string = note.replace(' ', '')
    if len(string) < 2:
        raise ValueError("Bad note format")
    noteidx = ord(string[0].upper()) - 65  # 65 os ord('A')
    if not 0 <= noteidx <= 6:
        raise ValueError("Bad note")
    sharpen = 0
    if string[1] == "#":
        sharpen = 1
    elif string[1].lower() == "b":
        sharpen = -1
    # int may throw exception here
    midi_note = int(string[1 + abs(sharpen) :]) * 12 + NOTE_OFFSET[noteidx] + sharpen
    return midi_note


import re

# Regex pattern to match the music notes
pattern = r'\b[A-G](?:b|#|-)?-?\d\b'

testString = "Rhodes Mark 1-096-127 Ab5.WAV"

print(parse_filename(testString))
# match = re.search(pattern, testString)
# if match:
#     print(note_string_to_midi_value(match.group()))