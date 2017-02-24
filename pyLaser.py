#!/usr/bin/python

import serial #pyserial
# from PIL import Image
# from PIL import ImageTk
# from PIL import ImageFilter
import time

_ORIGINAL_ARTHOR_ = "AppliedEllippsis"
_VERSION_ = "0.1a"
_LICENSE_ = "See License.txt, but GPLv3 for the lazy"

usb_port = "com19"
baund_rate = 115200

ser = serial.Serial(
    port=usb_port,
    baudrate=baund_rate,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = 1
)

def set_laser_speed(speed): # 0-250 
  ser.write( ("17" + format(speed,"02x") + "00000000ff").decode("hex") )

def set_laser_position(x,y): # X and Y range: 0-512 
  # note will not always take direct path if large gaps, keep it small if doing vector with laser on
  # time.sleep(0.01) is recommended after for smooth movement
  # use power 9 max, power 10 does not work properly with positioning
  pos_x = format(x/100,"02x") + format(x%100,"02x")
  pos_y = format(y/100,"02x") + format(y%100,"02x")
  cmd = ("18" + pos_x + pos_y + "00ff")
  # print "(" + str(x) + "," + str(y) + ") " + cmd
  ser.write( cmd.decode("hex") )



laser_buff_min = 60
laser_buff_max = 121
laser_buff = laser_buff_min

def draw_laser_pixel(x,y): # X and Y range: 0-512 
  global laser_buff, laser_buff_max
  # print laser_buff
  laser_buff += 1
  laser_buff = laser_buff%laser_buff_max
  if laser_buff == 0:
    print "Buffer Reset"
    laser_buff = laser_buff_min +1
    # print get_laser_resp()
    # raw_input("Press Enter to continue...")
    # wait_on_ready_status()

  # note will not always take direct path if large gaps, keep it small if doing vector with laser on
  # time.sleep(0.01) is recommended after for smooth movement
  pos_x = format(x/100,"02x") + format(x%100,"02x")
  pos_y = format(y/100,"02x") + format(y%100,"02x")
  cmd = (format(laser_buff,"02x") + pos_x + pos_y + "00ff")
  # cmd = ("44" + pos_x + pos_y + "00ff")
  print "(" + format(x,"03") + "," + format(y,"03") + ") " + '-'.join(a+b for a,b in zip(cmd[::2], cmd[1::2]))
  ser.write( cmd.decode("hex") )
  # raw_input("Press Enter to continue...")

def set_laser_move(direction): # Moves laser without x,y towards a direction 1=up, 2=down, 3=left, 4=right
  ser.write( ("19" + format(direction,"02x") + "00000000ff").decode("hex") )


def init_laser(): # seems optional but returns some nice to have info
  ser.write( ("1a0000000000ff").decode("hex") )
  return get_laser_resp()


def set_laser_box(x1, y1, x2, y2): # X and Y range: 0-512 
  pos_x1 = format(x1/100,"02x") + format(x1%100,"02x")
  pos_y1 = format(y1/100,"02x") + format(y1%100,"02x")
  pos_x2 = format(x2/100,"02x") + format(x2%100,"02x")
  pos_y2 = format(y2/100,"02x") + format(y2%100,"02x")
  # ser.write("ffffffff")
  ser.write(("1B" + pos_x1 + pos_y1 + "00FF").decode("hex"))
  ser.write(("1B" + pos_x2 + pos_y2 + "01FF").decode("hex"))
  ser.write(("1C0000000000FF").decode("hex"))


def stop_laser_job_center(): # take box and find center, don't do write in function 41,84 
  set_laser_position(0,0) # change to center of x,y later
  # ser.write("180128005400FF".decode("hex")) # original data from sample


def set_laser_power(power): # range 0-10 (Don't use 10, it messes up movement)
  ser.write( ("33" + format(power,"02x") + "00000000ff").decode("hex") )


