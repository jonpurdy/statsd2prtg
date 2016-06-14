#!/usr/bin/env python

from time import sleep

import socket
import select

#import SocketServer
import threading

import random

def main():

	send_test()

def send_test():
	'''
	Sends out data over UDP to localhost and the specified port.
	Receive using netcat:
	nc -u -l 8125
	'''
	UDP_IP = "127.0.0.1"
	UDP_PORT = 8125

	MESSAGE_LIST = ["rh.sccp.in:1|c\nrh.dialogueTracker.internalContinue:1|c\n",
					"rh.sccp.in:1|c\nrh.dialogueTracker.externalEnd:1|c\n",
					"rh.dialogueDatabase.findToExternal:3|ms\n",
					"rh.sccp.in:1|c\nrh.dialogueDatabase.findToExternal:4|ms\n"]

	# After running through that list once:
	# rh.sccp.in 							3
	# rh.dialogueTracker.internalContinue	1
	# rh.dialogueTracker.externalEnd		1
	# rh.dialogueDatabase.findToExternal	3ms + 4ms = 7ms/2 = 3.5ms

	# After running through that list 3x:
	# rh.sccp.in 							9
	# rh.dialogueTracker.internalContinue	3
	# rh.dialogueTracker.externalEnd		3
	# rh.dialogueDatabase.findToExternal	3ms + 4ms + 3ms + 4ms + 3ms +
	#										4ms = 21ms/6 = 3.5ms

	print("Starting in 1 second...")
	sleep(1)

	intervals = [0.25, 0.5, 1]

	for interval in intervals:
		print("Current interval: %s" % interval)

		for MESSAGE in MESSAGE_LIST:
			print(MESSAGE)

			sock = socket.socket(socket.AF_INET, # Internet
								 socket.SOCK_DGRAM) # UDP
			sock.sendto(bytes(MESSAGE, "utf-8"), (UDP_IP, UDP_PORT))
			print("Sending next in %s seconds..." % interval)
			sleep(interval)

if __name__ == '__main__':
	main()