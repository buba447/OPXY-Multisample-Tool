import os
import time
import argparse
import sounddevice as sd
import soundfile as sf
from mido import Message
import mido
import sys
import Helpers
import json


def list_audio_devices():
    """List all available audio devices."""
    return [d for d in sd.query_devices() if d['max_input_channels'] > 0]


def print_audio_devices():
    """Print available audio devices."""
    devices = "Audio Devices:\n"
    device_id = 0
    for d in list_audio_devices():
        name = d['name']
        in_count = d['max_input_channels']
        devices += f'  {device_id}: {name} ({in_count} in)\n'
        device_id += 1
    if device_id == 0:
        devices += '  No Audio Devices Found!\n'
    print(devices)


def list_midi_devices(virtual_enabled=False):
    """List all available midi devices."""
    devices = []
    if virtual_enabled:
        devices.append('Create Virtual MIDI Device (Mac Only)')
    devices.extend(mido.get_output_names())
    return devices


def print_midi_devices(virtual_enabled=False):
    devices = "MIDI Devices:\n"
    device_id = 0
    for name in list_midi_devices(virtual_enabled=virtual_enabled):
        devices += f'  {device_id}: {name}\n'
        device_id += 1
    if device_id == 0:
        devices += '  No Midi Devices Found!\n'
    print(devices)


def record_samples(
    midi_device_index,
    midi_channel,
    audio_device_index,
    audio_channels,
    start_key,
    end_key,
    interval,
    record_duration,
    preset_name,
    output_directory,
    samplerate=44100,
    note_velocity=112,
    record_delay=0,
    sustain_duration=None,
    midi_output=None,
    loop_start=None,
    loop_end=None,
    loop_crossfade=0
):
    if midi_output is None:
        midi_output = mido.open_output(list_midi_devices()[midi_device_index])

    if sustain_duration is None:
        sustain_duration = record_duration * 0.33

    if loop_start:
        loop_start = loop_start * samplerate
    else:
        loop_start = 0

    if loop_end:
        loop_end = loop_end * samplerate
    else:
        loop_end = sustain_duration * samplerate

    loop_crossfade = loop_crossfade * samplerate

    record_delay = max(0, record_delay)

    audo_device = list_audio_devices()[audio_device_index]['index']

    preset_name = Helpers.sanitize_name(preset_name)
    output_directory = os.path.join(output_directory, f'{preset_name}.preset')
    try:
        os.makedirs(output_directory, exist_ok=True)
    except:
        print("ERROR: Unable to create directory.")
        return

    preset_json = Helpers.load_preset_json()

    last_key = 0
    for key in range(start_key, end_key+1, interval):
        base_name = f"{preset_name}-{key:03}"
        filename = f"{base_name}.wav"
        output_file = os.path.join(output_directory, filename)
        print(f'Recording Note {key} to {output_file}')

        note_on = False
        note_off = False
        if record_delay > 0:
            midi_output.send(Message('note_on', channel=midi_channel, note=key, velocity=note_velocity))
            note_on = True
            if record_delay > sustain_duration:
                time.sleep(sustain_duration)
                midi_output.send(Message('note_off', channel=midi_channel, note=key, velocity=0))
                note_off = True
                time.sleep(record_delay - sustain_duration)
            else:
                time.sleep(record_delay)
            sustain_duration = sustain_duration - record_delay

        audio_data = sd.rec(
            int(record_duration * samplerate),
            samplerate=samplerate,
            device=audo_device,
            dtype='float32',
            mapping=audio_channels
        )
        if note_on is False:
            midi_output.send(Message('note_on', channel=midi_channel, note=key, velocity=note_velocity))

        if note_off is False:
            time.sleep(sustain_duration)
            midi_output.send(Message('note_off', channel=midi_channel, note=key, velocity=0))

        sd.wait()  # Wait until recording is finished

        sf.write(output_file, audio_data, samplerate)
        metadata = Helpers.sample_metadata(
            frame_count=samplerate*record_duration,
            output_basename=filename,
            hi_key=key,
            low_key=last_key,
            center=key,
            loop_crossfade=loop_crossfade,
            loop_start=loop_start,
            loop_end=loop_end
        )

        last_key = key + 1
        preset_json['regions'].append(metadata)

    json_file = os.path.join(output_directory, 'patch.json')
    # Write JSON file
    with open(json_file, "w") as f:
        json.dump(preset_json, f)
    print(f'Generated Patch! You may now copy {preset_name}.preset to the OPXY under \"presets\\PRESET GROUP\\')
    print(output_directory)


