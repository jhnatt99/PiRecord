###############################################################################
# PiCorderEngine.py - Raspberry Pi audio recorder record/playback engine module
# Author: John Hnatt
# Copyright 2019. All Rights Reserved.
# Version History:
#   11/24/19  jhnatt    original
#   11/26/19  jhnatt    modify for Python 3
#   11/26/19  jhnatt    configurable engine loop time, other changes
###############################################################################

import multiprocessing
import alsaaudio
import piRecordConf
import piRecordUtils
import time
import wave

# Message ids used to send to command queue 
REQ_REC_START = 1
REQ_REC_STOP = 2
REQ_REC_CONT = 3
#TODO: support playback
REQ_PLY_START = 4
REQ_PLY_STOP = 5
REQ_PLY_CONT = 6

# Initialize global variables
curr_filename = "$"
recording = False
pEngine = None
recPCM = None

# Debug vars
data_cnt = 0
nodata_cnt = 0

###############################################################################
# Function Name:
#   start_record
# Description:
#   called externally to start the recording process by sending a start request
#   to the engine 
# Parameters:
#   none
# Return value: 
#   0 = success else error
###############################################################################
def start_record():
    global curr_filename
    global recording
    status = 0
    print ("\n**NEW RECORDING**")
    print ("start_record() called, recording = ", recording)
    if recording == False:
        curr_filename = piRecordUtils.getNextFilename()
        piRecordUtils.setCurrentFilename(curr_filename)
        if status == 0:  #no error
            pQueue.put(REQ_REC_START)
            print ("REQ_REC_START sent.")
            recording = True
    return status == 0

###############################################################################
# Function Name:
#   stop_record
# Description:
#   called externally to stop the recording process by sending a stop request
#   to the engine
# Parameters:
#   none
# Return value: 
#   0 = success else error
###############################################################################
def stop_record():
    global recording
    status = 0
    print ("stop_record() called, recording = "), recording
    if recording == True:
        pQueue.put(REQ_REC_STOP)
        print ("REQ_REC_STOP sent" )
        recording = False
    return status == 0

###############################################################################
# Function Name:
#   audition
# Description:
#   plays a short excerpt from the last recording made
# Parameters:
#   duration - length of excerpt in seconds
# Return value: 
#   0
###############################################################################
def audition(duration):

    if curr_filename == '$':
        return -1
    f = wave.open(curr_filename, 'rb')
    device = alsaaudio.PCM(device=piRecordConf.getRecDevice())
    # Set attributes
    device.setchannels(f.getnchannels())
    device.setrate(f.getframerate())

    # 8bit is unsigned in wav files
    if f.getsampwidth() == 1:
        device.setformat(alsaaudio.PCM_FORMAT_U8)
    # Otherwise we assume signed data, little endian
    elif f.getsampwidth() == 2:
        device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    elif f.getsampwidth() == 3:
        device.setformat(alsaaudio.PCM_FORMAT_S24_LE)
    elif f.getsampwidth() == 4:
        device.setformat(alsaaudio.PCM_FORMAT_S32_LE)
    else:
        print ("Playback error: unsupported format")
        return (-1)
    
    periodsize = int(f.getframerate() / 8)

    device.setperiodsize(periodsize)

    elapsed_time = 0.000
    start_time = time.time();
    data = f.readframes(periodsize)
    while data and (elapsed_time < duration):
        device.write(data)
        data = f.readframes(periodsize)
        elapsed_time = time.time() - start_time
    f.close()

    return 0

###############################################################################
# Function Name:
#   stop_process
# Description:
#   stops the recording engine process (called upon program termination)
# Parameters:
#   none
# Return value: 
#   0
###############################################################################
def stop_process():
    #TODO: stop/cleanup any recording in process
    pEngine.terminate()
    return 0