def set_fan_speed(speed): # range 0-10
  ser.write( ("34" + format(speed,"02x") + "00000000ff").decode("hex") )


def set_motor_speed(speed): # range 0-100 recommended 60-75
  # ser.write( ("150000000000ff").decode("hex") )
  # set_laser_box(0,0,150,150)
  # ser.write( ("360000000000ff").decode("hex") )
  # return get_laser_resp()
  ser.write( ("37" + format(100-speed,"02x") + "00000000ff").decode("hex") )
  # set_laser_position(0,0)

def reboot_laser(): # returns same info as init
  ser.write( ("fe0000000000ff").decode("hex") )
  return get_laser_resp()


def get_laser_resp(): # 140 or timeout defined in serial connection
  return ser.read(140).encode("hex") 

def wait_on_ready_status():
  while 1:
    print 'getting resp...'
    resp = get_laser_resp()
    print resp
    if "ffff" in resp:
      resp = resp.split("ffff")
      print resp[-2]
      if resp[-2] == '3e02':
        break
      else:
        print 'waiting 1...'
        time.sleep(0.1)
    else:
      print 'waiting 2...'
      time.sleep(0.1)

def parse_init_resp(resp):
  for row in resp.split("ffff"):
    if row[0:4] == '3e28':
      s = row[4:18]
      print 'UID: ' + '-'.join(a+b for a,b in zip(s[::2], s[1::2]))
    if row[0:4] == '3e29': # still trying to figure out how the time works, seems to follow some conventions mm hh, where hh is 4+val, and mm changes from  95 + 04 (/12) = 8.25 hr .25*60=15 min, the actual val, or nn - 40, if negative  60 - it,
      print 'Power On Time: ' + row[4:]
      mins = ord(row[4:6].decode("hex")) - 40
      if mins < 0:
        mins += 60
      print 'Power On Time Min: ' + str(mins)
    if row[0:4] == '3e2a':
      calc = ""
      for x in range(4,12,2):
        calc = str(ord(row[x:x+2].decode("hex"))) + calc
      print 'Power Up Times: ' + calc
    if row[0:4] == '3e2b':
      print 'Complete Times: ' + str(ord(row[4:6].decode("hex")))
    if row[0:4] == '3e2c':
      print 'Firmware Version: ' + str(ord(row[4:6].decode("hex"))) + '.' + str(ord(row[6:8].decode("hex")))
  # SAMPLE Response Data
  # 3E 07 FFFF (same every time)
  # 3E 28 {-UIDREMOVED=} FFFF # uid
  # 3E 29 5F040000000000 FFFF # 95 + 04 (/12) = 8.25 hr .25*60=15 min
  # 3E 2A 2B610500000000 FFFF # 43 97 05 power up times order last mid first : 59743
  # 3E 2B 10000000000000 FFFF # 16 complete times
  # 3E 2C 02040000000000 FFFF # fw version v2.4
  # 3E 2D 32000000000000 FFFF # 50 (same every time), don't know what this is
  # another one as a long string
  # 3E07FFFF3E28{-UIDREMOVED=}FFFF3E295F040000000000FFFF3E2A2B610500000000FFFF3E2B10000000000000FFFF3E2C02040000000000FFFF3E2D32000000000000FFFF

  # Trying to figure out Power On Time data
  # 3E 29 5F040000000000 FFFF # 95 + 04 (/12) = 8.25 hr .25*60=15 min
  # 3E 29 13050000000000 FFFF # 63 + 05 = 8hr 39 min
  # 3E 29 1A050000000000 FFFF # 26 + 05 = 8h 46m
  # 3e 29 2e050000000000 # 46 = 9h 6-8m???   nn - 40, if negative  60 - it, hr 4+
  # 3e 29 33050000000000 # 51 = 9h 11m
  # 3e 29 34050000000000 # 52 = 9h 12m
  # 3e 29 35050000000000 # 53 = 9h 13m
  # 3e 29 41050000000000 # 65 = 9h 25m
  # 3e 29 44050000000000 #    = 9h 28m
  # 3e 29 02060000000000 # 02   = 10h 02m