def start_interactive():
    print('Welcome to the Multisample Tool! \nFollow the prompts to generate a multisample for your OPXY.\n\n')

    # MIDI DEVICE SETUP
    print_midi_devices(virtual_enabled=True)
    midi_device_index = int(input("Please select a MIDI output device: "))
    midi_output = None
    if midi_device_index == 0:
        midi_output = mido.open_output(name="Virtual Multisampler", virtual=True)
        _ = input("Select \"Virtual Multisampler\" as the midi input device in your DAW. Press Enter when ready.")
    else:
        midi_device_index -= 1
    print("\n")
    midi_channel = int(input("MIDI Output Channel (1-16): ")) - 1
    print("\n")

    # AUDIO DEVICE
    print_audio_devices()
    audio_device_index = int(input("Please select an audio input device: "))
    print("\n")

    audio_device = list_audio_devices()[audio_device_index]
    if audio_device['max_input_channels'] > 2:
        channel_inputs = input("Specify two input channels, separated by comma: ").split(',')
        print("\n")
        audio_channels = (int(channel_inputs[0]), int(channel_inputs[1]))
    else:
        audio_channels = (1, 2) if audio_device['max_input_channels'] == 2 else (1, 1)

    print("Record Settings")
    start_key = input("Enter start key (Midi Number 0-127 or C1, Gb3, E#2): ")
    if start_key.isnumeric():
        start_key = int(start_key)
    else:
        start_key = Helpers.note_string_to_midi_value(start_key)

    end_key = input("Enter end key (Midi Number 0-127 or C1, Gb3, E#2): ")
    if end_key.isnumeric():
        end_key = int(end_key)
    else:
        end_key = Helpers.note_string_to_midi_value(end_key)
    interval = int(input("How many semi-tones between samples (1 will record a sample for every key): "))
    record_duration = float(input("How many seconds to record each note (EG: 1.2): "))
    print("\n")
    adv_enabaled = input("Advanced Options (y/n)?")
    print("\n")

    note_velocity = 112
    record_delay = 0
    sustain_duration = None
    loop_start = None
    loop_end = None
    loop_crossfade = 0

    if adv_enabaled.lower().startswith('y'):
        record_delay = float(input("Record delay duration in seconds (EG: 1.2): "))
        sustain_duration = float(input("Sustain duration in seconds (EG: 1.2): "))
        note_velocity = int(input("Note Velocity (1-127): "))

        loop_start = float(input("Loop start in seconds (EG: 1.2): "))
        loop_end = float(input("Loop end in seconds (EG: 1.2): "))
        loop_crossfade = float(input("Loop crossfade in seconds (EG: 1.2): "))
        print("\n")
        #
        # |///////|  Midi Sustain Time
        # |   |////////|   Loop Point
        # |   /|      |\   Crossfade
        # |----------------------| 3.3 Record Time

    print("Output Settings")
    preset_name = input("Preset Name:")
    output_directory = input("Output Directory:")

    _ = input("Press enter when you are ready to record.")

    record_samples(
        midi_device_index=midi_device_index,
        midi_channel=midi_channel,
        audio_device_index=audio_device_index,
        audio_channels=audio_channels,
        start_key=start_key,
        end_key=end_key,
        interval=interval,
        record_duration=record_duration,
        preset_name=preset_name,
        output_directory=output_directory,
        midi_output=midi_output,
        note_velocity=note_velocity,
        record_delay=record_delay,
        sustain_duration=sustain_duration,
        loop_start=loop_start,
        loop_end=loop_end,
        loop_crossfade=loop_crossfade
    )

if __name__ == "__main__":
    start_interactive()



