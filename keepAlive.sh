#!/bin/bash

echo 'Checking if our monitor script is active'

if ps ax | grep -v grep | grep OtherPhone.py > /dev/null
then
	echo "Script is running"
else
	sudo shutdown now -r
fi