# below is a sample dance of the laser to show how to use some things
parse_init_resp(init_laser())
time.sleep(0.1)
# wait_on_ready_status()
# set_laser_power(10) # just a visible laser, nothing really will cut
# raw_input("Press Enter to start the dance...")


# attempting at drawing a line with a break using raster api
# print "set_laser_power 0"
# set_laser_power(0) # just a visible laser, nothing really will cut
# # time.sleep(0.1)
# # wait_on_ready_status()
# print "set_fan_speed 10"
# set_fan_speed(10)
# # time.sleep(0.1)
# # wait_on_ready_status()
# print("set_motor_speed(65)")
# set_motor_speed(65)
# # wait_on_ready_status()
# print "set_laser_speed(105)"
# set_laser_speed(105)

# parse_init_resp(reboot_laser())
# time.sleep(2)

# 1B 00 05 00 20 00 FF # Box Sequence
# 1B 03 63 00 21 01 FF #
# 1C 00 00 00 00 00 FF #
# 18 00 05 00 20 00 FF # Move to position
# 15 01 01 00 00 00 FF # ? start draw mode

# print "set_laser_box(0,10,700,10)"
# set_laser_box(0,0,512,512)
# time.sleep(2)
# # wait_on_ready_status()
# print "set_laser_position(0,0)"
# set_laser_position(0,0)
# time.sleep(2)
# wait_on_ready_status()


# using raster drawing functions, draw //////     /////// type of shape
ser.write( ("15 01 01 00 00 00 FF").replace(' ','').decode("hex") ) # start draw mode
print get_laser_resp()

for y in range(10,25):
  for x in range(0,512):
    if not (x > 220+y and x<380+y):
      draw_laser_pixel(x,y)  # go line by line, it does not like angles with this mode
      time.sleep(0.105) # set to the same as the laser speed

ser.write(( (format(laser_buff,"02x") + " 09 09 09 09 09 FF").replace(' ','').decode("hex") )) # ending transmission of data

# print "set_laser_position(0,0)"
# set_laser_position(0,0)
# time.sleep(3)
# print "set_laser_position(512,512)"
# set_laser_position(512,512)
# time.sleep(3)

# print "set_laser_box(0,10,700,10)"
# set_laser_box(0,0,200,212)
# time.sleep(2)
set_laser_position(0,0)
time.sleep(2)
# time.sleep(4) # set to the same as the laser speed
# print "set_fan_speed 10"
# set_fan_speed(10)
print "set_laser_power 9"
set_laser_power(9) # just a visible laser, nothing really will cut

for x in range(0,513, 4):
  set_laser_position(x,x)
  time.sleep(0.2) # set to the same as the laser speed

# print "set_laser_power 0"
# set_laser_power(0) # just a visible laser, nothing really will cut
# print "set_fan_speed 0"
# set_fan_speed(0)
print "set_laser_power 1"
set_laser_power(1) # just a visible laser, nothing really will cut



# print get_laser_resp()
# # warning end

# print get_laser_resp()
# 44 01 07 00 1D 00 FF
# 45 01 08 00 1D 00 FF
# 46 01 09 00 1D 00 FF
# 47 01 0A 00 1D 00 FF

# ser.write( ("44 01 d3 01 3D 00 FF").replace(' ','').decode("hex") )
# ser.write( ("45 01 05 00 1D 00 FF").replace(' ','').decode("hex") )
# ser.write( ("46 01 04 00 1D 00 FF").replace(' ','').decode("hex") )
# ser.write( ("47 01 03 00 1D 00 FF").replace(' ','').decode("hex") )

# print "set_laser_position(0,0)"
# set_laser_position(0,0)
# time.sleep(5)

