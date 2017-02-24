#!/usr/bin/python

import serial #pyserial
# from PIL import Image
# from PIL import ImageTk
# from PIL import ImageFilter
import time


usb_port = "com11"
baund_rate = 115200

ser = serial.Serial(
    port=usb_port,
    baudrate=baund_rate,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout = 1
)


def set_laser_position(x,y): # X and Y range: 0-512 
  # note will not always take direct path if large gaps, keep it small if doing vector with laser on
  pos_x = format(x/100,"02x") + format(x%100,"02x")
  pos_y = format(y/100,"02x") + format(y%100,"02x")
  cmd = ("18" + pos_x + pos_y + "00ff")
  # print "(" + str(x) + "," + str(y) + ") " + cmd
  ser.write( cmd.decode("hex") )

def set_laser_power(power): # range 0-10
  ser.write( ("33" + format(power,"02x") + "00000000ff").decode("hex") )

def set_fan_speed(speed): # range 0-10
  ser.write( ("34" + format(speed,"02x") + "00000000ff").decode("hex") )

def set_laser_box(x1, y1, x2, y2):
  pos_x1 = format(x1/100,"02x") + format(x1%100,"02x")
  pos_y1 = format(y1/100,"02x") + format(y1%100,"02x")
  pos_x2 = format(x2/100,"02x") + format(x2%100,"02x")
  pos_y2 = format(y2/100,"02x") + format(y2%100,"02x")
  ser.write("ffffffff")
  ser.write("1B" + pos_x1 + pos_y1 + "00FF".decode("hex"))
  ser.write("1B" + pos_x2 + pos_y2 + "01FF".decode("hex"))
  ser.write("1C0000000000FF".decode("hex"))

def set_laser_move(position): # 1=up, 2=down, 3=left, 4=right
  ser.write( ("19" + format(position,"02x") + "00000000ff").decode("hex") )

def stop_laser_job_center(): # take box and find center, don't do write in function 41,84 
  set_laser_position(0,0) # change to center of x,y later
  # ser.write("180128005400FF".decode("hex")) # original data from sample

def set_laser_speed(speed): # 0-250
  ser.write( ("17" + format(speed,"02x") + "00000000ff").decode("hex") )

def init_laser(): # 1=up, 2=down, 3=left, 4=right
  ser.write( ("1a0000000000ff").decode("hex") )
  return ser.read(140).encode("hex")

def reboot_laser(): # 1=up, 2=down, 3=left, 4=right
  ser.write( ("fe0000000000ff").decode("hex") )
  return ser.read(140).encode("hex")

def get_laser_resp(): # 140 or timeout defined in serial connection
  return ser.read(140).encode("hex") 

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
  # 3E 07 FFFF (same)
  # 3E 28 {UUIDREMOVED} FFFF # uid
  # 3E 29 5F040000000000 FFFF # 95 + 04 (/12) = 8.25 hr .25*60=15 min
  # 3E 2A 2B610500000000 FFFF # 43 97 05 power up times order last mid first : 59743
  # 3E 2B 10000000000000 FFFF # 16 complete times
  # 3E 2C 02040000000000 FFFF # fw version v2.4
  # 3E 2D 32000000000000 FFFF # 50 (same), don't knwo what this is

  # 3E07FFFF3E28{UUIDREMOVED}FFFF3E295F040000000000FFFF3E2A2B610500000000FFFF3E2B10000000000000FFFF3E2C02040000000000FFFF3E2D32000000000000FFFF
  # 3E 07 FFFF
  # 3E 28 {UUIDREMOVED} FFFF
  # 3E 29 13050000000000 FFFF # 63 + 05 = 8hr 39 min
  # 3E 2A 2B610500000000 FFFF
  # 3E 2B 10000000000000 FFFF
  # 3E 2C 02040000000000 FFFF
  # 3E 2D 32000000000000 FFFF


  # 8h 46m
  # 3E07FFFF
  # 3E 28 {UUIDREMOVED} FFFF
  # 3E 29 1A050000000000 FFFF # 26 + 05 = 8h 46m
  # 3E 2A 2B610500000000 FFFF
  # 3E 2B 10000000000000 FFFF
  # 3E 2C 02040000000000 FFFF
  # 3E 2D 32000000000000 FFFF

  # 3e 29 2e050000000000 # 46 = 9h 6-8m???   nn - 40, if negative  60 - it, hr 4+
  #       33050000000000 # 51 = 9h 11m
  #       34050000000000 # 52 = 9h 12m
  #       35050000000000 # 53 = 9h 13m
  #       41050000000000 # 65 = 9h 25m
  #       44050000000000 #    = 9h 28m
  #       02060000000000 # 02   = 10h 02m
  
parse_init_resp(init_laser())
raw_input("Press Enter...")


# raw_input("Press Enter...")
# parse_init_resp(reboot_laser())
# time.sleep(1)
# get_laser_resp()
# raw_input("Press Enter...")

# set_laser_power(1)
# time.sleep(0.1)
# set_fan_speed(0)
# time.sleep(0.1)
# set_laser_position(0,0)
# raw_input("Press Enter...")
# # time.sleep(3)
# set_laser_position(1024,1024)
# # time.sleep(3)
# raw_input("Press Enter...")

# set_laser_position(0,0)
# raw_input("Press Enter...")
# # time.sleep(3)
# # for x in range(0,513):
# #   print x
# #   set_laser_position(x,x)
# #   # raw_input("Press Enter...")
# #   time.sleep(0.01)
set_laser_position(30,20)
raw_input("Press Enter...")
set_laser_box(11,10,100,100)
raw_input("Press Enter...")
set_laser_position(0,0)




print 'done'