#!/usr/bin/env python

import RPi.GPIO as GPIO
from configparser import ConfigParser
import os, select, signal, socket, subprocess, sys, threading, time

config = ConfigParser()
config.read('base.ini')

global_config = ConfigParser()
global_config.read('global.ini')

# Global variables
call_in_progress = False
call_initiated = False
incoming_call_detected = False
remaining_rings = 0

# GPIO initialization
GPIO.setmode(GPIO.BCM)
GPIO.setup(config['Default']['OffHookPin'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(config['Default']['RingModePin'], GPIO.OUT)

def detectIncomingCall():
	while True:
		tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		tcp_server.bind(('127.0.0.1', global_config['TCP']['Port']))
		tcp_server.setblocking(False) # don't block other threads
		tcp_server.listen()

		tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_client.setblocking(False)
    tcp_client.connect(config['Default']['RemoteIP'], global_config['TCP']['Port'])


class SerenProcess:
	def __init__(self):
		self.pid = None

	def start_new_call(self):
		if self.pid is None:
			raise Exception('Attempt to start new call while call in progress')
		else:
			self.pid = subprocess.Popen([
				'/home/pi/seren/seren',
				'-N',                            # disable ncurses interface
				'-S',                            # disable STUN
				'-n', config['Default']['Name'], # nickname
				'-d', 'plughw:1,0',              # playback device
				'-D', 'plughw:1,0',              # capture device
				'-a',                            # auto-accept calls
				'-C', 0                          # lowest complexity
			]).pid

	def answer_incoming_call(self):
		if self.pid is None:
			raise Exception('Attempt to answer incoming call while call in progress')
		else:
			self.pid = subprocess.Popen([
				'/home/pi/seren/seren',
				'-N',                               # disable ncurses interface
				'-S',                               # disable STUN
				'-n', config['Default']['Name'],    # nickname
				'-d', 'plughw:1,0',                 # playback device
				'-D', 'plughw:1,0',                 # capture device
				'-a',                               # auto-accept calls
				'-C', 0,                            # lowest complexity
				'-c', config['Default']['RemoteIP'] # remote seren IP address
			]).pid

	def hang_up(self):
		if self.pid is None:
			raise Exception('Attempt to hang up non-existent call')
		else:
			os.kill(self.pid, signal.SIGTERM)
			self.pid = None

	def is_call_in_progress():
		return not self.pid is None

class CallListener:
	def __init__(self):
		self.internal_thread = None
		self.incoming_call_detected = False

	def start(self):
		if self.internal_thread:
			raise Exception('Do not start twice')
		else:
			self.internal_thread = threading.Thread(name='Call Listener', target=self.__run__)
			self.internal_thread.start()

	def __run__(self):
		while True:
			tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			tcp_server.bind(('127.0.0.1', global_config['TCP']['Port']))
			tcp_server.setblocking(False) # don't block other threads
			tcp_server.listen()
			while True:
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
								data = client_socket.recv(1)
								if not data:
									break # ready to read but there's no data -> disconnected
								elif data == global_config['TCP']['ShouldRingMessage']
									 # We got the expected string, so we've detected a call
									self.incoming_call_detected = True
								else:
									self.incoming_call_detected = False
							elif len(in_error) > 0:
								# Something is wrong with the client,
								# break out of the loop where we read from it
								break

							# Free up this thread so that another one can go
							time.sleep(global_config['General']['FreeUpDuration'])

						# If we broke out of the above loop, either:
						#   a) the client disconnected
						#   b) the client died
						# So try to close the connection and re-start the loop
						# that waits for a connection
						self.incoming_call_detected = False
						try:
							client_socket.shutdown()
							client_socket.close()
						except:
							pass
					elif len(in_error) > 0:
						# Something is wrong with the server, restart it
						self.incoming_call_detected = False
						try:
							tcp_server.shutdown()
							tcp_server.close()
						except:
							pass
						break
					else:
						time.sleep(global_config['General']['FreeUpDuration'])
				except:
					# Something is wrong with the server, restart it
					self.incoming_call_detected = False
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

	def is_call_available(self):
		return self.incoming_call_detected

def main():
	seren = SerenProcess()
	call_listener = CallListener()
	call_maker = CallMaker()
	call_listener.start()
	call_maker.start()
	while True:
		if seren.is_call_in_progress():
			if not GPIO.input(config['Default']['OffHookPin']):
				seren.hang_up()
		else:
			if GPIO.input(config['Default']['OffHookPin']):
				if call_listener.is_call_available():
					seren.answer_incoming_call()
				else:
					seren.start_new_call()
					call_maker.set_should_call(True)
			else:
				if call_listener.is_call_available():
					ring_the_phone()

	while True:
		if call_in_progress:
			if not GPIO.input(config['Default']['OffHookPin']):
				# End the call
				print 'Disconnecting seren call'
				call_in_progress = False
				call_initiated = False
				os.kill(seren_pid, signal.SIGTERM)
		elif incoming_call_detected:
			if GPIO.input(config['Default']['OffHookPin']):
				# Connect to the call
				call_in_progress = True
				print 'Connecting to seren call'
				seren_pid = subprocess.Popen([
					'/home/pi/seren/seren',
					'-N',                               # disable ncurses interface
					'-S',                               # disable STUN
					'-n', config['Default']['Name'],    # nickname
					'-d', 'plughw:1,0',                 # playback device
					'-D', 'plughw:1,0',                 # capture device
					'-a',                               # auto-accept calls
					'-C', 0,                            # lowest complexity
					'-c', config['Default']['RemoteIP'] # remote seren IP address
				]).pid
		elif GPIO.input(config['Default']['OffHookPin']):
			# Create a new call
			print 'Starting seren call'
			call_in_progress = True
			call_initiated = True
			seren_pid = subprocess.Popen([
				'/home/pi/seren/seren',
				'-N',                            # disable ncurses interface
				'-S',                            # disable STUN
				'-n', config['Default']['Name'], # nickname
				'-d', 'plughw:1,0',              # playback device
				'-D', 'plughw:1,0',              # capture device
				'-a',                            # auto-accept calls
				'-C', 0                          # lowest complexity
			]).pid

		# Cede control to another thread
		time.sleep(global_config['General']['FreeUpDuration'])

def ringTheOtherPhone():
	while True:
		tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_client.setblocking(False)
    tcp_client.connect(config['Default']['RemoteIP'], global_config['TCP']['Port'])
		while True:
			message = global_config['TCP']['ShouldRingMessage'] if call_initiated else global_config['TCP']['OKMessage']
			try:
				(ready_to_read, ready_to_write, in_error) = select.select([], [tcp_client], [], LISTEN_DURATION)



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

