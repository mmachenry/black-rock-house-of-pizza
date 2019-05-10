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

  def answer_incoming_call(self, host):
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
        '-c', host                          # remote seren IP address
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

class CallListener(Thread):
  def __init__(self, seren, hosts, port):
    self.seren = seren
    self.hosts = hosts
    self.port = port
    self.context = zmq.Context()
    self.socket = context.socket(zmq.SUB)
    super(name='Call Listener')

  def run(self):
    for host in self.hosts:
      self.socket.connect ("tcp://%s:%s" % (host, self.port))
    self.socket.setsockopt(zmq.SUBSCRIBE, config['Default']['Name'])
    while True:
      message_data = socket.recv().split()
      printDebug("Call Listener got: %s" % message_data)
      (topic, message) = message_data.split()
      if not self.seren.is_call_in_progress():
        self.seren.answer_incoming_call(message)

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
          (ready_to_read, ready_to_write, in_error) = select.select([], [tcp_client], [], global_config['TCP']['ListenDuration'])
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
  call_listener = CallListener(
    seren = seren,
    hosts = [config['Default']['RemoteIP']],
    post = global_config['TCP']['Port'])
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
