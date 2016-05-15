#!/usr/bin/env python

import logging
import sys      # for sys.exit
import json     # dealing with json
from time import sleep
import threading
import socketserver
import requests # HTTP requests

__version__ = '0.2'

UDP_IP = "127.0.0.1" # interface to listen on
UDP_PORT = 8125 # port to listen on
PRTG_PROBE_ADDRESS = "192.168.22.100:5050"
PRTG_TOKEN = "0CAB07F4-9DBC-49CA-BCC0-BE21C86721B9"
HTTP_SERVER = "http://httpbin.org/post" # server to post data to
HTTP_SERVER = "http://%s/%s" % (PRTG_PROBE_ADDRESS, PRTG_TOKEN) # server to post data to
POST_INTERVAL = 10 # seconds
DO_POST = True

def main():

    # pylint: disable=C0103

    logging.basicConfig(level=logging.DEBUG)

    # Initialize the UDP server

    server = ThreadedUDPServer((UDP_IP, UDP_PORT), ThreadedUDPRequestHandler)
    # ip_address, port = server.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    udp_server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    udp_server_thread.setDaemon(False)
    udp_server_thread.start()

    logging.debug("Server loop running in thread: %s", udp_server_thread.name)

    global my_bucket
    my_bucket = Stats_Bucket()

    prtg_collector_thread = threading.Thread(target=prtg_collector)
    prtg_collector_thread.start()

def prtg_collector():
    """Creates a bucket to collect statsd stats. Every x seconds,
    initializes a post to http thread, passes the existing bucket to that,
    then clears the current bucket.
    """

    global my_bucket

    while True:

        for i in range(POST_INTERVAL):
            i += 1
            logging.debug("i = %s" % i)
            my_bucket.show()
            sleep(1)

        #threading.Timer(POST_INTERVAL, post_to_prtg).start()
        payload = my_bucket.convert_to_prtg_json()
        my_bucket.clear()

        http_post_thread = threading.Thread(target=http_post, args=payload)
        http_post_thread.setDaemon(True)
        http_post_thread.start()

# from https://github.com/blackberry/Python/blob/master/Python-3/Doc/library/socketserver.rst
class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):
    """This listens for UDP packets. If it receives them in statsd format
    it separates them, then adds them to the statsd bucket.
    """
    def handle(self):
        # data = self.request.recv(1024)
        data = self.request[0].strip()
        # socket = self.request[1]
        # cur_thread = threading.current_thread()
        # response = bytes("%s: %s" % (cur_thread.getName(), data),'ascii')
        # self.request.send(response)

        separated_packets = statsd_separate_packets(data.decode('UTF-8'))
        logging.debug("Separated: %s\n" % separated_packets)

        for packet in separated_packets:
            my_bucket.add(packet)

class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass

def statsd_separate_packets(statsd_data):
    """Reassembled_list stores the reassembled packets
    - packet_string is used in the loop for each individual packet
    - the incoming stacked packets get split on the period
    - each list item then gets appended to packet_string
    - if the list item contains a pipe | the packet_string is added to
      reassembled list, then packet_string is reset

    There is probably a faster way to do this with regex.
    """
    logging.debug("statsd data: %s" % statsd_data)
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
    logging.debug(reassembled_list)

    return reassembled_list


class Stats_Bucket(object):
    """Collects statsd metrics for specified time period.
    """

    # Two separate dictionaries for packets by count and by time (milliseconds)

    by_count = {}

    by_time = {}
    by_time_count = {}

    def add(self, packet):
        """Adds the packet to the bucket.
        If it's by count, it simply adds it to the existing count.
        If it's by time (in milliseconds), it adds to both the count of that
        as well as the the time, so that milliseconds/count can be done to
        calculate the mean later on.
        """
        channel, value, unit = self.parse(packet)

        if unit == 'c':
            if channel not in self.by_count:
                self.by_count[channel] = 0
            self.by_count[channel] += value
        elif unit == "ms":
            if channel not in self.by_time:
                self.by_time[channel] = 0
                self.by_time_count[channel] = 0
            self.by_time[channel] += value
            self.by_time_count[channel] += 1
            # must fix the time; need to add them up as usual, but
            # then divide by count

        else:
            logging.warning("Unit: %s. Not c or ms. Discarding packet." % unit)
        return 0

    def parse(self, packet):
        """Splits the packet into channels, values, and units.
        value and unit is split further because they each contain a value and
        unit separated by a pipe.
        """
        packet_as_list = packet.split(":")
        channel = packet_as_list[0]
        value = int(packet_as_list[1].split("|")[0])
        unit = packet_as_list[1].split("|")[1]
        return channel, value, unit

    def show(self):
        logging.info("# Count-based")
        for item in self.by_count:
            logging.info("%s: %s count" % (item, self.by_count[item]))
        logging.info("# Time-based")
        for item in self.by_time:
            logging.info("%s: %s ms average" % (item, round((int(self.by_time[ 
                item]))/int(self.by_time_count[item]), 1)))
        # print("Time/Count:")
        # for item in self.by_time_count:
        #   print("%s: %s" % (item, self.by_time_count[item]))


    def convert_to_prtg_json(self):
        """We'll first create json_string, which is the basic PRTG JSON format.
        Then split each item in reassembled_list, add to a new dictionary, then
        append that dictionary to the existing PRTG JSON structure.

        Each statsd metric name contains two or three levels:
        eg. rhWorker.runOnce, rh.dialogueTracker.internalContinue
        PRTG can't read that anyway, so we'll just pass in the entire string
        """

        # base string: '{"prtg": {"result": [{"channel": "name","value": "1","unit": "Count"}]}}'
        json_string = '{"prtg": {"result": []}}'
        json_data = json.loads(json_string)

        logging.debug("self.by_count: %s\n" % self.by_count)
        for entry in self.by_count:
            item_dict = {}
            item_dict["channel"] = entry
            item_dict["value"] = self.by_count[entry]
            item_dict["unit"] = "Count"
            json_data["prtg"]["result"].append(item_dict)

        logging.debug("self.by_time: %s\n" % self.by_time)
        for entry in self.by_time:
            item_dict = {}
            item_dict["channel"] = entry
            item_dict["value"] = self.by_time[entry]
            item_dict["unit"] = "ms"
            json_data["prtg"]["result"].append(item_dict)


        return json_data

    def clear(self):
        self.by_count.clear()
        self.by_time.clear()

def http_post(payload):
    """Takes a payload and posts it to the HTTP_SERVER server.
    From PRTG: "Note: Postdata has to be application/x-www-form-urlencoded"
    """

    logging.debug("payload: %s" % payload)
    #payload = {'key1': 'value1', 'key2': 'value2'}
    req = requests.post(HTTP_SERVER, data=json.dumps(payload))
    logging.debug(req.text)

if __name__ == '__main__':

    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        print("Exiting...")
        sys.exit()
    except Exception as e:
        print(e)
