import zmq
import random
import sys
import time
import threading

port = "5556"
context = zmq.Context()

if len(sys.argv) > 1:
    port =  sys.argv[1]
    int(port)

def server():
  socket = context.socket(zmq.PUB)
  socket.bind("tcp://*:%s" % port)

  while True:
    topic = random.randrange(9999,10005)
    messagedata = random.randrange(1,215) - 80
    print "Server %d %d" % (topic, messagedata)
    socket.send("%d %d" % (topic, messagedata))
    time.sleep(1)

def client():
  print "Collecting updates from weather serves..."
  socket = context.socket(zmq.SUB)
  socket.connect ("tcp://localhost:%s" % port)

  # Subscribe to zipcode, default is NYC, 10001
  topicfilter = "10001"
  socket.setsockopt(zmq.SUBSCRIBE, topicfilter)

  while True:
    string = socket.recv()
    topic, messagedata = string.split()
    print "Client:", topic, messagedata

t = threading.Thread(target=server)
t.start()
t2 = threading.Thread(target=client)
t2.start()