###############################################################################
# Function Name:
#   piRecordEngine
# Description:
#   function that serves as the engine for the recording and playback process.
#   It is spawned as a process and monitors the message queues for record/playback
#   commands. 
# Parameters:
#   none
# Return value: 
#   0
###############################################################################   
def piRecordEngine():
    global data_cnt, nodata_cnt
    global recPCM

    # initialize local variables
    curr_fd = 0
    sleep_time = piRecordConf.engineLoopPd
    cnt = 0
    rec_in_progress = False

    # enter loop...    
    while True:

        # wait for the next request from the message queue 
        req = pQueue.get()

        # handle start record requests:       
        if req == REQ_REC_START:
            print ("REQ_REC_START received, calling do_record_start")
            curr_fd = handle_record_start_req()
            init_record_input()
            rec_in_progress = True
            data_cnt = 0
            nodata_cnt = 0
            pQueue.put(REQ_REC_CONT)

        # hanlde stop record requests:
        elif req == REQ_REC_STOP:
            print ("REQ_STOP received, calling do_record_stop")
            handle_record_stop_req(curr_fd)
            rec_in_progress = False
            print ("data_cnt = ", data_cnt)
            print ("nodata_cnt = ", nodata_cnt)

        # handle continue record requests:
        elif req == REQ_REC_CONT:
            if rec_in_progress == True:
                handle_record_continue_req(curr_fd, recPCM)
                time.sleep(sleep_time)
                pQueue.put(REQ_REC_CONT)
                cnt = cnt + 1
                if cnt >= 500:
                    cnt = 0
                    print (".....")
            else:
                print ("Recording has stopped...")
    
    return 0

###############################################################################
# Function Name:
#   init_record_input
# Description:
#   creates a new recoridng input object if not already created, then sets its
#   attributes according to the configuration
# Parameters:
#   none
# Return value: 
#   0
###############################################################################
def init_record_input():
    global recPCM
    device = piRecordConf.recDevice
    
    # create the recording input object
    if recPCM == None:
        recPCM = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, device=piRecordConf.getRecDevice())

    # Set attributes based on the current recording configuration
    recPCM.setchannels(piRecordConf.recChannels)
    recPCM.setrate(piRecordConf.recRate)
    recPCM.setformat(piRecordConf.recFormat)
    recPCM.setperiodsize(piRecordConf.recPeriodSize)

    #return the recording input object
    return 0

###############################################################################
# Function Name:
#   handle_record_start_req
# Description:
#   handles record start requests by opening the wave file for writing.
# Parameters:
#   none
# Return value: 
#   the file descriptor for the wave file
###############################################################################
def handle_record_start_req():
    curr_fn = piRecordUtils.getCurrentFilename()
    print ("handle_record_start_req: open file", curr_fn, "here...")
    fd = wave.open(curr_fn, 'wb')
    fd.setnchannels(piRecordConf.recChannels)
    fd.setsampwidth(piRecordConf.recSampleWidth)
    fd.setframerate(piRecordConf.recRate)
    return fd

###############################################################################
# Function Name:
#   handle_record_stop_req
# Description:
#   handles the record stop request by writing null and closing the file
# Parameters:
#   fd - file descriptor of the currenly open wave file
# Return value: 
#   0
###############################################################################
def handle_record_stop_req(fd):
    print ("handle_record_stop_req: close file here...")
    fd.writeframes(''.encode())
    fd.close()
    return 0

###############################################################################
# Function Name:
#   handle_record_continue_req
# Descripton:
#   handles the record continue request by reading data from the recording 
#   input and writing it to the currently opened file 
# Parameters:
#   fd - file descriptor of the currenly open wave file
#   inp - the recording input object
# Return value: 
#   0
###############################################################################
def handle_record_continue_req(fd, inp):
    global data_cnt, nodata_cnt
    lngth, data = inp.read()
    if lngth:
        fd.writeframesraw(data)
        data_cnt += 1
    else:
        nodata_cnt += 1
    return 0

###############################################################################
# Main code
###############################################################################
# create the mesage queue and start the engige
pQueue = multiprocessing.Queue()
pEngine = multiprocessing.Process(target=piRecordEngine)
pEngine.start()




