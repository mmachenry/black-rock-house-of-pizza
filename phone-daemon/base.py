#!/usr/bin/env python

import RPi.GPIO as GPIO
import os, select, signal, socket, subprocess, sys, threading, time

# GPIO pin constants
OFF_HOOK_PIN = 16
RING_MODE_PIN = 26

# TCP server constants
TCP_IP = '192.168.1.105'
TCP_PORT = 5005
LISTEN_DURATION = 0.1
SHOULD_RING_MESSAGE = '1'
OK_MESSAGE = '0'

# Phone constants
RING_DURATION = 4

# Thread constants
FREE_UP_DURATION = 0.1

# Global variables
call_in_progress = False

# GPIO initialization
GPIO.setmode(GPIO.BCM)
GPIO.setup(OFF_HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(RING_MODE_PIN, GPIO.OUT)

# Initiate the seren server
def seren():
	if not call_in_progress and GPIO.input(OFF_HOOK_PIN):
		print 'Initiating seren call'

		# Stop ringing immediately
		GPIO.ouput(RING_MODE_PIN, GPIO.LOW)
		ring_for_count = 0

		# Start the call
		call_in_progress = True
		seren_pid = subprocess.Popen(['seren', '-NS', '-c', PHONE_IP]).pid
	elif call_in_progress and not GPIO.input(OFF_HOOK_PIN)
		print 'Terminating seren call'
		call_in_progress = False
		os.kill(seren_pid, signal.SIGTERM)

	# Cede control to another thread
	time.sleep(FREE_UP_DURATION)

# Set the GPIO pin to ring or not ring the phone according to
# off-hook detection
def ringThePhone():
  while True:
    # Initiate the socket
    tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_client.setblocking(False)
    tcp_client.connect(TCP_IP, TCP_PORT)

    # Wait for off-hook detection
    while True:
      message = SHOULD_RING_MESSAGE if (GPIO.input(OFF_HOOK_PIN) and not call_in_progress) else OK_MESSAGE
      try:
        (ready_to_read, ready_to_write, in_error) = select.select([], [tcp_client], [], LISTEN_DURATION)
        if len(ready_to_write):
          sent = tcp_client.send(message)
          if sent === 0:
            raise RuntimeError('socket connection broken')
        elif len(in_error):
          raise RuntimeError('socket connection broken')
      except:
        try:
          tcp_client.shutdown()
          tcp_client.close()
        except:
          pass
        break
		  time.sleep(FREE_UP_DURATION)

def

# Start up the threads
#seren_thread = threading.Thread(name='seren', target=serenCall)
#ring_thread = threading.Thread(name='ring_da_phone', target=ringThePhone)
#tcp_thread = threading.Thread(name='tcp_server', target=listenForIncomingCall)
#seren_thread.start()
#ring_thread.start()
#tcp_thread.start()

