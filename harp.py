#!/usr/bin/env python3

# Simple test of the capacitive touch sensor library mpr121

# Will print out a message when any of the 12 capacitive touch inputs of the board are touched.
# Open the serial REPL after running to see the output.

import adafruit_mpr121
import board
import busio
import mido
import rtmidi
import time
import _thread

print(board.SCL)
print(board.SDA)

i2c = busio.I2C(board.SCL, board.SDA)

ON_PRESS = "on_press"
ON_RELEASE = "on_release"
TRIGGER_BEHAVIOR = ON_RELEASE

SENSOR_ADDRESSES = [0x5A, 0x5B, 0x5C]
# SENSOR_ADDRESSES = [0x5A, 0x5B]
# SENSOR_ADDRESSES = [0x5A]
mpr121s = [adafruit_mpr121.MPR121(i2c, address=address) for address in SENSOR_ADDRESSES]
SENSORS_PER_CHIP = 12
SEMITONES_PER_OCTAVE = 12
SENSOR_COUNT = len(mpr121s) * SENSORS_PER_CHIP
TICK_SECONDS = 0.01

print("Available MIDI outputs:")
print(mido.get_output_names())
port_name = mido.get_output_names()[2]
print("Using port:", port_name)
port = mido.open_output(port_name)
port.panic()
port.send(mido.Message('program_change', program=24))

CHROMATIC =  list(range(12))
HEPTATONIC = [0,2,4,5,7,9,11]
PENTATONIC = [0, 2, 4, 7, 9]
MAJOR      = [0, 4, 7]
MAJOR_ADD2 = [0, 2, 4, 7]
SUS4       = [0, 5, 7]
MINOR      = [0, 3, 7]

def chord_on_root(chord, root):
    return [(x+root)%12 for x in chord]

def degree_in_scale(i, scale, root=0):
    scale_length = len(scale)
    if i < scale_length:
        return scale[i] + root
    return degree_in_scale(i-scale_length, scale, root=root) + SEMITONES_PER_OCTAVE

def calibrate_sensors():
    global sensor_trigger_levels

    sensor_readings_over_time = [[] for i in range(SENSOR_COUNT)]
    for i in range(50):
        time.sleep(TICK_SECONDS)
        for j, value in enumerate(get_filtered_data()):
            sensor_readings_over_time[j].append(value)
    sensor_trigger_levels = [min(sensor_readings) - 5 for sensor_readings in sensor_readings_over_time]

def get_filtered_data():
    return [mpr121.filtered_data(x) for mpr121 in mpr121s for x in range(SENSORS_PER_CHIP)]

def get_touch_data():
    return [touch for mpr121 in mpr121s for touch in reversed(mpr121.touched_pins)]

def clear_notes_older_than(time_last_played, threshold):
    current = time.time()
    for i, time_played in enumerate(time_last_played):
        if current - time_played > threshold:
            port.send(mido.Message('note_off', note=i))

def status_string_for_sensor(i, filtered_data):
    note = sensor_to_midi_note[i]
    line = list(" "*10 + "." + " "*10)
    if note%SEMITONES_PER_OCTAVE in current_chord:
        name = root_to_name[note % SEMITONES_PER_OCTAVE]
        line[10] = name
    offset = sensor_trigger_levels[i] - filtered_data[i]
    offset = max(min(offset, 4), -4)
    line[10+offset] = "|"
    line += [str(filtered_data[i]), " / ", str(sensor_trigger_levels[i])]
    return "".join(line)

def loop():
    global last_touched_pins, last_filtered_data, time_last_played
    while True:
        clear_notes_older_than(time_last_played, 4)
        filtered_data = get_filtered_data()
        touched_pins = []
        for i in range(SENSOR_COUNT):
            stdscr.addstr(7+i, 0, status_string_for_sensor(i, filtered_data))
            if filtered_data[i] < sensor_trigger_levels[i]:
                touched_pins.append(i)

            note = sensor_to_midi_note[i]
            if note%SEMITONES_PER_OCTAVE not in current_chord:
                continue

            if TRIGGER_BEHAVIOR == ON_PRESS:
                if i in last_touched_pins:
                    continue
            elif TRIGGER_BEHAVIOR == ON_RELEASE:
                if i in touched_pins or i not in last_touched_pins:
                    continue

            velocity = 127
            port.send(mido.Message('note_off', note=note))
            port.send(mido.Message('note_on', note=note, velocity=velocity))
            time_last_played[note] = time.time()
        last_touched_pins = touched_pins[:]
        stdscr.refresh()
        time.sleep(.01)

# Initializations
root = 48
current_key = 48
sensor_to_midi_note = [degree_in_scale(i, CHROMATIC, root=root) for i in range(SENSOR_COUNT)]
print(sensor_to_midi_note)
time.sleep(2)
last_touched_pins = [False] * 12
last_filtered_data = [500] * 12
time_last_played = [0] * 127
sensor_trigger_levels = []

import curses
stdscr = curses.initscr()
curses.cbreak()
curses.noecho()
stdscr.keypad(1)

stdscr.addstr(0,10,"Calibrating sensors, do not touch!")
stdscr.refresh()
calibrate_sensors()
stdscr.addstr(0,10,"Hit 'q' to quit                  ")
stdscr.refresh()

_thread.start_new_thread(loop, ())

key = ''
key_to_root_and_type = {
    'a': (34, MAJOR), # Bb
    'o': (29, MAJOR), # F
    'e': (36, MAJOR_ADD2), # C add 2
    'u': (31, MAJOR), # G
    'i': (31, SUS4), # G sus4
    ';': (26, MINOR), # D
    'q': (33, MINOR), # A
    'j': (28, MINOR), # E
    'k': (35, MINOR), # B
}

root_to_name = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B']

current_chord = [0,4,7]

while key != ord('Q'):
    key = stdscr.getch()
    stdscr.refresh()
    for k, (r, t) in key_to_root_and_type.items():
        if key == ord(k):
            root = r
            # sensor_to_midi_note = [degree_in_scale(i, t, root=root) for i in range(SENSOR_COUNT)]
            sensor_to_midi_note[0:4] = [root, root+4, root+7, root+12]
            current_chord = chord_on_root(t, root)
            name = root_to_name[r % SEMITONES_PER_OCTAVE]
            stdscr.addstr(4, 20, "Chord: " + name + "    ")
    if key == curses.KEY_UP:
        root += 1
        stdscr.addstr(2, 20, "Up " + str(root))
    elif key == curses.KEY_DOWN:
        root -= 1
        stdscr.addstr(3, 20, "Down " + str(root))

curses.endwin()
