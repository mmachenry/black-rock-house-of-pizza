#!/usr/bin/env python

import RPi.GPIO as GPIO
from configparser import ConfigParser
import os, select, signal, socket, subprocess, sys, threading, time

config = ConfigParser()
config.read('base.ini')

global_config = ConfigParser()
global_config.read('global.ini')

def printDebug(*args, *kwargs):
  if global_config.getboolean('General', 'Debug'):
    print(*args, *kwargs)

class SerenProcess:
  def __init__(self):
    self.pid = None

  def start_new_call(self):
    printDebug('Starting new call')
    if is_call_in_progress(self):
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
      printDebug('New call started')

  def answer_incoming_call(self):
    printDebug('Answering incoming call')
    if is_call_in_progress(self):
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
      printDebug('Incoming call answered')

  def hang_up(self):
    printDebug('Hanging up')
    if not is_call_in_progress(self):
      raise Exception('Attempt to hang up non-existent call')
    else:
      os.kill(self.pid, signal.SIGTERM)
      self.pid = None
      printDebug('Hung up')

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
      printDebug('Listener creating TCP server')
      tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      tcp_server.bind(('127.0.0.1', global_config['TCP']['Port']))
      tcp_server.setblocking(False) # don't block other threads
      tcp_server.listen()
      printDebug('TCP server is listening')
      while True:
        try:
          (ready_to_read, ready_to_write, in_error) = select.select([tcp_server], [], [], LISTEN_DURATION)
          if len(ready_to_read) > 0:
            # If our server is ready to read, then there's an incoming connection to accept
            printDebug('Server accepting client')
            (client_socket, address) = tcp_server.accept()
            printDebug('Connected to ', address)
            while True:
              # Determine if our client socket is ready to read or in error
              (ready_to_read, ready_to_write, in_error) = select.select([client_socket], [], [], LISTEN_DURATION)
              if len(ready_to_read) > 0:
                # There's data to read
                printDebug('Reading data from client ', address)
                data = client_socket.recv(1)
                if not data:
                  printDebug('Client disconnected ', address)
                  break # ready to read but there's no data -> disconnected
                elif data == global_config['TCP']['ShouldRingMessage']
                  printDebug('Incoming call detected ', address)
                   # We got the expected string, so we've detected a call
                  self.incoming_call_detected = True
                else:
                  printDebug('OK detected ', address)
                  self.incoming_call_detected = False
              elif len(in_error) > 0:
                printDebug('Client in error ', address)
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
            printDebug('Closing connection with ', address)
            self.incoming_call_detected = False
            try:
              client_socket.shutdown()
              client_socket.close()
            except:
              pass
          elif len(in_error) > 0:
            # Something is wrong with the server, restart it
            printDebug('Closing listening server')
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
          printDebug('Closing listening server')
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

class CallMaker:
  def __init__(self):
    self.internal_thread = None
    self.should_call = False

  def start(self):
    if self.internal_thread:
      raise Exception('Do not start twice')
    else:
      self.internal_thread = threading.Thread(name='Call Maker', target=self.__run__)
      self.internal_thread.start()

  def set_should_call(self, should_call):
    self.should_call = should_call

  def __run__(self):
    while True:
      # Initiate the socket
      printDebug('Initializing call maker TCP client')
      tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      tcp_client.setblocking(False)
      tcp_client.connect(config['Default']['RemoteIP'], global_config['TCP']['Port'])
      printDebug('Call maker connected to ', config['Default']['RemoteIP'])

      while True:
        # Send either SHOULD_RING or OK, depending on state
        message = global_config['TCP']['ShouldRingMessage'] if (self.should_call) else global_config['TCP']['OKMessage']
        printDebug('Sending message ', message)
        try:
          (ready_to_read, ready_to_write, in_error) = select.select([], [tcp_client], [], LISTEN_DURATION)
          if len(ready_to_write):
            sent = tcp_client.send(message)
            if sent === 0:
              raise RuntimeError('socket connection broken')
            printDebug('Message sent')
          elif len(in_error):
            raise RuntimeError('socket connection broken')
        except:
          # Attempt to close the socket
          try:
            tcp_client.shutdown()
            tcp_client.close()
          except:
            # We did our best
            pass
          # Break out of the inner infinite loop
          break
        time.sleep(global_config['General']['FreeUpDuration'])

class PhoneRinger:
  def __init__(self):
    self.internal_thread = None
    self.should_ring = False

    # GPIO initialization
    printDebug('RingModePin set to ', config['Default']['RingModePin'])
    GPIO.setup(config['Default']['RingModePin'], GPIO.OUT)

  def start(self):
    if self.internal_thread:
      raise Exception('Do not start twice')
    else:
      self.internal_thread = threading.Thread(name='Phone Ringer', target=self.__run__)
      self.internal_thread.start()

  def __run__(self):
    while True:
      if self.should_ring:
        printDebug('Setting RingModePin high')
        GPIO.output(config['Default']['RingModePin'], GPIO.HIGH)
        time.sleep(global_config['Phone']['RingDuration'])
      else:
        printDebug('Setting RingModePin low')
        GPIO.output(config['Default']['RingModePin'], GPIO.LOW)
        time.sleep(global_config['General']['FreeUpDuration'])

  def set_should_ring(self, should_ring):
    self.should_ring = should_ring

def main():
  GPIO.setmode(GPIO.BCM)
  seren = SerenProcess()
  call_listener = CallListener()
  call_maker = CallMaker()
  phone_ringer = PhoneRinger()
  call_listener.start()
  call_maker.start()
  phone_ringer.start()
  GPIO.setup(config['Default']['OffHookPin'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
  printDebug('OffHookPin set to ', config['Default']['OffHookPin'])
  while True:
    if seren.is_call_in_progress():
      phone_ringer.set_should_ring(False)
      if not GPIO.input(config['Default']['OffHookPin']):
        seren.hang_up()
        call_maker.set_should_call(False)
    else:
      if GPIO.input(config['Default']['OffHookPin']):
        # Phone is off the hook, so:
        phone_ringer.set_should_call(False)
        if call_listener.is_call_available():
          seren.answer_incoming_call()
          call_maker.set_should_call(False)
        else:
          seren.start_new_call()
          call_maker.set_should_call(True)
      else:
        if call_listener.is_call_available():
          phone_ringer.set_should_ring(True)

    time.sleep(global_config['General']['FreeUpDuration'])
