#!/usr/bin/env python

"""Usage:
    statsd2prtg [--debug][--httpbin][--interval <seconds> ]

Options:
    -d, --debug      Log debug messages
    -b, --httpbin    Post HTTP to httpbin.org
    -i, --interval   Number of seconds between HTTP POSTs
    -h, --help       Print this help screen
"""

#from .statsd2prtg import Stuff

import os
import configparser
import logging
import sys      # for sys.exit
import json     # dealing with json
from time import sleep
import threading
import socketserver
import requests # HTTP requests
import docopt # parsing command line arguments

# These shouldn't change, but here for debug if necessary
UDP_IP = "127.0.0.1" # interface to listen on
UDP_PORT = 8125 # port to listen on
POST_INTERVAL = 30
HTTP_SERVER = "" # defined in main()

def main():
    # Getting configuration first
    config = load_config()

    try:
        PRTG_PROBE_ADDRESS = config.get('main', 'PRTG_PROBE_ADDRESS')
        PRTG_TOKEN = config.get('main', 'PRTG_TOKEN')
        DO_POST = config.get('main', 'DO_POST')
        LOG_LOCATION = config.get('main', 'LOG_LOCATION')
    except AttributeError as e:
        print(e)
        print("Does the file have the correct format?")

    arguments = docopt.docopt(__doc__)
    if arguments['--debug']:
        log_level=logging.DEBUG

    else:
        log_level=logging.INFO

    global HTTP_SERVER
    if arguments['--httpbin']:
        HTTP_SERVER = "http://httpbin.org/post"
    else:
        HTTP_SERVER = "http://%s/%s" % (PRTG_PROBE_ADDRESS, PRTG_TOKEN)

    if arguments['--interval']:
        try:
            interval = int(arguments['<seconds>'])
            if interval > 0:
                global POST_INTERVAL
                POST_INTERVAL = interval
            else:
                print("Please enter an integer greater than 0.")
                sys.exit()
        except:
            print("Please enter an integer greater than 0.")
            sys.exit()

    # pylint: disable=C0103
    logging.basicConfig(filename=LOG_LOCATION, level=log_level)
    logging.info("\n\n+++++ Reinitializing +++++")
    logging.info("Log level: %s" % logging.getLevelName(log_level))

    # Initialize the UDP server
    server = ThreadedUDPServer((UDP_IP, UDP_PORT), ThreadedUDPRequestHandler)

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

    # logging.debug("All threads: %s" % threading.enumerate())
    # logging.debug("Current thread: %s\n\n" % threading.current_thread())

