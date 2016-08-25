#!/usr/bin/python

import sys

from GSMModem import GSMModem

from PhoneManager import PhoneManager

from time import sleep

import os
import glob
import logging
import logging.handlers


# -- Logging --
logger = logging.getLogger('MY_OTHER_PHONE_APP')
logger.setLevel(logging.DEBUG)

ch = logging.handlers.RotatingFileHandler('OtherPhone-DEBUG.log', maxBytes=10485760, backupCount=5)
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

ci = logging.handlers.RotatingFileHandler('OtherPhone-INFO.log', maxBytes=10485760, backupCount=5)
ci.setLevel(logging.INFO)
ci.setFormatter(formatter)

logger.addHandler(ci)

cl = logging.StreamHandler()
cl.setLevel(logging.INFO)
cl.setFormatter(formatter)

logger.addHandler(cl)


# -- Overall Exception Handling --
try:

# -- Modems --

	searchList=glob.glob('/dev/ttyUSB*')
#	searchList=['/dev/ttyUSB2']
	searchList.sort()

	logger.info('Search List ' + str(searchList))

	modems = GSMModem.getAttachedModems(searchList)

	logger.info("Modems:" + str(len(modems)))
	logger.info(str(modems.keys()))

	if len(modems) == 0:
		logger.critical("Couldn't find any modems")
		sys.exit(1)

# -- Config Files --

	configList = glob.glob('config.d/*.ini')
	logger.info('Config Files ' + str(configList))

# -- Managers --

	managers = []

	for config in configList:
		try:
			managers.append( PhoneManager(modems, config) )

		except Exception, e:
			logger.error('Error creating manager for config file  ' + config)
			logger.exception(e)

	if len(modems) != len(managers):
		logger.warning('Configuration doesnt match number of modems')


	for manager in managers:
		try:
			manager.modem.deleteAllMessages()
			manager.start()
		except Exception, e:
			logger.error('Error starting manager for ' + manager.getIMSI( ))


# -- While Loop --

	active = True

	while active:

		sleep(30)

		for manager in managers:
			if manager.isActive() == False:
				active = False	

	logger.info('Exiting')

except Exception, e:
	logger.exception(e)


