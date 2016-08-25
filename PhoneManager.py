#!/usr/bin/python

import sys
import time
import GSMModem

import os
import threading
import glob
import pdb
import logging
from Message import Message

from apscheduler.scheduler import Scheduler

import ConfigParser

import shutil

logger = logging.getLogger('MY_OTHER_PHONE_APP')

class PhoneManager:

	# Default Sleep time between checks
	kDefaultLoopSleep=10

	# SMS Forwarding Information
	bForwardSMS=False
	sForwardSMSNumber=""
	bCallForwardNotify = False

	# Call Forwarding Information.
	bEnableCallForward = False
	sCallForwardNumber = ""
	bSMSForwardNotify = False	

	# SMS Auto Reply Informaiton.
	bAutoReply = False
	sAutoReplyText = ""
	bDeleteAfterResponse = False

	# Diable Call Forwarding
	bDisableCallForward = False

	# Determins if all SMS's should be processed, or just unread mesaages.
	bCheckAllSMS= True

	# The last result of a Send SMS 
	bLastResult = True

	# MSISDN of last received SMS
	sLastMessageFrom = ""

	# Maintains a list of numbers that have received an autoreply
	listAutoReply=[]

	# THread for prcessing
	_thread = None
	_bActive = False
	_lastRunTime = None

	# IMSI
	_IMSI = None

	# Message Queue
	messageQueue = None 

	# Config File.
	config = None
	configFile = ''

	kModemSection='modem'
	kIMSIOption='IMSI'

	kSettingsSection='settings'
	kForwardOption='forwardsms'
	kDivertOption='divert'
	kAutoReplyOption='autoreply'

	kScheduleSetting = 'schedule'
	kCommandOption = 'command'	
	kOptionOption = 'option'
	kDayOption = 'day'
	kWeekOption = 'week'
	kDayOfWeekOption = 'day_of_week'
	kHourOption = 'hour'
	kMinuteOption = 'minute'

	# Scheudler.
        sched = None

	# Config file changes
	configFileLastChanged = 0

	def __init__(self, modems, configFile):

		logger.debug('Init Modem, modems=' + str(modems) + ' configFileconfigFile='+ configFile)

		if modems == None:
			raise Exception('A Modem Must be Provided')

		if configFile == None:
			raise Exception('A config file must be provided.')

		self.messageQueue = []

                self.sched = Scheduler()
	
		self.loadConfig(configFile)

		if self._IMSI in modems:
			self.modem = modems[self._IMSI]
		else:
			raise Exception('No modem for selected IMSI')
		
	def loadConfig(self, configFile):

		logger.info('Loading config:' + configFile)
		self.configFile = configFile		

		workConfigFile = configFile + '~'

		logger.debug('Renaming to ' + workConfigFile)
		shutil.copyfile(configFile, workConfigFile)

		logger.debug('Clearing Scheduled Tasks')
		jobs = self.sched.get_jobs()
		for job in jobs:
			logger.debug('Removing ' + job.__str__())
			self.sched.unschedule_job(job)		

		try:
			config = ConfigParser.ConfigParser()
			config.read(workConfigFile)

			self.config = config

			IMSI = config.get(self.kModemSection, self.kIMSIOption)
			logger.debug('modem/IMSI-' + IMSI)
			self._IMSI = IMSI

			if config.has_option(self.kSettingsSection, self.kForwardOption):
				number = config.get(self.kSettingsSection, self.kForwardOption)
				if len(number) > 0:
					logger.debug('Forward SMS Number-' + number)
					self.enableSMSForwarding(number)
			else:
				self.disableSMSForwarding()

			if config.has_option(self.kSettingsSection, self.kDivertOption):
 	                      	number = config.get(self.kSettingsSection, self.kDivertOption)
        	                if len(number) > 0:
					logger.debug('Divert Number-' + number)
					self.enableCallForward(number)
			else:
				config.set(self.kSettingsSection, self.kDivertOption, '')
				#Diable call forward, need to right into main thread

			if config.has_option(self.kSettingsSection, self.kAutoReplyOption):
				autoReplyText = config.get(self.kSettingsSection, self.kAutoReplyOption)
				if len(autoReplyText) > 0:
					logger.debug('Auto Reply Text-' + autoReplyText)
					self.enableSMSAutoReply(autoReplyText)
				else:
					 self.disableSMSAutoReply()
			else:
				self.disableSMSAutoReply()

			for section in config.sections():
				if section.startswith(self.kScheduleSetting):
					logger.debug('Adding schedule ' + section)
				
					if config.has_option(section, self.kCommandOption):
						command = config.get(section, self.kCommandOption)
						
						if config.has_option(section, self.kOptionOption):
							option = config.get(section, self.kOptionOption)

							optionList = option.split(',')

							_optionDict = []

							for opt in optionList:
								logger.debug('Option: ' + opt)
								_optionDict.append(self.getStringAsType(opt))

							logger.debug('Options: ' + str(_optionDict))

						else:
							option = ''
					
						_day = self.getSetConfigOption(config, section, self.kDayOption)
						_week = self.getSetConfigOption(config, section, self.kWeekOption)
						_dayOfWeek = self.getSetConfigOption(config, section, self.kDayOfWeekOption)
						_hour = self.getSetConfigOption(config, section, self.kHourOption)
						_minute = self.getSetConfigOption(config, section, self.kMinuteOption)

                                                logger.debug('Add Schdule.  Comamnd=[' + command + '] options [' + option + '] day=' + _day + ' week=' + _week + ' day_of_week=' + _dayOfWeek + ' hour=' + _hour + ' minutes=' + _minute)

						if command == self.kForwardOption and len(option) > 0:
   
							job = self.sched.add_cron_job(self.enableSMSForwarding, 
								day = _day,
								week = _week,
								day_of_week = _dayOfWeek,
								hour = _hour,
								minute = _minute,
								args = _optionDict)
			
                                                if command == self.kForwardOption and len(option) == 0:

                                                        job = self.sched.add_cron_job(self.disableSMSForwarding,
                                                                day = _day,
                                                                week = _week,
                                                                day_of_week = _dayOfWeek,
                                                                hour = _hour,
                                                                minute = _minute)	

						if command == self.kDivertOption and len(option) > 0:

                                                        job = self.sched.add_cron_job(self.enableCallForward,
                                                                day = _day,
                                                                week = _week,
                                                                day_of_week = _dayOfWeek,
                                                                hour = _hour,
                                                                minute = _minute,
								args = _optionDict)

                                                if command == self.kDivertOption and len(option) == 0:

                                                        job = self.sched.add_cron_job(self.disableCallForward,
                                                                day = _day,
                                                                week = _week,
                                                                day_of_week = _dayOfWeek,
                                                                hour = _hour,
                                                                minute = _minute)
	
						if command == self.kAutoReplyOption and len(option) > 0:

                                                        job = self.sched.add_cron_job(self.enableSMSAutoReply,
                                                                day = _day,
                                                                week = _week,
                                                                day_of_week = _dayOfWeek,
                                                                hour = _hour,
                                                                minute = _minute,
                                                                args = _optionDict)

                                                if command == self.kAutoReplyOption and len(option) == 0:

                                                        job = self.sched.add_cron_job(self.disableSMSAutoReply,
                                                                day = _day,
                                                                week = _week,
                                                                day_of_week = _dayOfWeek,
                                                                hour = _hour,
                                                                minute = _minute)

						if job is not None:
							logger.info(job.__str__())

	                self.configFileLastChanged = time.ctime(os.path.getmtime(self.configFile))
	                logger.debug('Config file last changed: ' + self.configFileLastChanged)
							
		except Exception, e:
			logger.critical('Error loading config file')
			logger.exception(e)

	def getSetConfigOption(self, config, section, option):

		if config.has_option(section, option):
                	return config.get(section, option)

                else:
                       	config.set(section, option, '*')

		return '*'

	def getStringAsType(self, string):

		if string.lower() in ['true', '1', 't', 'y', 'yes', 'yeah', 'yup', 'certainly', 'uh-huh']:		
			return True

		if string.lower() in ['false', '0', 'f', 'n', 'no', 'nope']:
			return False