# print "\nAre you ready for the Chinese Laser Dance?"
# raw_input("Press Enter to start the dance...")
# print("set_motor_speed(65)")
# set_motor_speed(65)
# print "set_laser_speed(15)"
# set_laser_speed(15)
# print "set_laser_power 1"
# set_laser_power(1) # just a visible laser, nothing really will cut
# time.sleep(0.1)
# print "set_fan_speed 10"
# set_fan_speed(10)
# time.sleep(0.1)
# print "it's goot to go 0,0 -> 512,512, 0,0 for calibration of motors before tasks, you can also draw boxes"
# print "set_laser_position(0,0)"
# set_laser_position(0,0)
# time.sleep(5)
# print "set_laser_position(512,512)"
# set_laser_position(512,512)
# time.sleep(5)
# print "set_laser_power 1... pew"
# set_laser_power(1)
# time.sleep(1)
# print "set_laser_position(0,0)"
# set_laser_position(0,0)
# time.sleep(5)
# print "Top left to bottom right, angle"
# for x in range(0,513):
#   set_laser_position(x,x)
#   time.sleep(0.01)
# time.sleep(2)
# print "set_fan_speed 1"
# set_fan_speed(1)
# time.sleep(0.1)
# print "bottom left to top right, angle"
# for x in range(0,513):
#   set_laser_position(513-x,x)
#   time.sleep(0.01)
# time.sleep(2)
# print "bottom left to top left, angle, switcheroo"
# for x in range(0,513):
#   if x > 256:
#     set_laser_position(513-x,513-x)
#   else:
#     set_laser_position(x,513-x)
#   time.sleep(0.01)
# time.sleep(2)
# print "set_laser_position(30,20)"
# set_laser_position(30,20)
# time.sleep(5)
# print "Rebooting laser"
# parse_init_resp(reboot_laser())
# time.sleep(5)
# print "set_fan_speed 5"
# set_fan_speed(5)
# time.sleep(0.1)
# print "set_laser_box(100,100,150,150)"
# set_laser_box(100,100,150,150)
# time.sleep(2)
# print "set_laser_box(0,0,150,150)"
# set_laser_box(0,0,150,150)
# time.sleep(2)
# print "set_laser_box(10,100,50,50)"
# set_laser_box(10,100,50,50)
# time.sleep(2)
# print "set_laser_box(10,10,20,20)... Machine Gun #1"
# set_laser_box(10,10,20,20)
# time.sleep(2)
# print "set_laser_box(100,50,105,55)... Machine Gun #2"
# set_laser_box(100,50,105,55)
# time.sleep(2)
# print "set_laser_box(0,0,512,0)... Fax Machine"
# set_laser_box(0,0,512,0)
# time.sleep(4)
# print "set_laser_box(0,0,0,512)... Flatbed Scanner"
# set_laser_box(0,0,0,512)
# time.sleep(2)
# print "set_laser_box(25,10,150,50)"
# set_laser_box(25,10,150,50)
# time.sleep(2)
# print "set_fan_speed 10"
# set_fan_speed(10)
# time.sleep(0.1)
# print "set_laser_position(200,403)"
# set_laser_position(200,403)
# time.sleep(2)
# print "Rebooting laser, because why not"
# parse_init_resp(reboot_laser())
# time.sleep(2)
# print "set_laser_position(512,220)"
# print "set_laser_power 10... pew"
# set_laser_power(10)
# time.sleep(1)
# print "set_laser_power 0"
# set_laser_power(0)
# time.sleep(1)
# print "set_laser_power 10... {pew} pew"
# set_laser_power(10)
# time.sleep(1)
# print "set_laser_power 0"
# set_laser_power(0)
# time.sleep(1)
# print "set_laser_power 10... {pew pew} pew"
# set_laser_power(10)
# time.sleep(1)
# print "set_laser_power 0"
# set_laser_power(0)
# time.sleep(1)
# set_laser_position(512,220)
# print "set_fan_speed 0"
# set_fan_speed(0)
# time.sleep(0.1)

print '\nDone, now wasn\'t that dance fun?'