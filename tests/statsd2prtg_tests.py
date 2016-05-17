from nose.tools import *
import statsd2prtg

def setup():
    print("SETUP!")

def test_check_math():
	
	UDP_IP = "127.0.0.1"
	UDP_PORT = 8125
	from time import sleep
	import socket
	import select
	import threading
	import random

	# After running the next one:
	# rh.sccp.in 							3
	# rh.dialogueTracker.internalContinue	1
	# rh.dialogueTracker.externalEnd		1
	# rh.dialogueDatabase.findToExternal	3ms + 4ms = 7ms/2 = 3.5ms

	MESSAGE_LIST = ["rh.sccp.in:1|c.rh.dialogueTracker.internalContinue:1|c",
					"rh.sccp.in:1|c.rh.dialogueTracker.externalEnd:1|c",
					"rh.dialogueDatabase.findToExternal:3|ms",
					"rh.sccp.in:1|c.rh.dialogueDatabase.findToExternal:4|ms"]

	while True:

		for MESSAGE in MESSAGE_LIST:
			print()
			print("UDP target IP:", UDP_IP)
			print("UDP target port:", UDP_PORT)
			print(MESSAGE)

			sock = socket.socket(socket.AF_INET, # Internet
								 socket.SOCK_DGRAM) # UDP
			sock.sendto(bytes(MESSAGE, "utf-8"), (UDP_IP, UDP_PORT))
			interval = random.uniform(0.1, 1)
			print("Sending next in %s seconds..." % round(interval, 1))
			sleep(interval)


def test_teardown():
    print("TEAR DOWN!")

def test_basic():
    print("I RAN!")

#def test_stats_convert_to_json():
#    statsd_data = 