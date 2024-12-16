"""OPXY Multisample Tool: Pack Samples

This script is used to pack a collection of multisamples into an instrument preset for the OPXY.

Sample Prep:

    Place your samples in a folder. The naming format for samples follows a format like "Sample Name-[Note Number].wav"
    Where the note number is a number from 0-127. With 0 being C-1, 127 being G9 and 60 is Middle C.

    Like so

    "InputFolder\My Awesome Sample-48.wav"
    "InputFolder\My Awesome Sample-60.wav"
    "InputFolder\My Awesome Sample-64.wav"

    Some samples are named with a note and a velocity.
    "My Awesome Sample-48-127.wav"

    The OPXY does not currently support velocity mappings.
    There is no need to rename these. The script will automatically choose the highest velocity for each note.

Usage:
    python PackSamples.py --input /Path/To/Sample/Directory --output /Path/To/Output/Directory --name "Preset Name"
    python PackSamples.py --input /Path/To/Sample/Directory --output /Path/To/Output/Directory

    The instrument name can be specified, or it will be inferred from the sample names automatically.

    The resulting instrument pack will be places in the output directory and the audio files will be copied into it.
    This resulting directory can then be copied into the OPXY 'presets' directory.
    Instrusments can be grouped into a subdirectory one level deep.

    "\preset\Group Folder\My Awesome Preset.preset"
    "\preset\Group Folder\My Second Awesome Preset.preset"

Features:
    - Generates preset JSON for OPXY multisample instrument.
    - Properly names files according to OPXY naming standards.
    - Packs JSON and Audio Files into the appropriate file structure for OPXY.
    - Use the --help flag to display usage information.

License:
    MIT License
"""

import os
import re
import json
import subprocess
import argparse
import shutil

parser = argparse.ArgumentParser(
    description="Generate JSON files for multisample mappings.",
    epilog=""
)
parser.add_argument("--input", required=False, help="Directory containing WAV files for processing.")
parser.add_argument("--bulk", required=False, help="Directory containing nested directories of WAV files for processing.")
parser.add_argument("--output", required=True, help="Directory to save the generated multisample preset.")
parser.add_argument("--name", required=False, help="Name of the preset.")

args = parser.parse_args()

def load_preset_json():
    json_file_path = os.path.join(os.path.dirname(__file__), 'preset.json')
    with open(json_file_path, "r") as file:
        data = json.load(file)
    return data

preset_json = load_preset_json()

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

def get_wav_info(filename):
    """
    Get sample rate and frame count using `ffprobe`.
    Modify to use the tool available on your system.
    """
    # Use ffprobe (part of ffmpeg) to extract audio details
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=sample_rate,nb_frames,duration",
        "-of", "json",
        filename
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error processing {filename}: {result.stderr}")

    data = json.loads(result.stdout)
    stream = data["streams"][0]

    sample_rate = int(stream["sample_rate"])
    if "nb_frames" in stream:
        frame_count = int(stream["nb_frames"])
    elif "duration" in stream:
        frame_count = int(float(stream["duration"]) * sample_rate)
    else:
        raise RuntimeError(f"Cannot determine frame count for {filename}.")
    return sample_rate, frame_count


def generate_metadata(input_file, output_basename, hi_key, low_key, center):
    """
    Generate the JSON metadata for the given WAV file and key.
    """
    sample_rate, frame_count = get_wav_info(input_file)
    loop_start = frame_count // 4  # Arbitrary, first 25% of the sample
    loop_end = frame_count * 3 // 4  # Arbitrary, last 25% of the sample

    metadata = {
        "framecount": frame_count,
        "hikey": hi_key,
        "lokey": low_key,
        "loop.crossfade": 0,
        "loop.end": loop_end,
        "loop.onrelease": True,
        "loop.start": loop_start,
        "pitch.keycenter": center,
        "reverse": False,
        "sample": output_basename,
        "sample.end": frame_count,
        "tune": 0
    }

    # Write JSON file
    return metadata


def process_samples(input_dir, output_dir, preset_name):
    """
    Process all WAV files in the input directory.

    According to the XY how-to samples are saved like
    presets/subfolder/name.preset/patch.json
    """

    filenames = os.listdir(input_dir)

    if preset_name is None or len(preset_name) == 0:
        # Generate preset name from the sample
        preset_name, _ = parse_filename(filenames[0])

    print(f'Exporting Samples {preset_name}')
    preset_name = sanitize_name(preset_name)
    preset_directory = os.path.join(output_dir, f"{preset_name}.preset")

    os.makedirs(preset_directory, exist_ok=True)

    filenames.sort()

    keys = {}

    for filename in filenames:
        if filename.lower().endswith(".wav"):
            base_name, key = parse_filename(filename)
            keys[key] = (base_name, os.path.join(input_dir, filename), filename)

    last_key = 0
    for key in sorted(keys.keys()):
        base_name, wav_file, filename = keys[key]
        wav_name = sanitize_name(filename)
        try:
            metadata = generate_metadata(wav_file, wav_name, key, last_key, key)
            last_key = key + 1
            preset_json['regions'].append(metadata)
            shutil.copy(wav_file, os.path.join(preset_directory, wav_name))
        except Exception as e:
            print(f"Error processing {wav_file}: {e}")

    json_file = os.path.join(preset_directory, 'patch.json')

    # Write JSON file
    with open(json_file, "w") as f:
        json.dump(preset_json, f)
    print(f'Generated Patch! You may now copy {preset_name}.preset to the OPXY under \"presets\\PRESET GROUP\\')

# Main
if __name__ == "__main__":
    if args.bulk is not None and len(args.bulk):
        bulk_directory = args.bulk
        for d in os.listdir(bulk_directory):
            preset_json = load_preset_json()
            sub_path = os.path.join(bulk_directory, d)
            if os.path.isdir(sub_path):
                process_samples(sub_path, args.output, None)
    else:
        process_samples(args.input, args.output, args.name)
