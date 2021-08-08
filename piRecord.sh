#!/bin/bash
###############################################################################
# piRecord.sh - bash script for running PiRecord
# Author: John Hnatt
# Copyright 2019. All Rights Reserved.
# Version History:
#   11/25/19    jhnatt    fix directory name
#   11/26/19    jhnatt    support Python 3 (only)
#   11/27/19    jhnatt    configurable recording dir, run from current directory,
#                         add playback of last recording, other changes
###############################################################################

PROGDIR="/home/pi/PiRecord"
RECDIR="/home/pi/Recordings"

CFGFILE="$PROGDIR/piRecord.cfg"
LOGFILE="$PROGDIR/piRecord.log"
PROGFILE="$PROGDIR/piRecord.py"
CFGPROGFILE="$PROGDIR/piRecordConf.py"
CURRFNFILE="$PROGDIR/.currfn"

myPid=0
usage()
{
    echo "USAGE: piRecord [start|stop|restart|status|config|listrecs|delrecs|showlog|clearlog|playback|help]"
}

is_running()
{
    ps -f -C "python3" | grep -q 'piRecord'
}

areyousure()
{
    read -p "are you sure (y/n)? " ans
    [ "$ans" == "y" ]    
}

start()
{
    rm -f .myfifo
    python3 $PROGFILE &
    echo $! >.mypid
    echo "piRecord runing, pid = $!"
}

stop()
{
    if is_running; then
        #TODO: ensure other python programs don't get killed
        sudo pkill -SIGTERM python
        echo 0 >.mypid
    else
        echo "piRecord is already stopped."
    fi
}

restart()
{
    stop
    sleep 3
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
    python3 $CFGPROGFILE
}

listrecs()
{
    ls -l $RECDIR
    echo " "
    df -h --output=avail,used,pcent $RECDIR
}

delrecs()
{
    echo "about to delete contents from $RECDIR:"
    if areyousure; then
        rm -f $RECDIR/*
        echo "recordings deleted."
        echo " "
        df -h --output=avail,used,pcent $RECDIR
    else
        echo "delete aborted."
    fi
}

showlog()
{
    more $LOGFILE
}

clearlog()
{
    if areyousure; then
        rm -f $LOGFILE
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

playback()
{
    read -r pbfile <$CURRFNFILE
    aplay $pbfile
}

help()
{
    usage
    
    echo "start - starts the piRecord program"
    echo "stop - stops the piRecord program"
    echo "restart - stops the currently running piRecord program and restarts it"
    echo "status - prints the run status of the piRecord program (running or stopped)""
    echo "config - lists the piRecord configuration"
    echo "listrecs - lists the recording files in the recording directory"
    echo "delrecs - deletes all recordings in the recording directory"
    echo "showlog - shows the program logfile"
    echo "clearlog - clears the program logfile"
    echo "playback - plays back the last file recorded"
    echo "help - this menu

}

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
    playback)
        playback
        ;;
    help)
        help
        ;;
    *)
        usage
        ;;
esac


