# otherphone
This is a work in progress application which allows you to use a second phone number without carrying a second phone/sim.

A python scipt that connects to a GSM Modem (such as Huawei H220 ) and:
- Schedule call diverts between certain times.
- Forward SMSs to another number.
  - Replies sent to these SMS's are send to the originator. 
  
## Requires
- PySerial http://pyserial.sourceforge.net
- Python Messaaging https://github.com/pmarti/python-messaging
- SMSPDU https://pypi.python.org/pypi/smspdu

## To use 
- Create a file in config.d based on the template.
