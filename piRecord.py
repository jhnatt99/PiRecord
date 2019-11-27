###############################################################################
# piCorder.py - Raspberry Pi audio recorder main module
# Author: John Hnatt
# Copyright 2019. All Rights Reserved.
#   11/24/19    jhnatt    original
#   11/25/19    jhnatt    sleep on idle state, 
#   11/26/19    jhnatt    modify for Python 3,  
###############################################################################

# TODO: describe the hardware (i.e. user interface module used)

import RPi.GPIO as GPIO
import signal
import time
import logging
import piRecordConf
import piRecordEngine
import piRecordUtils
import Adafruit_CharLCD as LCD    #library used to control the LCD module
import os
import errno

# switch debounce time
# TODO: make this configurable 
DEBOUNCE_TIME = 0.020

IDLE_SECONDS = 300.000  #5 minutes idle before sleeping

# Recorder states
IDLE_STATE = 0
BUSY_STATE = 1
ERROR_STATE = 2

# Operation Modes
STARTUP_MODE = 0 
RECORD_MODE = 1
PLAYBACK_MODE = 2
CONFIG_MODE = 3
UTIL_MODE = 4

# These are used to cycle through the operation modes when selecting the mode
FIRST_MODE = RECORD_MODE
LAST_MODE = UTIL_MODE

# values used to define initial submode and top of menu for each operation mode
INIT_SUBMODE = 0
TOP_SUBMODE = 1

# record submodes
REC_STOPPED=INIT_SUBMODE
REC_STANDBY=TOP_SUBMODE
REC_IN_PROG=REC_STANDBY+1
REC_ERROR=REC_IN_PROG+1

# config submodes
CFG_START=INIT_SUBMODE
CFG_SEL_ITEM=TOP_SUBMODE
CFG_CHANGE=CFG_SEL_ITEM+1
CFG_ERROR=CFG_CHANGE+1

# global variables to indicate current state and mode/submode of device
running = True
state = IDLE_STATE
run_mode = STARTUP_MODE
submode = 0
sleeping = False

# fifo used to allow commands to be sent from command line.  
# TODO (currently not working)
fifo = None
FIFO = ".myfifo"

# short constant defined for typing convenience
LOG_DBG = piRecordConf.LOG_LVL_DBG

#
# MENU DISPLAY LISTS: These lists contain the strings used to display various menu and submenu items
#

# The strings displayed when selecting the operation mode
mode_disp_list = ["STARTUP         ", 
                  "RECORD          ", 
                  "PLAYBACK        ", 
                  "CONFIG          ",
                  "UTILITY         "]

# strings used to display current operation mode
mode_disp_list_short = ["SUP", "REC", "PLY", "CFG", "UTL"]

# 2 dimensional list for the submodes defined for each mode
submode_disp_list = [["---         ", "            ", "             ", "            "], 
                     ["---         ", "Standby...  ", "Rec in prog  ", "Rec Error   "], 
                     ["---         ", "Sel file:   ", "Playing...   ", "Play Error  "], 
                     ["---         ", "Sel item:   ", "Changing...  ", "Error       "],
                     ["---         ", "sel utility ", "Running...   ", "Error       "]] 

# switch indices
SEL_SW = 0
UP_SW = 1
DOWN_SW = 2
LEFT_SW = 3
RIGHT_SW = 4
NUM_SW = 5

# object for controlling the LCD module object
lcd = LCD.Adafruit_CharLCDPlate()

# lists to manage each switch, refereced by the switch indices above
switch_list = [LCD.SELECT, LCD.UP, LCD.DOWN, LCD.LEFT, LCD.RIGHT]
switch_down_cnt = [0,0,0,0,0]
switch_down = [False, False, False, False, False]
switch_last = [False, False, False, False, False]

###############################################################################
# Function Name:
#   graceful_exit
# Description:
#   assures that the program will exit gracefully when device is shutdown.
#   Note: pulling the plug will not shut things down gracefully
#   TODO: add a power switch sequence to allow graceful shutdown on powerdown
#   (right now can only shut down this via terminal).
# Parameters:
#   none
# Return value: 
#   0
###############################################################################
def graceful_exit():
    piRecordEngine.stop_process()  #stop the engine 
    logging.info(">> piRecord has exited gracefully.")

    # display goodbye message on terminal and on device
    print ("goodbye.") 
    lcd.clear()
    lcd.message("goodbye!")

    # blank display after 3 seconds
    time.sleep(3.0)
    lcd.clear()
    lcd.set_color(0,0,0)

    # TODO: close fifo
    # if fifo != None:
    #     fifo.close()
    
    return 0

