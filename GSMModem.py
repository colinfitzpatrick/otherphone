# 
# otherPhone.py
#
# Copyright xsynergy ltd 2010.  All Rights Reserved.
#

# Setup
# Install PySerial http://pyserial.sourceforge.net
# Install Pything Messaagine https://github.com/pmarti/python-messaging

import sys
sys.path.append("/home/colin/tools/pyserial-2.6")

import sys
import serial
import os
import time
import syslog
import logging

from Message import Message

from time import sleep

logger = logging.getLogger('MY_OTHER_PHONE_APP')

# GSM Modem (Generic)
class GSMModem:

	# AT Command
        kCMD_OK="OK"
        kCMD_PREFIX="AT+"
        kCMD_EOL="\r\n"

	kCMD_TEST="AT"
        kCMD_PDU_MODE=kCMD_PREFIX+"CMGF=0"

	kCMD_ECHO_OFF="ATE0"

        kCMD_CHECKPIN=kCMD_PREFIX+"CPIN?"
	kCMD_SET_PIN=kCMD_PREFIX+"CPIN={0}"
	kCMD_DISABLE_PIN=kCMD_PREFIX+"CLCK=\"SC\",0,\"{0}\""

	kSIM_PIN_READY="+CPIN: READY"

	kCMD_TEXT_MODE=kCMD_PREFIX+"CMGF=1"

	kCMD_FORWARD_ENABLE=kCMD_PREFIX+"CCFC=0,1"
	kCMD_FORWARD_REG=kCMD_PREFIX+"CCFC=0,3,{0},145"
	kCMD_FORWARD_DISABLE=kCMD_PREFIX+"CCFC=0,4"

	kCMD_GET_SMS=kCMD_PREFIX+"CMGL={0}"
	kCMD_SEND_SMS=kCMD_PREFIX+"CMGS=\"{0}\""
	kCMD_DEL_SMS=kCMD_PREFIX+"CMGD={0}"
        kCMD_SEND_PDU_SMS=kCMD_PREFIX+"CMGS={0}"
	kCMD_SET_SMSC=kCMD_PREFIX+"CSCA=\"{0}\""

        kCMD_IMSI=kCMD_PREFIX+"CIMI"

	kCMD_CTRL_Z="\x1A"

	# SMS Status (Text Mode)
        kALL="ALL"
        kNEW="REC UNREAD"
	kSMS="+CMGL:"	


	# SMS Startus (PDU Mode)
	kPDU_ALL=4
	kPDU_NEW=0
	kPDU_OLD=1

	serialTimeout=2

	_bPDUMODE=False

	bConnected=False
	
	IMSI=""	

        def __init__(self, sDevice):

		logger.info('Creating modem for device [' + str(sDevice) + ']')
	
		self.ser = serial.Serial(sDevice, timeout=self.serialTimeout)

		self.clear()

		self.setPDUMode()

		self.getIMSI()

	# If the modem has a monitor serial port, set it up here.
	# Currently not used.
	def setMonitor(self, sDevice):

		logger.info('Creating monitor for device [' + str(sDevice) + ']')

		self.monitor = serial.Serial(sDevice, timeout=self.serialTimeout)

	#Gets the list of currently attached modems, and ensures that they have an IMSI
	@staticmethod
	def getAttachedModems(sDevices):

		logger.debug('getAttachedModems() ' + str(sDevices))
		modemList = {}

		for device in sDevices:

			try:
				m = GSMModem(device)
			except:
				logger.warning("Invalid Device " + device)
				continue 

			if m.bConnected == True:
				if modemList.has_key(m.getIMSI()) == False:
					modemList[m.getIMSI()] = m
				else:
					modemList[m.getIMSI()].setMonitor(device)

		logger.info('Found ' + str(len(modemList)) + ' modem(s)')
		return modemList

	def clear(self):

		logger.debug('clear()')		

		#Send a CTRL-Z incase there is an open SMS problem.
                self.cmd(self.kCMD_CTRL_Z)
                self.cmd(self.kCMD_TEST)
                self.cmd(self.kCMD_ECHO_OFF)

		result = self.cmd(self.kCMD_TEST)		

		if result[0] != self.kCMD_OK:
			logger("Failed to talk to modem")
	
		logger.info("Modem Detected")
		self.bConnected=True
		
	def isConnected(self):
		logger.debug('isConnected()')
		return self.bConnected


	def getIMSI(self):
		logger.debug('getIMSI()')		

		if len(self.IMSI) == 0:
			result = self.cmd(self.kCMD_IMSI)
			self.IMSI = result[0]	
			logger.info('IMSI:' + self.IMSI)

		return self.IMSI

	def setSMSC(self, smsc):
		logger.debug('Setting SMSC ' + smsc)

		self.cmd(self.kCMD_SET_SMSC.format(smsc))
		

        def checkPIN(self, pin):
		logger.debug('Check Pin ' + pin)

		result = self.cmd(self.kCMD_CHECKPIN)
                if result[0] != self.kSIM_PIN_READY:
			command = self.kCMD_SET_PIN.format(pin)
			result = self.cmd(command)
			if result[0] != self.kCMD_OK:
				logger.error("PIN Error") 
				return False			
		
			# command = self.kCMD_DISABLE_PIN.format(pin)
			# result = self.cmd(command)

		logger.info("PIN OK")
		return True

	def setTextMode(self):
		logger.debug('setTextMode()')

		result = self.cmd(self.kCMD_TEXT_MODE)
                if result[0] != self.kCMD_OK:
                        raise Exception("Failed to set text mode")

		self._bPDUMODE=False

        def setPDUMode(self):
		logger.debug('setPDUMode()')

                result = self.cmd(self.kCMD_PDU_MODE)
                if result[0] != self.kCMD_OK:
                        logger.error("Failed to set pdu mode")
			self._bPDUMODE=False
			return

		self._bPDUMODE=True

        def setCallForward(self, number):
		
		logger.debug('setCallForward() ' + number)

                result = self.cmd(self.kCMD_FORWARD_ENABLE)
                if result[0] != self.kCMD_OK:
			logger.warning("Failed to set call forwarding")

		result = self.cmd(self.kCMD_FORWARD_REG.format(number))	
		if result[0] != self.kCMD_OK:
			logger.error("Failed to set call forwarding")
			return

		logger.info("Call forward set to " + number)

        def disableCallForward(self):

		logger.debug('disableCallForward()')
                result = self.cmd(self.kCMD_FORWARD_DISABLE)
                if result[0] != self.kCMD_OK:
			logger.warning("Failed to set call forwarding")
                
		return

        def getNewMessages(self):
                
		logger.debug('getNewMessages()')

		if self._bPDUMODE == False:
                        logger.error('Must Enable PDU Mode')
			return {}
                else:
                        return self.getMessages(self.kPDU_NEW)


	def getMessages(self, type=kPDU_ALL):
		
		logger.debug('getMessages()')

		if self._bPDUMODE == False:
                        logger.error('Must Enable PDU Mode')
                        return {}                
		else:
                        return self.getPDUMessages(type)

	#Depreciated, user PDU version.
        def getTextMessages(self, type=kALL):
                messages = []
		success=False

		result = self.cmd(self.kCMD_GET_SMS.format("\"" + type + "\""))
		
		for i in range(len(result)):
			if result[i].startswith(self.kSMS):
				logger("Message details:" + msgDetails)
	
				pdu = result[i+1]
				pduSMS = SMSDeliver(pdu)

				message = SMS(pduSMS.text, pduSMS.number) 
				messages.append(message)
				continue

			if result[i] == self.kCMD_OK:
				success=True
				break
		
		if success == False:
			logger("Failed to get SMS")
			raise Exception("Failed to get SMS")

                return messages

	def getPDUMessages(self, type=kPDU_ALL):

		logger.debug('getPDUMessages() type='+ str(type))

                messages = []
                success=False

                result = self.cmd(self.kCMD_GET_SMS.format(type))

							# For each line
                for i in range(len(result)):
							# If it starts with kSMS
                        if result[i].startswith(self.kSMS):
							# ... we found the Message details
							# ... the next line is the PDU Text
				# Message(message pdu text, details)
				message = Message()
				message.importMessage(result[i+1], result[i])
 
				messages.append(message)
                                continue

							# When we hit OK, exit loop
                        if result[i] == self.kCMD_OK:
                                success=True
                                break

                if success == False:
                        logger.error("Failed to get SMS")
			return {}

                return messages


	def sendMessage(self, message):
		logger.debug('sendMessage() - ' + message.toString())

		if self._bPDUMODE == False:
			logger.error('Must Enable PDU Mode')
			return False
		else:
			return self.sendPDUMessage(message)

	# Depreicated, with PDU Version
	def sendTextMessage(self, message):

		self.cmd(self.kCMD_SEND_SMS.format(message.getTo()))
		result = self.cmd(message.getMessage()[:158] + self.kCMD_CTRL_Z)
	
                success=False

                for i in range(len(result)):
                        if result[i] == self.kCMD_OK:
				return True

		return False

        def sendPDUMessage(self, message):

		logger.debug('sendPDUMessage() ' + message.toString())

		# Retunrs a list of messages to send (for long messages)
		pduTexts = message.exportMessage()

		result = ''

                for pdu in pduTexts:
                        self.cmd(self.kCMD_SEND_PDU_SMS.format(pdu.length))
                        result = self.cmd(pdu.pdu + self.kCMD_CTRL_Z)

                for i in range(len(result)):
                        if self.kCMD_OK in result[i]:
                                return True

		return False


	def deleteMessage(self, index):
		logger.debug('Delete message at ' + str(index))
		self.cmd(self.kCMD_DEL_SMS.format(index))

	def deleteAllMessages(self):
                success=False

		if self._bPDUMODE == False:
                        logger.error('Must Enable PDU Mode')
                        return False
		else:
			result = self.cmd(self.kCMD_GET_SMS.format(self.kPDU_ALL))


                for i in range(len(result)):
                        if result[i].startswith(self.kSMS):
                                msgDetails = result[i].split(",")
				index = msgDetails[0].split(":")[1]

				self.cmd(self.kCMD_DEL_SMS.format(index))

                        if result[i] == self.kCMD_OK:
                                success=True
                                break

                if success == False:
			logger.error("Failed to delete SMS")
		
		logger.info("All messages deleted")


	def cmd(self, command):
		logger.debug("Command: " + command)
		
		self.ser.write(command+self.kCMD_EOL)
		result=self.tidy(self.ser.readlines())

		if len(result) == 0:
			sleep(5)
			result=self.tidy(self.ser.readlines())

		logger.debug("Result: " + " ".join(str(x) for
x in result))

		return result
        
	def tidy(self, result):

		tidyresult = []	
	
		for item in result:
			tidyitem = item.strip(self.kCMD_EOL)
			if len(tidyitem) > 0 :
				tidyresult.append(tidyitem)
		
		return tidyresult


