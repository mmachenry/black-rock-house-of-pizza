# Rings the phone when it's on the hook. Silences the ringer when off hook.

import RPi.GPIO as GPIO
from time import sleep

RING_MODE_PIN = 25
SWITCH_HOOK_PIN = 5

GPIO.setmode(GPIO.BCM)
GPIO.setup(RING_MODE_PIN, GPIO.OUT)
GPIO.setup(SWITCH_HOOK_PIN, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

GPIO.output(RING_MODE_PIN, 0)

last_switch_hook_read = GPIO.input(SWITCH_HOOK_PIN)

try:
    while True:
        switch_hook_read = GPIO.input(SWITCH_HOOK_PIN)

        if switch_hook_read != last_switch_hook_read:
            last_switch_hook_read = switch_hook_read
            if switch_hook_read:
                print "Phone is off da' hook!"
            else:
                print "Phone is on hook."

        if switch_hook_read:
            GPIO.output(RING_MODE_PIN, 0)
	else:
            GPIO.output(RING_MODE_PIN, 1)

        sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()

