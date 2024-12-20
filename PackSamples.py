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
import Helpers
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
parser.add_argument("--sample_rate", required=False, type=int, help="Force a sample rate. Will re-encode if the sample rate of the source does not match.")
parser.add_argument("--sample_start", required=False, type=float, help="Time in seconds for the sample start point. Useful for samples that have a bit of silence at the beginning.")

args = parser.parse_args()


preset_json = Helpers.load_preset_json()


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


def reencode_wav_file(input_file, output_file, sample_rate):
    # ffmpeg -i input.wav -ar 44100 output.wav
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-ar", f'{sample_rate}',
        output_file
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error processing {input_file}: {result.stderr}")



def process_samples(input_dir, output_dir, preset_name, sample_rate, sample_start):
    """
    Process all WAV files in the input directory.

    According to the XY how-to samples are saved like
    presets/subfolder/name.preset/patch.json
    """
    if sample_start is None:
        sample_start = 0

    filenames = [f for f in os.listdir(input_dir) if os.path.splitext(f)[-1].lower() in ['.wav', '.aiff']]

    if preset_name is None or len(preset_name) == 0:
        # Generate preset name from the sample
        preset_name, _ = Helpers.parse_filename(filenames[0])

    preset_name = Helpers.sanitize_name(preset_name)
    print(f'Exporting Samples {preset_name}')
    preset_directory = os.path.join(output_dir, f"{preset_name}.preset")

    os.makedirs(preset_directory, exist_ok=True)

    filenames.sort()

    keys = {}

    for filename in filenames:
        base_name, key = Helpers.parse_filename(filename)
        keys[key] = (base_name, os.path.join(input_dir, filename), filename)

    last_key = 0
    key_metadata = []
    for key in sorted(keys.keys()):
        base_name, wav_file, filename = keys[key]
        wav_name = Helpers.sanitize_name(filename)
        file_sample_rate, frame_count = get_wav_info(wav_file)
        if sample_rate is None:
            sample_rate = file_sample_rate
        copy_file = True
        if sample_rate != file_sample_rate:
            print('Re-encoding', os.path.basename(wav_file))
            copy_file = False
            output_file = os.path.join(preset_directory, wav_name)
            input_file = wav_file
            reencode_wav_file(input_file, output_file, sample_rate)
        print('Packing key ', os.path.basename(wav_file), key)
        try:
            metadata = Helpers.sample_metadata(
                frame_count=frame_count,
                output_basename=wav_name,
                low_key=last_key,
                hi_key=key,
                center=key,
                sample_start=sample_start*sample_rate)
            last_key = key + 1
            key_metadata.append(metadata)
            if copy_file:
                shutil.copy(wav_file, os.path.join(preset_directory, wav_name))
        except Exception as e:
            print(f"Error processing {wav_file}: {e}")
    preset_json['regions'] = key_metadata
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
            preset_json = Helpers.load_preset_json()
            sub_path = os.path.join(bulk_directory, d)
            if os.path.isdir(sub_path):
                process_samples(sub_path, args.output, None, args.sample_rate, args.sample_start)
    else:
        process_samples(args.input, args.output, args.name, args.sample_rate, args.sample_start)

