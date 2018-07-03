#!/usr/bin/env python

import RPi.GPIO as GPIO
import os, select, signal, socket, subprocess, sys, threading, time

# GPIO pin constants
OFF_HOOK_PIN = 5
RING_MODE_PIN = 25

# Seren constants
PHONE_IP = '192.168.0.102'

# TCP server constants
TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1
LISTEN_DURATION = 0.1
SHOULD_RING_MESSAGE = '1'

# Phone constants
RING_DURATION = 4

# Thread constants
FREE_UP_DURATION = 0.1

# Global variables
call_in_progress = False
ring_for_count = 0
seren_pid = None

# GPIO initialization
GPIO.setmode(GPIO.BCM)
GPIO.setup(OFF_HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(RING_MODE_PIN, GPIO.OUT)

# Start or stop a seren call
def serenCall():
	if not call_in_progress and GPIO.input(OFF_HOOK_PIN):
		print 'Initiating seren call'

		# Stop ringing immediately
		GPIO.ouput(RING_MODE_PIN, GPIO.LOW)
		ring_for_count = 0

		# Start the call
		call_in_progress = True
		seren_pid = subprocess.Popen(['seren', '-N', '-c', PHONE_IP]).pid
	elif call_in_progress and not GPIO.input(OFF_HOOK_PIN)
		print 'Terminating seren call'
		call_in_progress = False
		os.kill(seren_pid, signal.SIGTERM)

	# Cede control to another thread
	time.sleep(FREE_UP_DURATION)

# Set the GPIO pin to ring or not ring the phone according to
# the count
def ringThePhone():
	if ring_for_count > 0 and not call_in_progress:
		print 'Ringing the phone'
		GPIO.output(RING_MODE_PIN, GPIO.HIGH)
		ring_for_count = ring_for_count - 1
		time.sleep(RING_DURATION)
	else:
		GPIO.output(RING_MODE_PIN, GPIO.LOW)
		time.sleep(FREE_UP_DURATION)

# Initiate the TCP socket to listen for calls
def listenForIncomingCall():
	while True:
		tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		tcp_server.bind((TCP_IP, TCP_PORT))
		tcp_server.setblocking(False) # don't block other threads
		tcp_server.listen()
		while True:
			client_socket = None
			try:
				(ready_to_read, ready_to_write, in_error) = select.select([tcp_server], [], [], LISTEN_DURATION)
				if len(ready_to_read) > 0:
					# If our server is ready to read, then there's an incoming connection to accept
					(client_socket, address) = tcp_server.accept()
					print 'Connected to ', address
					while True:
						# Determine if our client socket is ready to read or in error
						(ready_to_read, ready_to_write, in_error) = select.select([client_socket], [], [], LISTEN_DURATION)
						if len(ready_to_read) > 0:
							# There's data to read
							data = client_socket.recv(BUFFER_SIZE)
							if not data:
								break # ready to read but there's no data -> disconnected
							if data == SHOULD_RING_MESSAGE and not call_in_progress
								 # We got the expected string, so tell the phone ring thread to ring twice
								ring_for_count = 2
						elif len(in_error) > 0:
							# Something is wrong with the client,
							# break out of the loop where we read from it
							break

						# Free up this thread so that another one can go
						time.sleep(FREE_UP_DURATION)

					# If we broke out of the above loop, either:
					#   a) the client disconnected
					#   b) the client died
					# So try to close the connection and re-start the loop
					# that waits for a connection
					try:
						client_socket.shutdown()
						client_socket.close()
					except:
						pass
				elif len(in_error) > 0:
					# Something is wrong with the server, restart it
					try:
						tcp_server.shutdown()
						tcp_server.close()
					except:
						pass
					break
				else:
					time.sleep(FREE_UP_DURATION)
			except:
				# Something is wrong with the server, restart it
				try:
					client_socket.shutdown()
					client_socket.close()
				except:
					pass
				try:
					tcp_server.shutdown()
					tcp_server.close()
				except:
					pass
				break

# Start up the threads
seren_thread = threading.Thread(name='seren', target=serenCall)
ring_thread = threading.Thread(name='ring_da_phone', target=ringThePhone)
tcp_thread = threading.Thread(name='tcp_server', target=listenForIncomingCall)
seren_thread.start()
ring_thread.start()
tcp_thread.start()