def prtg_collector():
    """Creates a bucket to collect statsd stats. Every x seconds,
    initializes a post to http thread, passes the existing bucket to that,
    then clears the current bucket.
    """

    while True:

        for i in range(POST_INTERVAL):
            i += 1
            #logging.debug("i = %s" % i)
            logging.debug("%s seconds until next HTTP post" % (POST_INTERVAL - i))
            my_bucket.show()
            sleep(1)

        #threading.Timer(POST_INTERVAL, post_to_prtg).start()
        payload = my_bucket.convert_to_prtg_json_and_clear()

        # XXX: How do we prevent of having too many stale HTTP processes
        # in case PRTG doesn't respond quickly enough? Can we at least
        # monitor it?
        http_post_thread = threading.Thread(target=http_post, args=(payload,))
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

        my_bucket.add_packets(separated_packets)

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

    >>> statsd_separate_packets("rh.sccp.in:1|c\\nrh.dialogueTracker.externalEnd:1|c\\nrh.dialogueDatabase.findToExternal:0|ms\\nrh.sccp.out:1|c\\nrh.toExternal:1|c\\nrhWorker.runOnce:1|ms")
    ['rh.sccp.in:1|c', 'rh.dialogueTracker.externalEnd:1|c', 'rh.dialogueDatabase.findToExternal:0|ms', 'rh.sccp.out:1|c', 'rh.toExternal:1|c', 'rhWorker.runOnce:1|ms']
    """
    logging.debug("statsd data: %s" % statsd_data)
    split_statsd_data = statsd_data.split("\n")
    logging.debug(split_statsd_data)

    return split_statsd_data


class Stats_Bucket(object):
    """Collects statsd metrics for specified time period.
    """

    # Two separate dictionaries for packets by count and by time (milliseconds)

    by_count = {}

    by_time = {}
    by_time_count = {}
    by_time_minmax = {}
    lock = threading.Lock()

    def minKey(self, key):
        return key + ".min"

    def maxKey(self, key):
        return key + ".max"

    def add_packets(self, packets):
        for packet in packets:
            with self.lock:
                self.add(packet)

    def add(self, packet):
        """Adds the packet to the bucket.
        If it's by count, it simply adds it to the existing count.
        If it's by time (in milliseconds), it adds to both the count of that
        as well as the the time, so that milliseconds/count can be done to
        calculate the mean later on.

        # Create bucket, add values, print, export, check it is cleared
        >>> bucket = Stats_Bucket()
        >>> bucket.add('rh.sccp.in:4|ms')
        0
        >>> bucket.add('rh.sccp.in:3|ms')
        0
        >>> bucket.add('rh.sccp.in:5|ms')
        0
        >>> bucket.add('rh.sccp.in:10|ms')
        0
        >>> bucket.show()
        >>> bucket.show_on(print)
        Count-based:
        Time-based:
        rh.sccp.in: 5.5 ms average 3 ms min 10 ms max
        >>> sorted(bucket.by_time.keys())
        ['rh.sccp.in']
        >>> sorted(bucket.by_time_minmax.keys())
        ['rh.sccp.in.max', 'rh.sccp.in.min']
        >>> res = bucket.convert_to_prtg_json_and_clear()
        >>> sorted(bucket.by_time.keys())
        []
        >>> sorted(bucket.by_time_minmax.keys())
        []
        >>> sorted(res.keys())
        ['prtg']
        >>> res = res['prtg']['result']
        >>> len(res)
        4
        >>> res = sorted(res, key=lambda x: x['channel'])
        >>> for key in sorted(res[0].keys()): print(key, res[0][key])
        channel json-success
        unit Count
        value 1
        >>> for key in sorted(res[1].keys()): print(key, res[1][key])
        channel rh.sccp.in
        customunit msec
        unit Custom
        value 5
        >>> for key in sorted(res[2].keys()): print(key, res[2][key])
        channel rh.sccp.in.max
        unit msec
        value 10
        >>> for key in sorted(res[3].keys()): print(key, res[3][key])
        channel rh.sccp.in.min
        unit msec
        value 3
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
                self.by_time_minmax[self.minKey(channel)] = sys.maxsize
                self.by_time_minmax[self.maxKey(channel)] = 0
            self.by_time[channel] += value
            self.by_time_count[channel] += 1
            # must fix the time; need to add them up as usual, but
            # then divide by count

            if self.by_time_minmax[self.minKey(channel)] > value:
                self.by_time_minmax[self.minKey(channel)] = value
            if self.by_time_minmax[self.maxKey(channel)] < value:
                self.by_time_minmax[self.maxKey(channel)] = value

        else:
            logging.warning("Unit: %s. Not c or ms. Discarding packet." % unit)
            logging.warning("Packet: %s" % packet)
            logging.warning("Channel: %s. Value: %s. Unit: %s." % (channel, value, unit))
        return 0

    def parse(self, packet):
        """Splits the packet into channels, values, and units.
        value and unit is split further because they each contain a value and
        unit separated by a pipe.

        >>> Stats_Bucket().parse('rh.sccp.in:1|c')
        ('rh.sccp.in', 1, 'c')

        >>> Stats_Bucket().parse('gorets:1|c|@0.1')
        ('gorets', 1, 'c')
        """
        packet_as_list = packet.split(":")
        channel = packet_as_list[0]
        value = int(packet_as_list[1].split("|")[0])
        unit = packet_as_list[1].split("|")[1]
        return channel, value, unit

    def show(self):
        return self.show_on(logging.debug)

    def show_on(self, output):
        output("Count-based:")
        for item in self.by_count:
            output("%s: %s count" % (item, self.by_count[item]))
        output("Time-based:")
        for item in self.by_time:
            output("%s: %s ms average %s ms min %s ms max" % (item, round((int(self.by_time[
                item]))/int(self.by_time_count[item]), 1), self.by_time_minmax[self.minKey(item)], self.by_time_minmax[self.maxKey(item)]))
        # print("Time/Count:")
        # for item in self.by_time_count:
        #   print("%s: %s" % (item, self.by_time_count[item]))

    def convert_to_prtg_json_and_clear(self):
        with self.lock:
            json_data = self.convert_to_prtg_json()
            self.clear()
            return json_data

    def convert_to_prtg_json(self):
        """We'll first create json_string, which is the basic PRTG JSON format.
        Then split each item in reassembled_list, add to a new dictionary, then
        append that dictionary to the existing PRTG JSON structure.

        Each statsd metric name contains two or three levels:
        eg. rhWorker.runOnce, rh.dialogueTracker.internalContinue
        PRTG can't read that anyway, so we'll just pass in the entire string
        """

        # base string: '{"prtg": {"result": [{"channel": "name","value": "1","unit": "Count"}]}}'
        json_string = '{"prtg": {"result": [{"channel": "json-success","value": "1","unit": "Count"}]}}'
        #json_string = '{"prtg": {"result": []}}'
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
            # print("self.by_time[entry]: %s" % self.by_time[entry])
            # print("self.by_time_count[entry]: %s" % self.by_time_count[entry])
            item_dict = {}
            item_dict["channel"] = entry
            # the below line divides the sum of the times (in ms) by the count
            # of the entries
            item_dict["value"] = int(self.by_time[entry]/self.by_time_count[entry])
            item_dict["unit"] = "Custom"
            item_dict["customunit"] = "msec"
            json_data["prtg"]["result"].append(item_dict)

        logging.debug("self.by_time_minmax: %s\n" % self.by_time)
        for entry in self.by_time_minmax:
            item_dict = {}
            item_dict["channel"] = entry
            item_dict["value"] = self.by_time_minmax[entry]
            item_dict["unit"] = "Custom"
            item_dict["unit"] = "msec"
            json_data["prtg"]["result"].append(item_dict)

        return json_data

    def clear(self):
        self.by_count.clear()
        self.by_time.clear()
        self.by_time_minmax.clear()

