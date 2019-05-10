#!/usr/bin/env python3

import zmq
import sys
import threading
import time

topic = "brhop"
port = "5556"

if len(sys.argv) != 3:
  print("Usage: pub_sub_test.py <host> <message>")
  exit(1)

host = sys.argv[1]
message = sys.argv[2]

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:%s" % port)

#socket.connect("tcp://%s:%s" % (host, port))
#socket.setsockopt(zmq.SUBSCRIBE, topic.encode('ascii'))

def listen():
  while True:
    string = socket.recv()
    topic, messagedata = string.split()
    print("Got message: %s" % messagedata)

def talk():
  while True:
    to_send = "%s %s" % (topic, message)
    socket.send(to_send.encode('ascii'))
    time.sleep(3)

#t = threading.Thread(target=listen())
#t.start()
talk()
