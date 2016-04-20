from nose.tools import *
import statsd2prtg

def setup():
    print("SETUP!")

def test_teardown():
    print("TEAR DOWN!")

def test_basic():
    print("I RAN!")

#def test_stats_convert_to_json():
#    statsd_data = 