#!/usr/bin/env python

import requests

def main():

	#send_test()
	http_post()

def http_post():
	'''
	'''

	payload = {'key1': 'value1', 'key2': 'value2'}
	r = requests.post('http://httpbin.org/post', data = payload)
	print(r.text)

if __name__ == '__main__':
	main()