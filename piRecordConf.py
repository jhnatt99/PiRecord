###############################################################################
# PiCorderConf.py - Raspberry Pi audio recorder configuration module
# Author: John Hnatt
# Copyright 2019. All Rights Reserved.
#   11/24/19    jhnatt    original
#   11/26/19    jhnatt    modify for Python 3
#   11/27/19    jhnatt    add performance tuning and user preferences
###############################################################################

import alsaaudio
import logging
import configparser

# Constants
UI_PROTO = 0
UI_LED_DISPLAY = 1

UI_DEFAULT = UI_PROTO

# Prototype Hardware configuration
protoSwPin  = 26                #GPIO 26
protoLedPin = 13                #GPIO 13
protoDebounce = 0.02            #debounce time = 20 ms 

# File namimng configuration
outputDir = "../Recordings"
fileFormatStr = "%Y%m%d_%H%M%S"
fileTypeExt = ".wav"


#global record configuration variables.  Initialize with default values.
recDevice = "default"    
recChannels = 1
recRate = 44100
recFormat = alsaaudio.PCM_FORMAT_S16_LE
recPeriodSize = 160
recSampleWidth = 2

#Performance tuning
engineLoopPd = 0.001    
swDebounceTime = 0.020

#User preferences 
idleSeconds = 300.000  
auditionTime = 3.00


#Config item display lists (exported to main which handles settings)
cfgItemDispList = ["Dev", "Chn", "Rat", "Fmt", "Per", "Wid"]

#Logging configuration
LOG_LVL_DBG = 15  #define higher than regular debug to keep from flooding with ALSA debug messages 
logLevel = LOG_LVL_DBG
logFile = './piRecord.log'
logFormat = '%(asctime)s %(levelname)s:  %(message)s'

logging.basicConfig(filename=logFile,format=logFormat,level=logLevel)

#Create configuration parser object
recConfig = configparser.RawConfigParser()

###############################################################################
# Function Name:
#   printConfig
# Description:
#   prints the current configuration
# Parameters:
#   none
# Return value: 
#   0
###############################################################################
def printConfig():
    global recConfig
    global recDevice, recChannels, recRate, recFormat, recPeriodSize, recSampleWidth
    global swDebounceTime, engineLoopPd, idleSeconds, auditionTime
    print ("Current Recording Config:")
    print ("  recDevice = ", recDevice)
    print ("  recChannels = ", recChannels)
    print ("  recRate = ", recRate)
    print ("  recFormat = ", recFormat)
    print ("  recPeriodSize = ", recPeriodSize)
    print ("  recSampleWidth = ", recSampleWidth)
    print ("Performance Tuning:")
    print ("  swDebounceTime: ", swDebounceTime)
    print ("  engineLoopPd: ", engineLoopPd)
    print ("User Preferences: ")
    print ("  idleSeconds", idleSeconds)
    print ("  auditionTime", auditionTime)
    print (" ")
    print ("to change a setting, edit piRecord.cfg and restart piRecord")
    return 0

###############################################################################
# Function Name:
#   getRecDevice
# Description:
#   this function obtains the list of available devices from ALSA and finds the 
#   one matching the configured device.
# Parameters:
#   none
# Return value: 
#   device name, else null if device not found.
###############################################################################
def getRecDevice():
    devList = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
    for dev in devList:
        if recDevice in dev:
           return dev
    return 'null'

###############################################################################
# Function Name:
#   getRecFormat
# Description:
#   this function converts the individual format parameters into the single
#   constant used by the ALSA library.
# Parameters:
#   numBits: number of bits (8, 16, or 32)
#   signed:  True = signed, False = unsigned
#   byteOrder: LE = little endian, BE = big endian
# Return value: 
#   the resulting constant.
###############################################################################
def getRecFormat(numBits, signed, byteOrder):
    if signed == False:
        if byteOrder == 'BE':
            if numBits == 8:
                fmt = alsaaudio.PCM_FORMAT_U8
            elif numBits == 24:
                fmt = alsaaudio.PCM_FORMAT_U24_BE
            elif numBits == 32:
                fmt = alsaaudio.PCM_FORMAT_U32_BE
            else:
                fmt = alsaaudio.PCM_FORMAT_U16_BE
        else:
            if numBits == 8:
                fmt = alsaaudio.PCM_FORMAT_U8
            elif numBits == 24:
                fmt = alsaaudio.PCM_FORMAT_U24_LE
            elif numBits == 32:
                fmt = alsaaudio.PCM_FORMAT_U32_LE
            else:
                fmt = alsaaudio.PCM_FORMAT_U16_LE
    else:
        if byteOrder == 'BE':
            if numBits == 8:
                fmt = alsaaudio.PCM_FORMAT_S8
            elif numBits == 24:
                fmt = alsaaudio.PCM_FORMAT_S24_BE
            elif numBits == 32:
                fmt = alsaaudio.PCM_FORMAT_S32_BE
            else:
                fmt = alsaaudio.PCM_FORMAT_S16_BE
        else:
            if numBits == 8:
                fmt = alsaaudio.PCM_FORMAT_S8
            elif numBits == 24:
                fmt = alsaaudio.PCM_FORMAT_S24_LE
            elif numBits == 32:
                fmt = alsaaudio.PCM_FORMAT_S32_LE
            else:
                fmt = alsaaudio.PCM_FORMAT_S16_LE
    
    return fmt

###############################################################################
# Function Name:
#   getRecDevDevConfig
# Description:
#   this function obtains the configuration from the config file piRecord.cfg.
# Parameters:
#   none
# Return value: 
#   0
###############################################################################
def getRecDevConfig():
    global recConfig
    global recDevice, recChannels, recRate, recFormat, recPeriodSize, recSampleWidth
    global swDebounceTime, engineLoopPd, idleSeconds, auditionTime

    recConfig.read('piRecord.cfg')

    #get recording configuration
    recDevice = recConfig.get('recDevice', 'devName')
    recChannels = recConfig.getint('recDevice', 'numChan')
    recRate = recConfig.getint('recDevice', 'rate')
    recFormat = getRecFormat(recConfig.getint('recDevice', 'numBits'), recConfig.getboolean('recDevice', 'signed'), recConfig.get('recDevice', 'byteOrder'))
    recPeriodSize = recConfig.getint('recDevice', 'periodSize')
    recSampleWidth = recConfig.getint('recDevice', 'sampleWidth')
    
    #get performance tunings:
    swDebounceTime = recConfig.getfloat('performanceTuning', 'swDebounceTime')
    engineLoopPd = recConfig.getfloat('performanceTuning', 'engineLoopPd')

    #get user preferences:
    idleSeconds = recConfig.getfloat('userPreferences', 'idleSeconds')
    auditionTime = recConfig.getfloat('userPreferences', 'auditionTime')

    return 0


###############################################################################
# Function Name:
#   __main__to be 
# Description:
#   the main function for the piRecordCfg module.  Allows module to run standalone
#   from command line to display configuration.
# Parameters:
#   none
# Return value: 
#   none
###############################################################################
if __name__ == "__main__":
    getRecDevConfig()
    printConfig()
    print ("\nList of available record devices:")
    devList = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
    for dev in devList:
        print ("  ", dev)
    print ("Record device in use = ", getRecDevice())

