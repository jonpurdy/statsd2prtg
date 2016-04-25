#!/usr/bin/env python

import requests	# HTTP requests
import socket	# for udp
import select	# for udp
import re 		# for splitting strings with multiple delimeters
import sys		# for sys.exit
import json 	# dealing with json
from time import sleep

__version__ = '0.1'

UDP_IP		 		= "127.0.0.1"					# interface to listen on
UDP_PORT	 		= 8125							# port to listen on

PRTG_PROBE_ADDRESS	= "192.168.22.100:5050"
PRTG_TOKEN			= "0CAB07F4-9DBC-49CA-BCC0-BE21C86721B9"

HTTP_SERVER			= "http://httpbin.org/post"		# server to post data to
#HTTP_SERVER			= "http://%s/%s" % (PRTG_PROBE_ADDRESS, PRTG_TOKEN)		# server to post data to

POST_INTERVAL		= 5								# seconds

DO_POST				= True
DEBUG_ALL			= False

def main():

	'''
	Initialize the UDP server
	Create a bucket to hold these stats
	'''
	sock = socket.socket(socket.AF_INET, # Internet
						 socket.SOCK_DGRAM) # UDP
	sock.bind((UDP_IP, UDP_PORT))

	my_bucket = Stats_Bucket()
	

	'''
	Every UDP packet gets converted and sent into a bucket
	'''
	while True:
		data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
		print("Data received: %s\n" % data) if DEBUG_ALL else 0

		'''
		Separate the stacked packets
		'''
		separated = statsd_separate_packets(data.decode('UTF-8'))
		print("Separated: %s\n" % separated) if DEBUG_ALL else 0

		for item in separated:
			#print(item) if DEBUG_ALL else 0
			my_bucket.add(item)

		# x = 0
		# while x < 10:
		# 	x += 1
		# 	print(x)
		# 	sleep(1)		

		my_bucket.show()


class Stats_Bucket(object):
	''' Collects statsd metrics for specified time period.
	'''
	# def __init__(self):
	# 	self.name = name

	''' Two separate dictionaries for packets by count and by time (milliseconds)
	'''
	by_count	= {}
	by_time		= {}

	def add(self, packet):
		channel, value, unit = self.parse(packet)

		if unit == 'c':
			if channel not in self.by_count:
				self.by_count[channel] = 0
			self.by_count[channel] += value
		elif unit == "ms":
			if channel not in self.by_time:
				self.by_time[channel] = 0
			self.by_time[channel] += value
		else:
			print("Unit is not c or ms.")
		return 0

	def parse(self, packet):
		packet_as_list = packet.split(":")
		channel = packet_as_list[0]
		value = int(packet_as_list[1].split("|")[0])
		unit = packet_as_list[1].split("|")[1]
		return channel, value, unit

	def show(self):
		print(self.by_count)
		print(self.by_time)

	def clear():
		by_count.clear()
		by_time.clear()

# def udp_receive():
# 	'''
# 	Receives UDP on localhost and the specified port.
# 	Send using netcat:
# 	nc localhost 8125
# 	'''

# 	sock = socket.socket(socket.AF_INET, # Internet
# 						 socket.SOCK_DGRAM) # UDP
# 	sock.bind((UDP_IP, UDP_PORT))

# 	while True:
# 		data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
# 		json_data = statsd_convert_to_json(data.decode('UTF-8'))
# 		http_post(json_data) if DO_POST else 0


def statsd_separate_packets(statsd_data):
	'''
	Reassembled_list stores the reassembled packets
	- packet_string is used in the loop for each individual packet
	- the incoming stacked packets get split on the period
	- each list item then gets appended to packet_string
	- if the list item contains a pipe | the packet_string is added to 
	  reassembled list, then packet_string is reset

	There is probably a faster way to do this with regex.
	'''
	reassembled_list = []
	split_statsd_data = statsd_data.split(".")
	packet_string = ""					
	for item in split_statsd_data:
		packet_string += item
		if "|" in item:
			reassembled_list.append(packet_string)
			packet_string = ""
		else:
			packet_string += "."
	print(reassembled_list) if DEBUG_ALL else 0

	return reassembled_list

# def convert_to_json():

# 		'''
# 	We'll first create json_string, which is the basic PRTG JSON format.
# 	Then split each item in reassembled_list, add to a new dictionary, then
# 	append that dictionary to the existing PRTG JSON structure.

# 	Each statsd metric name contains two or three levels:
# 	eg. rhWorker.runOnce, rh.dialogueTracker.internalContinue
# 	PRTG can't read that anyway, so we'll just pass in the entire string
# 	'''
# 	json_string = '{"prtg": {"result": [{"channel": "name","value": "1","unit": "Count"}]}}'
# 	json_data = json.loads(json_string)

# 	for item in reassembled_list:
# 		item_as_list = item.split(":")
# 		item_dict = {}
# 		item_dict["channel"] = item_as_list[0]
# 		item_dict["value"] = item_as_list[1].split("|")[0]
# 		item_dict["unit"] = item_as_list[1].split("|")[1]
# 		json_data["prtg"]["result"].append(item_dict)

# 	return json_data

def http_post(payload):
	'''
	Takes a payload and posts it to the HTTP_SERVER server.
	From PRTG: "Note: Postdata has to be application/x-www-form-urlencoded"
	'''

	print("payload: %s" % payload)
	#payload = {'key1': 'value1', 'key2': 'value2'}
	r = requests.post(HTTP_SERVER, data = json.dumps(payload))
	
	print(r.text)

if __name__ == '__main__':
	main()