###############################################################################
# Function Name:
#   handle_stop_signals
# Description:
#   handle the signals from the kernel that will stop the program
# Parameters:
#   signum - the signal number
#   frame - current stack frame
# Return value: 
#   0
###############################################################################
def handle_stop_signals(signum,frame):
    global running
    running = False
    graceful_exit()
    return 0
   
# register the signals used to stop the program.
signal.signal(signal.SIGTERM, handle_stop_signals)
signal.signal(signal.SIGHUP, handle_stop_signals)
signal.signal(signal.SIGQUIT, handle_stop_signals)

###############################################################################
# Function Name:
#   process_command   
# Description:
#   processes PiRecord commands entered from the command line (TODO)
# Parameters:
#   
# Return value: 
#   0
###############################################################################
def process_command():
    # global fifo
    # TODO
    # if fifo != None:
    #    cmd=fifo.read()
    #    if len(cmd) > 0:
    #        print cmd, "received."
    return 0

###############################################################################
# Function Name:
#   process_sigusr
# Description:
#   processes user defined signals
# Parameters:
#   signum - the signal number
#   frame - current stack frame
# Return value: 
#   0
###############################################################################
def process_sigusr(signum,frame):
    #TODO: find use for signals.  For now just test.
    if (signum == signal.SIGUSR1):
        print ("SIGUSR1 received")
    elif (signum == signal.SIGUSR2):
        print ("SIGUSR2 received")
    else:
        print ("signal received: ", signum)
    return 0

# register user signals
signal.signal(signal.SIGUSR1, process_sigusr)
signal.signal(signal.SIGUSR2, process_sigusr)

###############################################################################
# Function Name:
#   display_submode
# Description:
#   displays the submode on the LCD screen
# Parameters:
#   mode - the mode for which the submode is to be displayed
#   submode - the submode to be displayed
# Return value: 
#   0
###############################################################################
def display_submode(mode,submode):
    lcd.set_cursor(0,0)
    lcd.message(submode_disp_list[mode][submode])
    return 0

###############################################################################
# Function Name:
#   display_mode
# Description:
#   displays the short mode string on the LCD screen. Also updates the submode 
# Parameters:
#   mode - the mode to be displayed
#   submode - the submode to be displayed
# Return value: 
#   0
###############################################################################
def display_mode(mode,submode):
    lcd.set_cursor(13,0)
    lcd.message(mode_disp_list_short[mode])
    display_submode(mode,submode)
    return 0

###############################################################################
# Function Name:
#   display_mode_selection
# Description:
#   displayes the long mode string on the LCD screen. Used when changing modes.
# Parameters:
#   mode - the mode to display
# Return value: 
#   0
###############################################################################
def display_mode_selection(mode):
    lcd.set_cursor(0,1)
    lcd.message(mode_disp_list[mode]);
    return 0

###############################################################################
# Function Name:
#   setmode
# Description:
#   sets the current operation mode to the new mode and updates the display
# Parameters:
#   newmode - the new mode
# Return value: 
#   0
###############################################################################
def set_mode(newmode):
   global run_mode
   global submode

   #update the operation mode and initialize its submode
   run_mode = newmode
   submode = INIT_SUBMODE

   #update the display
   display_mode(run_mode,submode)

   logging.log(LOG_DBG, "mode set to %d", run_mode)
   
   return 0

###############################################################################
# Function Name:
#   increment_mode
# Description:
#   increments the given mode with wraparound. Used when cycling through the 
#   mode selections.
# Parameters:
#   mode - the mode to be incremented
# Return value: 
#   the resulting mode value
###############################################################################
def increment_mode(mode):
    if mode == LAST_MODE:
       mode = FIRST_MODE
    else:
       mode += 1
    return mode

###############################################################################
# Function Name:
#   decrement_mode
# Description:
#   decrements the given mode with wraparound. Used when cycling through the 
#   mode selections.
# Parameters:
#   mode - the mode to be decremented
# Return value: 
#   the resulting mode value
###############################################################################
def decrement_mode(mode):
    if mode == FIRST_MODE:
       mode = LAST_MODE
    else:
       mode -= 1
    return mode

