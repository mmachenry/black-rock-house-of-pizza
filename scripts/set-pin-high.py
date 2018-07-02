import RPi.GPIO as GPIO
from time import sleep
from sys import argv

GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.OUT)
GPIO.output(25, 1)
sleep(float(argv[1]))
GPIO.cleanup()

