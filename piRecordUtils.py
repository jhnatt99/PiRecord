
###############################################################################
# PiCorderUtils.py - Raspberry Pi audio recorder utility module
# Author: John Hnatt
# Copyright 2019. All Rights Reserved.
# Version History:
#   11/24/19    jhnatt    original
###############################################################################

import datetime
import piRecordConf

###############################################################################
# Function Name:
#   getNextFilename  
# Description:
#   generates the filename to be used for a newly-started recording
# Parameters:
#   none
# Return value: 
#   the filename
###############################################################################
def getNextFilename():
    nextFilename = piRecordConf.outputDir + "/" + datetime.datetime.now().strftime(piRecordConf.fileFormatStr) + piRecordConf.fileTypeExt 
    return(nextFilename)

###############################################################################
# Function Name:
#   getCurrentFilename 
# Description:
#   reads the current filename from the .currfn file
# Parameters:
#   none
# Return value: 
#   the filename
###############################################################################
def getCurrentFilename():
    fd = open("./.currfn","r")
    fn = fd.read()
    fd.close()
    return fn

###############################################################################
# Function Name:
#   setCurrentFilename
# Description:
#   overwrites the current filename in the .currfn file with that of the new 
#   current file
# Parameters:
#   newFilename - the new file
# Return value: 
#   0
###############################################################################
def setCurrentFilename(newFilename):
    fd = open("./.currfn", "w+")
    fd.write(newFilename)
    fd.close()
    return 0
