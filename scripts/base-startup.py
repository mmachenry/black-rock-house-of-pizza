#!/usr/bin/env python

import RPi.GPIO as GPIO
from time import sleep

LED_PIN = 26

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

for x in range(5):
  GPIO.output(LED_PIN, GPIO.HIGH)
  sleep(0.5)
  GPIO.output(LED_PIN, GPIO.LOW)
  sleep(0.5)

GPIO.cleanup()
