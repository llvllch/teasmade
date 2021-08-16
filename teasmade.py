#!/usr/bin/python3
from tqdm import tqdm
import vlc
import struct
import re
import os
import subprocess
import sys
import pyaudio
import gpiozero
import apa102
from pixels import Pixels
import time
import yaml
import argparse
import logging
import threading
import argparse
from datetime import datetime, timedelta
# Initialise things, lights loglevel, flags etc
pixels = Pixels()
parser = argparse.ArgumentParser()
parser.add_argument("--log", default='info', help='Set the log level (default: info)')
args = parser.parse_args()
loglevel = getattr(logging, args.log.upper(), logging.WARN)
logging.basicConfig(level=loglevel)	
gpiosparerelay = 13 # Only one relay is currently used, this is the spare
gpiopinheat = 12
heatrelay = gpiozero.OutputDevice(gpiopinheat, active_high=True, initial_value=False)

def resetkettle():
	poweron=False
	pixels.off()
	heatrelay.off()
	return poweron

def boil():
	# Turn the relay on
	heatrelay.on()
	# Visual Indicator of Heating
	pixels.wakeup()
	time.sleep(3)
	pixels.think()
	# Note the time it was turned on at
	turnedonat=datetime.now()
	poweron=True
	# The Kettle is on now, so we can move on
	return poweron

def main():
	button = gpiozero.Button(17)
	configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.yaml')
	parser = argparse.ArgumentParser()
	parser.add_argument("--log", default='info', help='Set the log level (default: info)')
	args = parser.parse_args()
	loglevel = getattr(logging, args.log.upper(), logging.WARN)
	logging.basicConfig(level=loglevel)

	with open(configfile) as f:
		config = yaml.load(f, Loader=yaml.FullLoader)
	logging.info(config)

	try:
		#Initialise to off
		poweron=resetkettle()
		
		while True:
			# If the kettle isn't on, check if it should be
			while poweron==False:
				# Check calendar for coffee in the next 10 minutes
				now = datetime.now()
				lookahead = config['calendar']['lookahead']
				now_plus_start = now + timedelta(minutes = lookahead)
				now_plus_end= now + timedelta(minutes = lookahead+1)
				result=subprocess.run(['gcalcli','--calendar',config['calendar']['name'],'search', config['calendar']['trigger'],str(now_plus_start), str(now_plus_end)], stdout=subprocess.PIPE)
				logging.info(result.stdout.decode())
				waitforit ="No Event" in result.stdout.decode()
				if waitforit==False:
					logging.info("Matching appointment coming up, heating the water")
					poweron=boil()
				else:
					time.sleep(60)

			# The Kettle must have turned on, so we wait, then play an alarm?
			iterations=100
			heattimeseconds=int(config['relay']['closedfor'])*60

			notify = "Power to teasmade active for "+str(config['relay']['closedfor'])+" minutes"
			logging.info(notify)

			for i in tqdm(range(iterations)):
				time.sleep(heattimeseconds/iterations)

			# Been boiling for a while, time for a glorious fanfare
			logging.info("Alarm Music starting")
			brewalarm= vlc.MediaPlayer(config['alarm']['pathtotrack'])
			brewalarm.play()

			# Turn the kettle off. Teasmade should have already done this. Safety first etc
			poweron=resetkettle()
			# Back to beginning of loop to check the calendar

	except KeyboardInterrupt:  
		resetkettle()
		time.sleep(1)  
		logging.info("Interrupt: ctrl + c:")
		heatrelay.close()


if __name__ == '__main__':
	main()
