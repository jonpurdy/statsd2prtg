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
	MESSAGE_LIST = ["rh.sccp.in:1|c.rh.dialogueTracker.internalContinue:1|c.rh.dialogueDatabase.findToInternal:3|ms.rh.sccp.out:1|c.rh.toInternal:1|c.rhWorker.runOnce:6|ms"]

	MESSAGE_LIST = ["rh.sccp.in:1|c\nrh.dialogueTracker.internalContinue:1|c\nrh.dialogueDatabase.findToInternal:3|ms\nrh.sccp.out:1|c\nrh.toInternal:1|c\nrhWorker.runOnce:7|ms",
		"rh.sccp.in:1|c\nrh.dialogueTracker.externalEnd:1|c\nrh.dialogueDatabase.findToExternal:1|ms\nrh.sccp.out:1|c\nrh.toExternal:1|c\nrhWorker.runOnce:3|ms",
		"rh.sccp.in:1|c\nrh.dialogueTracker.internalContinue:1|c\nrh.dialogueDatabase.findToInternal:2|ms\nrh.sccp.out:1|c\nrh.toInternal:1|c\nrhWorker.runOnce:5|ms",
		"rh.sccp.in:1|c\nrh.dialogueTracker.internalContinue:1|c\nrh.dialogueDatabase.findToInternal:3|ms\nrh.sccp.out:1|c\nrh.toInternal:1|c\nrhWorker.runOnce:7|ms",
		"rh.sccp.in:1|c\nrh.dialogueTracker.internalBegin:1|c\nrh.dialogueDatabase.findToInternalDuplicate:2|ms\nrh.imsiMapping:1|ms\nrh.sccp.in:1|c\nrh.dialogueTracker.internalContinue:1|c\nrh.dialogueDatabase.findToInternal:4|ms\nrh.sccp.out:1|c\nrh.toInternal:1|c\nrhWorker.runOnce:9|ms",
		"rh.vlrMsisdnMapping:31|ms\nrh.sccp.out:1|c\nrh.toInternal:1|c\nrhWorker.runOnce:25|ms",
		"rh.sccp.in:1|c\nrh.dialogueTracker.externalEnd:1|c\nrh.dialogueDatabase.findToExternal:2|ms\nrh.sccp.out:1|c\nrh.toExternal:1|c\nrhWorker.runOnce:4|ms"]

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

if __name__ == '__main__':
	main()