#		try:
#        		return int(string)
#    		except ValueError:
#        		return string

		return string

	def saveConfig(self):

		logger.debug('Saving Config File')

		config = self.config

		config.write(open(self.configFile, 'w'))

	# Start PhoneManager Thread 
	def start(self):
		logger.info('Starting Thread for ' + self._IMSI)		
		logger.debug('self ' + str(self))

                self.sched.start()

		self._lastRunTime = time.time()

		if self._bActive == False:
			self._bActive = True
			self._thread = threading.Thread(target=self._runLoop, name=self._IMSI)
			self._thread.daemon = True
			self._thread.start()
			logger.debug('Thread - ' + str(id(self._thread)))
		else:
			logger.warning('Thread already started ... ignorning.')

	def stop(self):
		logger.info('Stopping Thread')
		self._bActive=False

	def isActive(self):
		logger.debug('isActive()')

		if (self._lastRunTime + (self.kDefaultLoopSleep * 40)) < time.time(): 
			logger.critical('Thread appeared to be stalled')
			return False
		
		if self._thread.is_alive() == False:
			logger.critical('Thread is reporting as inactive')
			return False

		logger.debug('Thread is Active')
		return True

	def getIMSI(self):
		return self._IMSI

	def sendMessage(self, to, message):
		logger.debug('sendMessage() to ' + to + ' message ' + message) 
		logger.debug('self ' + str(self))
		logger.debug('self.messageQueue ' + str(id(self.messageQueue)))

		msg = Message()
		msg.createMessage(to, message)

		self.messageQueue.append(msg)

	def forward(self, number, notify=False, message='Forwarding Services to this phone.'):

		logger.debug('forwardAll() number ' + number)

		self.enableSMSForwarding(number, False)
		
		self.enableCallForward(number, False)

		if notify == True:
			self.sendMessage(number, message)

	def disableForward(self):

		logger.debug('disableForward()') 

		self.disableSMSForwarding()


	# Enablle SMS Forwarding (Async Process)
	def enableSMSForwarding(self, forwardSMSNumber, notify=False):
		logger.info('enableSMSForwarding() forwardSMSNumber=' + forwardSMSNumber)  		


		self.sForwardSMSNumber=forwardSMSNumber

		# Notify the user of the setup
		self.bSMSForwardNotify = notify	
		if notify == True:
			self.sendMessage(forwardSMSNumber, 'SMS Fowarding enabled.')

		# Ensure all SMS's are checked
		self.bCheckAllSMS = True

		# Set this last to avoid THreading Problems
		self.bForwardSMS=True 

		self.config.set(self.kSettingsSection, self.kForwardOption, forwardSMSNumber)
		self.saveConfig()

	# DIable call forwarding
	def disableSMSForwarding(self):
		logger.info('disableSMSForwarding()')
	
		self.bForwardSMS=False

		self.config.set(self.kSettingsSection, self.kForwardOption, '')
		self.saveConfig()

	# Enable SMS Auto Reply
	def enableSMSAutoReply(self, sMessage, delete=False):
		logger.info('enableSMSAutoReply() sMessage=' + sMessage)

		self.sAutoReplyText = "(Automatic Response) " + sMessage
		
		self.bDeleteAfterResponse=delete

		#Set this last to avoid Threading Problems
		self.bAutoReply = True 

		self.config.set(self.kSettingsSection, self.kAutoReplyOption, sMessage)
		self.saveConfig()

	# Disable SMS AutoRreply
	def disableSMSAutoReply(self):
		logger.info('disableSMSAutoReply()')
		
		self.bAutoReply = False

		self.config.set(self.kSettingsSection, self.kAutoReplyOption, '')
		self.saveConfig()

	# enable Call forwarding
        def enableCallForward(self, sNumber, notify = False):
		logger.info('enableCallForward() sNumber='+sNumber)

		self.bCallForwardNotify = False

                self.sCallForwardNumber = sNumber
                self.bEnableCallForward = True

		self.config.set(self.kSettingsSection, self.kDivertOption, sNumber)
		self.saveConfig()

	# Disable call Forwarding
	def disableCallForward(self, notify = False):
		logger.info('Disabling call forwarding')

		self.bDisableCallForward = True

		if notify == True:
			self.sendMessage(self.bCallForwardNumber, 'Calls are no longer diverted to you')

		self.config.set(self.kSettingsSection, self.kDivertOption, '')
		self.saveConfig()

	# Main run loop
	def _runLoop(self):

		logger.debug('_runLoop()')

		while self._bActive:

			logger.debug('Run Loop ...')
			logger.debug('self:' + str(self) + ' ' + str(id(self)))

			if self.bForwardSMS == True or self.bAutoReply == True:
				self._processSMS()

			if self.bEnableCallForward == True:
				self._forwardCall(self.sCallForwardNumber)			
				self.bEnableCallForward = False

			if self.bDisableCallForward == True:
				self._disableCallForward()
				self.bDisableCallForward = False

			if len(self.messageQueue) > 0:
				logger.debug('Found messages to send')
			 	logger.debug('self.messageQueue:' + str(id(self.messageQueue)))

				for message in self.messageQueue:
					logger.debug('New message ' + message.toString())
					if self.modem.sendMessage(message) == True:
						self.messageQueue.remove(message)
			
			currentTime = time.ctime(os.path.getmtime(self.configFile))			
			logger.debug('Config time last modified time: ' + str(currentTime) + '. Last load time : ' + str(self.configFileLastChanged))		

			if self.configFileLastChanged < currentTime:
				logger.info('Config File (' + self.configFile + ') has changed ...')
				self.loadConfig(self.configFile)	

			time.sleep(self.kDefaultLoopSleep)

			self._lastRunTime = time.time()
	
		logger.debug('Exitin _runLoop()')

	# Forward a call to another number
	# Should only be called form runloop
	def _forwardCall(self, sNumber):
		logger.debug('_forwardCall() sNumber ' + sNumber) 

		self.modem.setCallForward(sNumber)
		
		if self.bCallForwardNotify == True:
			notify = Message()
			notify.createMessage(sNumber, 'Calls are now being diverted to you.')
			self.modem.sendMessage(notify)

	def _disableCallForward(self):
		logger.debug('_disableCallForward()')

		self.modem.disableCallForward()

	# Process SMS messages
	# Should only be alled from runLoop
	def _processSMS(self):

		logger.debug('_processSMS()')

                if self.bCheckAllSMS == True:
			logger.debug('Getting all messages')
                        messages = self.modem.getMessages()
                        self.bCheckAllSMS = False
                else:
			logger.debug('Getting new messages')
                        messages = self.modem.getNewMessages()

		if len(messages) > 0:
			logger.info('Found ' + str(len(messages)) + ' message(s)')

		logger.debug('Found ' + str(len(messages)) + ' message(s)')

		for message in messages:

			logger.info('Message ' + message.toString())

			resultForward = resultAutoReply = True

			if self.bForwardSMS == True:
				logger.debug('Foward SMS')	
				resultForward = self._forwardSMS(message)

			if self.bAutoReply == True and message.isRead() == False:
				logger.debug('Auto Reply SMS')
				resultAutoReply = self._autoReply(message)

			result = resultForward and resultAutoReply

			# If last message failed to send, and this one was successful
			# .. next time check all messages to fix errors.
                	if self.bLastResult != result: 
                        	self.bCheckAllSMS = True

                	self.bLastResult = result

                	if (self.bForwardSMS == True and resultForward == True) or \
				(resultAutoReply == True and self.bDeleteAfterResponse == True):
                        	self.modem.deleteMessage(message.getID())

	# Autoreply to message
	# Should onlbe called from runLoop
	def _autoReply(self, message):

		result = True
		logger.debug('_autoReply() ' + message.toString())
		logger.debug('_autoReply() ' + str(self.listAutoReply) )

		if (message.getFrom() in self.listAutoReply) == False:
			self.listAutoReply.append(message.getFrom())

			reply = Message()
			reply.createMessage(message.getFrom(), self.sAutoReplyText)	

			result = self.modem.sendMessage(reply)
					
		return result
	
	# Forward SMS
	# Should only be called form runLoop
	# If the mesaage is from the owner, forward the messages to the MSISDN of the previous message
	def _forwardSMS(self,message):

		forwardMessage = Message()

		if message.getFrom() == self.sForwardSMSNumber:
			if len(self.sLastMessageFrom) > 0:
				forwardMessage.createMessage(self.sLastMessageFrom, message.getMessage())
               		else:
				forwardMessage.createMessage(self.sForwardSMSNumber, 'There is no message to reply to ... sorry')
		else:
                       	self.sLastMessageFrom = message.getFrom()            

                      	newMessage = '(' + message.getFrom() + ') ' + message.getMessage()
			
			forwardMessage.createMessage(self.sForwardSMSNumber, newMessage)

		logger.debug(forwardMessage.toString())
               	return self.modem.sendMessage(forwardMessage)

#END CLASS Manager


