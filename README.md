# PiRecord
Raspberry Pi Audio Recorder

This project turns a Raspberry Pi into a standalone USB audio recorder.  Being a part-time gigging musician, I wanted to create a compact standalone device with which I could record myself from the USB out on my mixer, rather than having to lug a laptop to every gig. 

It uses the following hardware component for the display and switches from AdaFruit:

https://learn.adafruit.com/adafruit-16x2-character-lcd-plus-keypad-for-raspberry-pi

Note that this device is a kit that needs to be assembled, so you will need to do some soldering. The link above includes assembly directions and links to the Python library needed to use it.

THis project also uses the following ALSA python library to do the audio processing:

https://larsimmisch.github.io/pyalsaaudio/

TODO: add details on how to load and configure the Raspberry Pi for PiRecord.  
