# OPXY Multisample Tool

This script is used to pack a collection of multisamples into an instrument preset for the OPXY.

## Features

- Generates preset JSON for OPXY multisample instrument.
- Properly names files according to OPXY naming standards.
- Packs JSON and Audio Files into the appropriate file structure for OPXY.
- Use the --help flag to display usage information.

## Dependencies

- Python 3 (https://www.python.org/downloads/)
- ffmpeg (https://www.ffmpeg.org)

## Sample Prep

Place your samples in a folder. The naming format for samples follows a format like `Sample Name-[Note Number].wav`
Where the note number is a number from 0-127. With 0 being C-1, 127 being G9 and 60 is Middle C.

Like so:

```
"InputFolder\My Awesome Sample-48.wav"
"InputFolder\My Awesome Sample-60.wav"
"InputFolder\My Awesome Sample-64.wav"
```

Some samples are named with a note and a velocity. `My Awesome Sample-48-127.wav`

The OP-XY does not currently support velocity mappings.
There is no need to rename these. The script will automatically choose the highest velocity for each note.

## Usage

Once your samples are grouped into a folder, open terminal and navigate to this script. 

Execute the script like so:

`python PackSamples.py --input /Path/To/Sample/Directory --output /Path/To/Output/Directory --name "Preset Name"`

_NOTE: Be sure to set your output directory to a different directory from the input!_

_NOTE: The name argument is optional- if a name is not provided then the preset will be inferred from the sample name._

The resulting instrument pack will be placed in the output directory and the audio files will be copied into it.

## Copying onto the XY

_NOTE If you are on a Mac ensure that you download the FieldKit app and run it. This enables the Mac to mount the XY._

It's a good idea to create a new empty project on the OP-XY before copying and to power cycle before and after copying.

Plug in your OP-XY. Press `com` and then `4: mtp`
The OP-XY should then show up as a drive on your computer.

Copy the output into the OPXY 'presets' directory.
Instrument presets can be grouped into a subdirectory one level deep.

```
OPXY\preset\Group Folder\My Awesome Preset.preset
OPXY\preset\Group Folder\My Second Awesome Preset.preset
```

**NOTE After copying samples eject the OP-XY and power cycle the device. For some reason samples don't always load until the device is power cycled.**

Example OPXY
![Output Example](imgs/output.png)

## Advanced Usage

Using the `--bulk` command will automatically pack multiple presets. 

Pass a folder containing multiple subfolders of samples into the bulk command along with an output directory.
The tool will then run the pack command for each subfolder automatically.

## License

MIT License