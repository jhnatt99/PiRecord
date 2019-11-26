#!/bin/bash
###############################################################################
# piRecord.sh - bash script for running PiRecord
# Author: John Hnatt
# Copyright 2019. All Rights Reserved.
# Version History:
#   mm/dd/yy    jhnatt    fix directory name
###############################################################################

myPid=0
usage()
{
	echo "USAGE: piRecord [start|stop|restart|status|config|listrecs|delrecs|showlog|clearlog|help]"
}

is_running()
{
        ps -f -C "python" | grep -q 'piRecord.py'
}

areyousure()
{
	read -p "are you sure (y/n)? " ans
	[ "$ans" == "y" ]	
}

start()
{
	cd /home/pi/PiRecord
	rm -f .myfifo
	python ./piRecord.py &
	echo $! >.mypid
	echo "piRecord runing, pid = $!"
}

stop()
{
	if is_running; then
		pkill -SIGTERM python
		echo 0 >.mypid
	else
		echo "piRecord is already stopped."
	fi
}

restart()
{
	stop
	sleep 1
	start
}


status()
{
	if is_running; then
  		echo "piRecord is running."
	else
		echo "piRecord is stopped."	
	fi
}

config()
{
	echo "cmd not supported yet..."
}

listrecs()
{
	ls -l ../Recordings
}

delrecs()
{
	if areyousure; then
		rm -f ../Recordings/*
		echo "recordings deleted."
	else
		echo "delete aborted."
	fi
}

showlog()
{
	more "./piRecord.log"
}

clearlog()
{
	if areyousure; then
		rm -f ./piRecord.log
		echo "log is deleted."
	else
		echo "delete aborted."
	fi
}

sendsig()
{
	read -r myPid <.mypid
	echo "send SIGUSR$SIGNUM to $myPid..."
	if [ $myPid != 0 ]; then
        	kill -SIGUSR$SIGNUM $myPid
		echo "SIGUSR$SIGNUM sent"
	else
		echo "invalid pid"
	fi	
}

help()
{
	echo "help not available yet..."
	usage
}

echo $0 $1 $2
case $1 in
	start)
		start
		;;
	stop)
		stop
		;;
	status)
		status
		;;
	restart)
		restart
		;;
	config)
		config
		;;
	listrecs)
		listrecs
		;;
	delrecs)
		delrecs
		;;
	showlog)
		showlog
		;;
	clearlog)
		clearlog
		;;
	sendsig)
		SIGNUM=$2
		sendsig
		;;
	help)
		help
		;;
	*)
		usage
		;;
esac


