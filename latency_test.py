#!/usr/bin/env python3

# Test of the latency of timidity

# Best latency achieved:
#
# timidity -iA
# .29 seconds
#
#
#
# .082

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
mpr121 = adafruit_mpr121.MPR121(i2c)

print("Available MIDI outputs:")
print(mido.get_output_names())
port_name = mido.get_output_names()[2]
print("Using port:", port_name)
port = mido.open_output(port_name)
port.panic()

last_touched_pins = [False] * 12
play_time = time.time()
latency = .02
historical_times = []
avg_number = 15

def loop():
    global latency
    # Play the note, noting the time
    play_time = time.time()
    port.send(mido.Message('note_off', note=80, velocity=127))
    port.send(mido.Message('note_on', note=80, velocity=127))

    # Wait for user to indicated hearing the note
    input()

    # Compute the time it took
    latency = time.time() - play_time
    historical_times.append(latency)
    avg_over = min(avg_number, len(historical_times))
    latency_avg = sum(historical_times[-avg_over:]) / avg_over
    print(latency_avg)

while True:
    loop()