def http_post(payload):
    """Takes a payload and posts it to the HTTP_SERVER server.
    From PRTG: "Note: Postdata has to be application/x-www-form-urlencoded"
    """
    logging.debug("All threads: %s" % threading.enumerate())
    logging.debug("Current thread: %s" % threading.current_thread())
    logging.info("Payload in http_post: %s" % payload)
    # payload format is a dictionary {'key1': 'value1', 'key2': 'value2'}
    req = requests.post(HTTP_SERVER, data=json.dumps(payload))
    logging.info("Posted to HTTP server")
    logging.info(req.text)

def load_config():
    '''
    Loads config from config. Default is in ~/.statsd2prtg-config.
    '''

    # Getting configuration first
    file_path = os.path.expanduser("~/.statsd2prtg-config")
    # configparser silently fails if the file doesn't exist
    if os.path.isfile(file_path):   
        config = configparser.ConfigParser()
        try:
            config.read(file_path)
        except Exception as e:
            print(e)
            print("Couldn't read configuration file.")
    else:
        print("Couldn't open config file. Has it been created as \'~/.statsd2prtg-config\'?")

    return config

if __name__ == '__main__':

    try:
        main()
    except (KeyboardInterrupt):
        print("Exiting...")
        sys.exit()
    except Exception as e:
        print(e)