###############################################################################
# Function Name:
#   check_switches   
# Description:
#   checks the state of each switch and updats the switch status/count arrays 
#   accordingly
# Parameters:
#   none
# Return value: 
#   0
###############################################################################
def check_switches():
    
    for sw in range(SEL_SW, NUM_SW):

        # store last switch position
        switch_last[sw] = switch_down[sw];

        # if switch is down, set down status and increment down count
        if lcd.is_pressed(switch_list[sw]):
            switch_down[sw] = True
            switch_down_cnt[sw] += 1

        # else if switch up, clear switch down status and clear down count
        else:
            switch_down[sw] = False
            switch_down_cnt[sw] = 0

    return 0
          
###############################################################################
# Function Name:
#   switch_pressed
# Description:
#   checks whether or not a given switch has been pressed
# Parameters:
#   sw - the ID of the switch to be checked
# Return value: 
#   boolean indicating whether switch was pressed (True = pressed)
###############################################################################
def switch_pressed(sw):

    # if the switch is down but wasn't last time check_switch was run, it means
    # that the switch was pressed 
    if switch_down[sw]:
       if switch_last[sw] == False:
           logging.log(LOG_DBG, "sw %d pressed", sw)
           return True
    return False

###############################################################################
# Function Name:
#   any_switch_pressed
# Description:
#   checks whether or not any of the switches has been pressed
# Parameters:
#   none
# Return value: 
#   boolean indicating whether any switch was pressed (True = one was pressed)
###############################################################################
def any_switch_pressed():
    for sw in range(SEL_SW, NUM_SW):
        if switch_pressed(sw):
           # return True as soon as a pressed switch was found
           return True
    return False

###############################################################################
# Function Name:
#   do_record_mode
# Description:
#   this function handles all of the processing while in RECORD mode.  It
#   monitors buttons and acts on them to change submodes, update displays, 
#   start/stop recording, etc. 
# Parameters:
#   submode - the RECORD submode
# Return value: 
#   new_submode - the new submode if a submode change has taken place (returns 
#   the old if not)
###############################################################################
def do_record_mode(submode):
    global state

    # initialize the new submode return value to the current submode.  If no 
    # change takes place then we will remain in the current submode.
    new_submode = submode

    # if submode is STOPPED, we change immediately to STANDBY to get ready 
    # to record again.
    if submode == REC_STOPPED:
        new_submode = REC_STANDBY
        display_submode(RECORD_MODE,REC_STANDBY)
        lcd.set_cursor(0,1)
        lcd.message("Rt Btn to start ")

    # if submode is STANDBY, then we monitor the record switch.  If pressed we
    # start recording and change submode to REC_IN_PROG
    elif submode == REC_STANDBY:
        if switch_pressed(RIGHT_SW):
            logging.info("recording started")
            if piRecordEngine.start_record():
                new_submode = REC_IN_PROG
                state = BUSY_STATE
                display_submode(RECORD_MODE,REC_IN_PROG)
                lcd.set_cursor(0,1)
                lcd.message("Any Btn to stop ")
            else:
                # if there was an error in starting the recording, display it,
                # stop recording, and set state to ERROR .
                piRecordEngine.stop_record()
                new_submode = REC_ERROR
                state = ERROR_STATE
                display_submode(RECORD_MODE,REC_ERROR)
                lcd.set_cursor(0,1)
                lcd.message("Any Btn to clear")

    # if submode is REC_IN_PROG, check if any switch was pressed and if so, 
    # stop the recording and change state to STOPPED 
    elif submode == REC_IN_PROG:
        if any_switch_pressed():
            logging.info("recording stopped")
            piRecordEngine.stop_record()
            new_submode = REC_STOPPED
            state = IDLE_STATE
            display_submode(RECORD_MODE,REC_STOPPED)
            lcd.set_cursor(0,1)
            lcd.message("Stopped.        ")

    # if submode is ERROR, check if any switch pressed and if so, clear
    # the error and set state to STOPPED.
    elif submode == REC_ERROR:
        if any_switch_pressed():
            logging.info("rec err cleared")
            new_submode = REC_STOPPED
            STATE = IDLE_STATE
            display_submode(RECORD_MODE,REC_STOPPED)
            lcd.set_cursor(0,1)
            lcd.message("Cleared.        ")
    
    # return the new submode (which could be current submode, i.e. no change)
    return new_submode

