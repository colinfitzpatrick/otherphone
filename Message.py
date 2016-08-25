# 
# Message.py
#
# Copyright xsynergy ltd 2010.  All Rights Reserved.
#

# Setup
# Install PySerial http://pyserial.sourceforge.net
# Install Pything Messaagine https://github.com/pmarti/python-messaging

import sys
import logging

from messaging.sms import SmsSubmit
from messaging.sms import SmsDeliver

logger = logging.getLogger('MY_OTHER_PHONE_APP')

# Class for dealing with SMS Message
# Include PDU text.

class Message:

	kNONE="none"

	_sMessage=""
	_sFrom=""
	_sTo=""
	_sId=""

	# New or Read Message
	_bStatus=True

	def __init__(self):

		logger.debug('New Message Class Created')
		_sMessage=""
        	_sFrom=""
        	_sTo=""
        	_sId=""

	# Create a message for sending
	def createMessage(self, to, message):
		logger.info('Creating message to "%s" "%s"' % (to,message) )

		self._sTo = to
		self._sMessage = message 

	# Import a message received from the deviee
	def importMessage(self, pduText, details=''):
		logger.debug('importMessage()-%s (%s)' % (pduText, details))

		try:
			message = SmsDeliver(pduText)
			self._sMessage = message.text
			self._sFrom = message.number		
	
			msgDetails = details.split(",")
                        self._sId = msgDetails[0].split(":")[1].strip()
	
			if msgDetails[1] != '0':
				self._bStatus = True
			else:
				self._bStatus = False

		except Exception, e:
			logger.exception(e)
			logger.error('Failed to decode incoming message')
			return False
		 
		logger.debug(self.toString())

		return True
	
	# Export message to a device
	# May return an empty string
	def exportMessage(self):
		logger.debug('exportMessage()')
		try:
			message = SmsSubmit(self._sTo, self._sMessage)
			return message.to_pdu()
		except:
			logger.error('Failed to encode message ' + self.toString())		

		return ''

	# Print the Message, for debugging
	def toString(self):
		return '[from: %s] [to: %s] [ID: %s] [Read: %s] %s' % (self._sFrom, self._sTo, self._sId, self._bStatus, self._sMessage)

	def getFrom(self):
		logger.debug('getFrom() ' + self.toString())
		return self._sFrom

	def getTo(self):
		logger.debug('getTo() ' + self.toString())
		return self.sTo

	def getMessage(self):
		logger.debug('getMessage() ' + self.toString())
		return self._sMessage

	def getID(self):
		logger.debug('getID() ' + self.toString())
		return self._sId

	def isRead(self):
		logger.debug('isRead() ' + self.toString())
		return self._bStatus