###############################################################################
# Function Name:
#   do_playback_mode
# Description:
#   the handler for the PLAYBACK operation mode
# Parameters:
#   submode - the current submode
# Return value: 
#   new submode - the new submode
###############################################################################
def do_playback_mode(submode):
    new_submode = submode
    #TODO: add play logic
    return new_submode

# global config item count
cfgItemCnt = 0

###############################################################################
# Function Name:
#   do_config_mode 
# Description:
#   the handler for the CONFIG operation mode
# Parameters:
#   submode - the current submode
# Return value: 
#   new submode - the new submode
###############################################################################
def do_config_mode(submode):
    global cfgItemCnt

    # initialize return value to current submode
    new_submode = submode

    # handle the START submode: 
    if submode == CFG_START:
        logging.log(LOG_DBG, "submode set to CFG_START")
        new_submode = CFG_SEL_ITEM
        display_submode(CONFIG_MODE,CFG_SEL_ITEM)
        cfgItemCnt = 0
        lcd.set_cursor(0,1)
        lcd.message("                    ")
        lcd.set_cursor(0,1)
        lcd.message(piRecordConf.cfgItemDispList[cfgItemCnt]);
        #TOD show setting value

    # handle the SELECT ITEM submode:
    elif submode == CFG_SEL_ITEM:
        
        # if up/down button pressed, cycle through settings
        if switch_pressed(UP_SW):
            if cfgItemCnt == len(piRecordConf.cfgItemDispList)-1:
                cfgItemCnt = 0
            else:
                cfgItemCnt += 1
            lcd.set_cursor(0,1)
            lcd.message(piRecordConf.cfgItemDispList[cfgItemCnt]);
            #TODO show setting
        elif switch_pressed(DOWN_SW):
            if cfgItemCnt == 0:
                cfgItemCnt = len(piRecordConf.cfgItemDispList)-1
            else:
                cfgItemCnt -= 1
            lcd.set_cursor(0,1)
            lcd.message(piRecordConf.cfgItemDispList[cfgItemCnt]);
            #TODO: show setting

        #if left/right switch pressed, cycle through values for current setting
        #elif switch_pressed(LEFT_SW):
            #TODO decr setting value
        #elif switch_pressed(RIGHT_SW):
            #TODO incr setting value

        #if select switch pressed, enter CHANGE submode
        elif switch_pressed(SEL_SW):
            new_submode = CFG_CHANGE
            display_submode(CONFIG_MODE,CFG_CHANGE)

    #handle the CHANGE ITEM submode
    elif submode == CFG_CHANGE:
        #TODO: make the setting change
        new_submode = CFG_SEL_ITEM
        display_submode(CONFIG_MODE,CFG_SEL_ITEM)
        lcd.set_cursor(0,1)
        lcd.message("                    ")
        lcd.set_cursor(0,1)
        lcd.message(piRecordConf.cfgItemDispList[cfgItemCnt]);
        #TODO: show setting value
    return new_submode

###############################################################################
# Function Name:
#   do_utility_mode
# Description:
#   handleer for the UTILITY mode
# Parameters:
#   submode - the current submode
# Return value: 
#   new_submode - the new submode
###############################################################################
def do_utility_mode(submode):
    new_submode = submode
    #TODO
    return new_submode

###############################################################################
# Function Name:
#   put_to_sleep()
# Description:
#   puts the recorder to sleep by blanking the screen
# Parameters:
#   none
# Return value: 
#   0
###############################################################################
def put_to_sleep():
    global sleeping
    sleeping = True
    lcd.set_color(0,0,0)
    logging.log(LOG_DBG, "recorder put to sleep.")
    print ("Recorder put to sleep.")
    return 0

###############################################################################
# Function Name:
#   wake_up()
# Description:
#   wakes up the recorder by unblanking the screen
# Parameters:
#   none
# Return value: 
#   0
###############################################################################
def wake_up():
    global sleeping
    sleeping = False
    lcd.set_color(1,0,0)
    logging.log(LOG_DBG, "recorder awakened.")
    print ("Recorder awakened.")
    return 0

###############################################################################
# Function Name:
#   __main__  
# Description:
#   The main loop for the PiRecord program
# Parameters:
#   none
# Return value: 
#   none
###############################################################################
if __name__ == "__main__":
    cnt = 0
    test_cnt = 0
    select_mode = STARTUP_MODE

    # display copyright info on terminal and LCD display
    print ("piRecord 0.1")
    print ("Copyright 2019 by John Hnatt.  All rights reserved")
    logging.info(" ")
    logging.info("***** piRecord has started *****")    

    lcd.set_color(1,0,0)
    lcd.message("piRecord 0.1\n")
    lcd.message("(c) 2019 J Hnatt")
    time.sleep(2.0)
    lcd.clear()

    # display the configuration on the terminal
    piRecordConf.getRecDevConfig()
    piRecordConf.printConfig()

    #initialize local variables
    change_mode_in_prog = False
    change_mode_pending = False
    change_mode_cnt = 0
    idle_counter = 0
    prev_state = IDLE_STATE

    # Create message pipe to command line /bash shell script
    # TODO: figure out how to get this to work
    #try:
    #   os.mkfifo(FIFO)
    #except:
    #   print "error creating fifo"
    #fifo=open(FIFO, "r")
    #print  "after open, fifo = ", fifo
 
    # initialize mode to RECORD MODE
    set_mode(RECORD_MODE)

    try:
        # MAIN LOOP:
        while running:

            cnt += DEBOUNCE_TIME
            test_cnt += 1
            time.sleep(DEBOUNCE_TIME) # sleep to debounce

            check_switches()

            #only perform switch functionality when recorder is awake
            if sleeping == False:
            
                #CHECK IF ENTERING CHANGE MODE:
                #if SELECT button pressed, start 1 second counter, if down after one second
                #then enter change mode procedure.
                if switch_down[SEL_SW]:
                    if submode <= TOP_SUBMODE: #must be at top level of mode
                        if switch_last[SEL_SW] == False:
                            change_mode_pending = True
                            change_mode_cnt = 0
                        elif change_mode_in_prog == False:
                            change_mode_cnt += 1
                            if change_mode_cnt >= 1.000/DEBOUNCE_TIME:
                                change_mode_cnt = 0
                                change_mode_pending = False
                                change_mode_in_prog = True
                                select_mode = run_mode
                                lcd.set_cursor(0,0)
                                lcd.message("Sel Mode:    ")
                                display_mode_selection(select_mode)
                else: 
                    #button up, cancel change mode pending
                    if change_mode_pending == True:
                        change_mode_pending = False
                        change_mode_cnt = 0

                #CHANGE MODE PROCESSING
                #if we are in change mode, handle the up/down arrows and selection
                #for changeing the mode
                if change_mode_in_prog == True:
                    if  switch_pressed(UP_SW):
                            select_mode = increment_mode(select_mode)
                            display_mode_selection(select_mode)
                    if switch_pressed(DOWN_SW):
                            select_mode = decrement_mode(select_mode)
                            display_mode_selection(select_mode)
                    if switch_pressed(SEL_SW):
                            lcd.clear()
                            set_mode(select_mode)
                            change_mode_in_prog = False

                # if not in change mode, call the mode handler for the current operation mode
                else:
                    if run_mode == RECORD_MODE:
                        submode = do_record_mode(submode)
                    elif run_mode == PLAYBACK_MODE:
                        submode = do_playback_mode(submode)
                    elif run_mode == CONFIG_MODE:
                        submode = do_config_mode(submode)
                    elif run_mode == UTIL_MODE:
                        submode = do_utility_mode(submode)
                    else:
                        logging.error("Invalid Mode")
                        lcd.clear()
                        lcd.message("Invalid Mode!")
                        print ("Invalid Mode = ", mode)
            # endif not sleeping

            # do idle state sleep/wakeup stuff
            if state == IDLE_STATE:
                if any_switch_pressed():
                    idle_counter = 0
                    if sleeping:
                        wake_up()
                else:
                    if sleeping == False:
                        idle_counter += 1;
                        if idle_counter >= IDLE_SECONDS/DEBOUNCE_TIME:
                            put_to_sleep()
                            idle_counter = 0
            else:
                if sleeping:
                    wake_up()
                idle_counter = 0
            prev_state = state

    except KeyboardInterrupt: 
    # If CTRL+C is pressed, exit cleanly
        graceful_exit()
