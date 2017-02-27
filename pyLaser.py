#!/usr/bin/env python2

import os, sys, getopt, re

import serial #pyserial
from PIL import Image
# from PIL import ImageTk
# from PIL import ImageFilter
import time, glob, math

module_info = {
'NAME': "pyLaser",
'ORIGINAL_ARTHOR': "Applied Ellippsis", # leave this
'ARTHOR': "Applied Ellipsis", # change this to you
'DESCRIPTION': '''
Python Interface for HTPOW (Cheap Chinese CNC Laser Engravers)
''',
'REPO_URL': 'https://github.com/AppliedEllipsis/pyLaser',
'VERSION': "0.1a",
'LICENSE': "See License.txt, but GPLv3 for the lazy",
}

debug = True

def serial_connect(com_port):
  try:
    ser = serial.Serial(
        port=com_port,
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout = 1
    )
    return ser
  except:
    return False

def serial_send(ser, data):
  if debug: print "\tDBG: serial_send, payload=" + data
  try:
    data = data.replace(' ','').decode('hex')
    ser.write(data)
    return True
  except:
    return False


def serial_read(ser): # 140 or timeout defined in serial connection
  if debug: print "\tDBG: serial_read"
  ret = ser.read(140).encode("hex") 
  print "\tDBG: payload=" + ret
  return ret


def set_laser_speed(ser, speed): # 0-250 
  if debug: print "\tDBG: set_laser_speed: " + str(speed)
  serial_send(ser, ("17" + format(speed,"02x") + "00000000ff") )
  time.sleep(.2)

def set_laser_position(ser, x,y): # X and Y range: 0-512 
  if debug: print "\tDBG: set_laser_position: " + str(x) + ',' + str(y)
  # note will not always take direct path if large gaps, keep it small if doing vector with laser on
  # time.sleep(0.01) is recommended after for smooth movement
  # use power 9 max, power 10 does not work properly with positioning
  pos_x = format(x/100,"02x") + format(x%100,"02x")
  pos_y = format(y/100,"02x") + format(y%100,"02x")
  cmd = ("18" + pos_x + pos_y + "00ff")
  # print "(" + str(x) + "," + str(y) + ") " + cmd
  serial_send(ser, cmd)


laser_buff_min = 60
laser_buff_max = 121
laser_buff = laser_buff_min

laser_grey_buff_min = 151
laser_grey_buff_max = 181
laser_grey_buff = laser_grey_buff_min
# grey may be 0x97 (151) - 0xb4 (180)



def config_open(ser): # not sure what these really do, but I'm going to have done before other settings
  # most of these cause issues so disabled for now
  if debug: print "\tDBG: config_open"
  # serial_send(ser, ("18 00 00 00 00 FF"))
  # time.sleep(0.1)
  # serial_send(ser, ("15 00 00 00 00 FF")) # 15 01 sets raster mode, maybe this forces off, maybe should use in other things
  # time.sleep(0.1)
  # serial_send(ser, ("1B 00 00 00 00 FF")) # send box partial
  # time.sleep(0.1)
  # serial_send(ser, ("1B 04 32 04 32 01 FF")) # send box 432,432 with 1?
  # time.sleep(0.1)
  serial_send(ser, ("36 00 00 00 00 00 FF")) # idk?
  # read 3E 36 28 01 01 00 00 00 00 FF FF
  time.sleep(0.2)
  return serial_read(ser)


def config_close(ser): # not sure what these really do, but I'm going to have done after other settings
  # most of these cause issues so disabled for now
  if debug: print "\tDBG: config_close"
  # serial_send(ser, ("18 00 00 00 00 FF")) # sometimes it sends a partial one
  # time.sleep(0.2)
  # serial_send(ser, ("18 00 00 00 00 00 FF"))
  # time.sleep(0.2)
  return serial_read(ser)

def start_laser_raster_mode(ser):
  if debug: print "\tDBG: start_laser_raster_mode"
  global laser_buff, laser_buff_max, laser_buff_min
  laser_buff = laser_buff_min
  serial_send(ser, ("15 01 01 00 00 00 FF"))
  time.sleep(.2)

def stop_laser_raster_mode(ser):
  if debug: print "\tDBG: stop_laser_raster_mode"
  global laser_buff
  serial_send(ser, ( (format(laser_buff,"02x") + "09 09 09 09 09 FF")))
  time.sleep(.2)

def start_laser_raster_grey_mode(ser):
  if debug: print "\tDBG: start_laser_raster_mode"
  global laser_grey_buff, laser_grey_buff_max, laser_grey_buff_min
  laser_grey_buff = laser_grey_buff_min
  # serial_send(ser, "15 00 00 00 00 00 FF")
  # time.sleep(.2)
  # serial_send(ser, "1B 00 29 00 2F 00 FF")
  # time.sleep(.2)
  # serial_send(ser, "1B 00 59 02 2B 01 FF")
  # time.sleep(.2)
  # serial_send(ser, "1C 00 00 00 00 00 FF")
  # time.sleep(2)
  # serial_send(ser, "18 00 29 00 2F 00 FF")
  # time.sleep(2)
  serial_send(ser, "15 01 01 00 00 00 FF")
  time.sleep(1)
  # serial_send(ser, "15 01 01 00 00 00 FF")
  # 15 00 00 00 00 00 FF # pause
# WRITE=1B 00 13 00 1F 00 FF        (19,31) = 0
# WRITE=1B 00 5A 00 3C 01 1C 00 00 00 00 00 FF
# WRITE=18 00 00 1F 00 FF
# WRITE=15 01 01 00 00 00 FF        (101,0) = 0

  time.sleep(.2)

def stop_laser_raster_grey_mode(ser):
  if debug: print "\tDBG: stop_laser_raster_mode"
  global laser_grey_buff
  serial_send(ser, ( (format(laser_grey_buff,"02x") + "09 00 00 00 00 FF")))
  # serial_send(ser, "15 00 00 00 00 00 FF")
  time.sleep(.2)

def raster_draw_grey_pixel(ser,x,y,grey=0,delay=0.2): # X and Y range: 0-512, grey range 0-254 [0=darkest, 254=lightest besides not firing.] 
  # I find if using grey values, to skip 2 pixels horizontal or it won't show up
  # Actually, I don't think grey works on this machine, even using stock software, sample images are not grey when done in grey mode
  if debug: print "\tDBG: raster_draw_pixel: " + str(x) + "," + str(y) + " / " + str(grey) 
  global laser_grey_buff, laser_grey_buff_max, laser_grey_buff_min
  laser_grey_buff += 1
  laser_grey_buff = laser_grey_buff%laser_grey_buff_max
  if laser_grey_buff == 0:
    laser_grey_buff = laser_grey_buff_min

  # note will not always take direct path if large gaps, keep it small if doing vector with laser on
  # time.sleep(0.01) is recommended after for smooth movement
  pos_x = format(x/100,"02x") + format(x%100,"02x")
  pos_y = format(y/100,"02x") + format(y%100,"02x")
  cmd = (format(laser_grey_buff,"02x") + pos_x + pos_y +  format(grey,"02x") + "ff")
  # print "(" + format(x,"03") + "," + format(y,"03") + ") " + '-'.join(a+b for a,b in zip(cmd[::2], cmd[1::2]))
  serial_send(ser, cmd)
  time.sleep(delay)
  # raw_input("Press Enter to continue...")


def raster_draw_pixel(ser,x,y,grey=0,delay=0.2): # X and Y range: 0-512, grey range 0-254 [0=darkest, 254=lightest besides not firing.] 
  # I find if using grey values, to skip 2 pixels horizontal or it won't show up
  # Actually, I don't think grey works on this machine, even using stock software, sample images are not grey when done in grey mode
  if debug: print "\tDBG: raster_draw_pixel: " + str(x) + "," + str(y) + " / " + str(grey) 
  global laser_buff, laser_buff_max, laser_buff_min
  laser_buff += 1
  laser_buff = laser_buff%laser_buff_max
  if laser_buff == 0:
    laser_buff = laser_buff_min

  # note will not always take direct path if large gaps, keep it small if doing vector with laser on
  # time.sleep(0.01) is recommended after for smooth movement
  pos_x = format(x/100,"02x") + format(x%100,"02x")
  pos_y = format(y/100,"02x") + format(y%100,"02x")
  cmd = (format(laser_buff,"02x") + pos_x + pos_y +  format(grey,"02x") + "ff")
  # print "(" + format(x,"03") + "," + format(y,"03") + ") " + '-'.join(a+b for a,b in zip(cmd[::2], cmd[1::2]))
  serial_send(ser, cmd)
  time.sleep(delay)
  # raw_input("Press Enter to continue...")


def config_run(ser, bool_val=True): # run checkbox from settings
  if debug: print "\tDBG: config_run: " + str(bool_val)
  if bool_val:
    serial_send(ser,  "1C 00 00 00 00 00 FF")
  else:
    serial_send(ser,  "18 00 00 00 00 00 FF")
  time.sleep(.12)


def set_laser_move(ser, direction): # Moves laser without x,y towards a direction 1=up, 2=down, 3=left, 4=right
  if debug: print "\tDBG: set_laser_move: " + str(direction)
  serial_send(ser, ("19" + format(direction,"02x") + "00000000ff"))
  time.sleep(.12)


def init_laser(ser): # seems optional but returns some nice to have info
  if debug: print "\tDBG: init_laser"
  serial_send(ser, ("1a 00 00 00 00 00 ff"))
  time.sleep(.2)
  return serial_read(ser)


def set_laser_box(ser, x1, y1, x2, y2): # X and Y range: 0-512
  if debug: print "\tDBG: set_laser_box: (" + str(x1) + "," + str(y1) + ") - (" + str(x2) + "," + str(y2) + ")"
  pos_x1 = format(x1/100,"02x") + format(x1%100,"02x")
  pos_y1 = format(y1/100,"02x") + format(y1%100,"02x")
  pos_x2 = format(x2/100,"02x") + format(x2%100,"02x")
  pos_y2 = format(y2/100,"02x") + format(y2%100,"02x")
  # serial_send("ffffffff")
  serial_send(ser, "1B" + pos_x1 + pos_y1 + "00FF" )
  time.sleep(.2)
  serial_send(ser, "1B" + pos_x2 + pos_y2 + "01FF" )
  time.sleep(.2)
  serial_send(ser, "1C0000000000FF")
  time.sleep(.2)


def stop_laser_job_center(ser): # take box and find center, don't do write in function 41,84 
  if debug: print "\tDBG: stop_laser_job_center"
  set_laser_position(ser, 0,0) # change to center of x,y later
  time.sleep(.2)
  # serial_send(ser,"180128005400FF") # original data from sample


def set_laser_power(ser, power): # range 0-10 (Don't use 10, it messes up movement)
  if debug: print "\tDBG: set_laser_power: " + str(power)
  serial_send(ser, ("33" + format(power,"02x") + "00000000ff"))
  time.sleep(.2)


def set_fan_speed(ser, speed): # range 0-10
  if debug: print "\tDBG: set_fan_speed: " + str(speed)
  serial_send(ser, ("34" + format(speed,"02x") + "00000000ff"))
  time.sleep(.2)



def shutdown_laser(ser): # shuts down laser, you have to replug it, or hold down red power button on it. Power button doesn't work for me.
  if debug: print "\tDBG: shutdown_laser"
  serial_send(ser, ("3A 00 00 00 00 00 FF"))
  time.sleep(.2)
  return serial_read(ser)




def set_motor_speed(ser, speed): # range 0-100 recommended 60-75
  if debug: print "\tDBG: set_motor_speed: " + str(speed)
  # serial_send(ser, ("150000000000ff"))
  # set_laser_box(0,0,150,150)
  # serial_send(ser, ("360000000000ff"))
  # return serial_read(ser)
  serial_send(ser, ("37" + format(100-speed,"02x") + "00000000ff"))
  time.sleep(.2)
  # set_laser_position(0,0)


def set_motor_x_reverse(ser, value): # range 0-1 0=off,1=on  # checkbox from settings
  if debug: print "\tDBG: set_motor_x_reverse: " + str(value)
  serial_send(ser, ("38 01" + format(value,"02x") + "00 00 00 00 FF"))
  time.sleep(.2)


def set_motor_y_reverse(ser, value): # range 0-1 0=off,1=on # checkbox from settings
  if debug: print "\tDBG: set_motor_y_reverse: " + str(value)
  serial_send(ser, ("39 01" + format(value,"02x") + "00 00 00 00 FF"))
  time.sleep(.2)


def laser_reboot(ser): # returns same info as init, actually today it seems to return something different
  if debug: print "\tDBG: laser_reboot"
  serial_send(ser, "FE 00 00 00 00 00 FF")
  time.sleep(.2)
  return serial_read(ser)


def check_for_heartbeat(ser): # not sure this really is ready, it seems to throw a 01 or 02 occationally while doing some actions
  # my latest theory is 3e01 and 3e02 are heartbeats the laser sends during raster/engraving processes
  # my theory is alternates between the two so if you have a large buffer that has not been read, you can tell the difference of the previous sent packet
  # this can be used to ensure the laser is still online while performing large tasks
  if debug: print "\tDBG: check_for_heartbeat"
  while 1:
    print 'getting resp...'
    resp = serial_read(ser)
    print resp
    if "ffff" in resp:
      resp = resp.split("ffff")
      print resp[-2]
      if resp[-2] == '3e01':
        break
      elif resp[-2] == '3e02':
        break
      else:
        print 'waiting 1...'
        time.sleep(0.1)
    else:
      print 'waiting 2...'
      time.sleep(0.1)


def parse_init_resp(resp):
  if debug: print "\tDBG: parse_init_resp: " + resp 
  for row in resp.split("ffff"):
    if row[0:4] == '3e3e': # triggered on reboot
      ''
    if row[0:4] == '3e07':
      ''
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



def get_avail_serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    # Original Source: http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException, serial.serialutil.SerialException):
            pass
    return result


def draw_line(ser, x1, y1, x2, y2, sleep, power=8, blink=False, skip=1):
  # add variable power levels
  if debug: print "\tDBG: draw_line (" + str(x1) + "," + str(y1) + ") - (" + str(x2) + "," + str(y2) + ")"
  line_points = get_line((x1,y1), (x2,y2))
  if not blink: 
    set_laser_power(ser, 9)  # higher values seem to cause problems
  else:
    set_laser_power(ser, 1)

  skip_list = range(1, skip)
  skip_num = 1
  for xy in line_points:
    skip_num = (skip_num+1)%skip
    if skip_num != 1 and (xy[0] != x2 and xy[1] != y2):
      if skip_num in skip_list:
        if debug: print( "\t\tskipping due to skip_num not being 1 (" + str(skip_num) + ") while skipping " + str(skip) + " (" + str(xy[0]) + ", " + str(xy[1]) + ")" )
        continue
    # print str(xy[0]) + ', ' + str(xy[1])
    set_laser_position(ser, xy[0], xy[1])
    if blink: 
      time.sleep(0.05) # set to the same as the laser speed or longer for best results
      set_laser_power(ser, 9)
      time.sleep(0.105) # set to the same as the laser speed or longer for best results
      set_laser_power(ser, 0)
    else:
      time.sleep(0.105) # set to the same as the laser speed or longer for best results

  set_laser_power(ser,1)



def draw_line_raster(ser, x1, y1, x2, y2, sleep, skip=1):
  # add variable power levels
  if debug: print "\tDBG: draw_line_raster (" + str(x1) + "," + str(y1) + ") - (" + str(x2) + "," + str(y2) + ")"
  line_points = get_line((x1,y1), (x2,y2))

  skip_list = range(1, skip)
  skip_num = 1
  for xy in line_points:
    skip_num = (skip_num+1)%skip
    if skip_num != 1 and (xy[0] != x2 and xy[1] != y2):
      if skip_num in skip_list:
        if debug: print( "\t\tskipping due to skip_num not being 1 (" + str(skip_num) + ") while skipping " + str(skip) + " (" + str(xy[0]) + ", " + str(xy[1]) + ")" )
        continue
    raster_draw_pixel(ser, xy[0], xy[1], 0, sleep)



def get_line(start, end):
    if debug: print "\tDBG: get_line: " + str(start) + str(end)
    # Bresenham's Line Algorithm
    # Original Source: http://www.roguebasin.com/index.php?title=Bresenham%27s_Line_Algorithm#Python
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
 
    is_steep = abs(dy) > abs(dx) # Determine how steep the line is
    if is_steep: # Rotate line
        x1, y1 = y1, x1
        x2, y2 = y2, x2
 
    swapped = False # Swap start and end points if necessary and store swap state
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        swapped = True
 
    # Recalculate differentials
    dx = x2 - x1
    dy = y2 - y1
 
    # Calculate error
    error = int(dx / 2.0)
    ystep = 1 if y1 < y2 else -1
 
    # Iterate over bounding box generating points between start and end
    y = y1
    points = []
    for x in range(x1, x2 + 1):
        coord = (y, x) if is_steep else (x, y)
        points.append(coord)
        error -= abs(dy)
        if error < 0:
            y += ystep
            error += dx
    # Reverse the list if the coordinates were swapped
    if swapped:
        points.reverse()

    return points


def fan_3_sec(ser):
  if debug: print "\tDBG: Running fan for a few sec"
  time.sleep(3)
  set_fan_speed(ser,0)


def laser_reset_calibrate(ser):
  # sometimes you just have to unplug everything to fix issues
  stop_laser_raster_mode(ser) # make sure not in raster mode
  stop_laser_raster_grey_mode(ser) # make sure not in raster mode
  config_open(ser)
  config_run(True)
  set_motor_speed(ser, 65)
  set_motor_x_reverse(ser, 0)
  set_motor_y_reverse(ser, 0)
  config_close(ser)
  # time.sleep(1)
  config_run(ser,False)
  # time.sleep(1)
  set_laser_speed(ser, 105)
  set_fan_speed(ser, 10)
  set_laser_power(ser, 1)
  parse_init_resp(laser_reboot(ser))
  time.sleep(3)
  config_open(ser)
  config_run(ser,True)
  # time.sleep(1)
  set_motor_speed(ser, 65)
  set_motor_x_reverse(ser, 0)
  set_motor_y_reverse(ser, 0)
  config_close(ser)
  # time.sleep(1)
  config_run(ser,False)
  # serial_read(ser)
  # time.sleep(1)
  set_laser_speed(ser, 105)
  set_fan_speed(ser, 0)
  set_laser_power(ser, 1)
  set_laser_position(ser, 0, 0)
  time.sleep(3)
  set_laser_position(ser, 512, 512)
  time.sleep(3)
  set_laser_position(ser, 0, 0)
  time.sleep(3)






# drawing a line with a break using raster api
def example_raster_draw_line_break(ser, skip=1):
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 105)
  set_laser_box(ser, 0, 0, 512, 512)  # quick calibration
  time.sleep(3)
  set_laser_box(ser, 0, 10, 512, 12) # outline the area we are going to draw
  time.sleep(3)
  set_laser_position(ser, 10,0)
  time.sleep(2)
  start_laser_raster_mode(ser)
  for y in range(10, 12, skip):
    for x in range(0, 512, skip):
      if not (x > 220+y and x<380+y):
        raster_draw_pixel(ser, x, y, 0, 0.105)  # go line by line, it does not like angles with this mode
        # maybe I should have it draw backwards alternating lines to save a trip back
  stop_laser_raster_mode(ser)
  set_laser_power(ser,1)
  fan_3_sec(ser)


# drawing various shades using raster api
def example_raster_draw_shades(ser, skip=1):
  stop_laser_raster_grey_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 50)
  # set_laser_box(ser, 0, 0, 512, 512)  # quick calibration
  # time.sleep(3)
  # set_laser_box(ser, 0, 10, 350, 30) # outline the area we are going to draw
  # time.sleep(3)
  # lets draw the box
  # set_laser_power(ser, 8)
  # set_laser_box(ser, 0, 10, 350, 30) # outline the area we are going to draw
  # time.sleep(3)
  set_laser_power(ser, 1)
  set_laser_position(ser, 10,0)
  time.sleep(2)
  start_laser_raster_grey_mode(ser)
  for y in range(10, 30, 4):
    for x in range(0,350, skip):
      grey = 10
      if x > 25: grey = 50
      if x > 50: grey = 100
      if x > 75: grey = 150
      if x > 100: grey = 200
      if x > 125: grey = 250
      if x > 150: grey = 200
      if x > 160: grey = 250
      if x > 165: grey = 254
      if x > 175: grey = 250
      if x > 195: grey = 150
      if x > 200: grey = 100
      if x > 250: grey = 50
      if x > 300: grey = 0

      # if x > 100: grey = 250
      # if x > 200: grey = 10
      raster_draw_grey_pixel(ser, x, y, grey, 0.050)
        # maybe I should have it draw backwards alternating lines to save a trip back
  stop_laser_raster_grey_mode(ser)
  set_laser_power(ser,1)
  fan_3_sec(ser)


def example_raster_draw_grey_picture(ser, image_path):
  # image conversions from http://stackoverflow.com/questions/1109422/getting-list-of-pixel-values-from-pil
  # and http://stackoverflow.com/questions/32361908/python-gray-scale-formula-with-pil
  if image_path == '':
    print "\n\tERROR: No image file provided"
    return
  if not os.path.isfile(image_path):
      print "\n\tERROR: No image file exists"
      return
  i = Image.open(image_path)
  width, height = i.size
  # stop_laser_raster_mode(ser) # make sure not in raster mode
  # stop_laser_raster_grey_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  speed_ms = 125
  speed_s = speed_ms/1000.0
  set_laser_speed(ser, speed_ms)

  # this seems to be needed for raster
  set_laser_box(ser, 0, 0, 512, 512) # quick calibration
  time.sleep(2)
  set_laser_position(ser, 0,0)
  time.sleep(3)

  # set_laser_box(ser, 0, 0, 512, 512)  # quick calibration
  # time.sleep(3)
  # set_laser_box(ser, 0, 10, 350, 30) # outline the area we are going to draw
  # time.sleep(3)
  # lets draw the box
  # set_laser_power(ser, 8)
  # set_laser_box(ser, 0, 10, 350, 30) # outline the area we are going to draw
  # time.sleep(3)
  # set_laser_power(ser, 1)
  # set_laser_position(ser, 10,0)
  time.sleep(1)
  start_laser_raster_grey_mode(ser)
  for y in range(0, height, 2):
    for x in range(0, width, 1):
      pixel = i.getpixel((x, y))
      r = pixel[0]
      g = pixel[1]
      b = pixel[2]
      # r, g, b = i.getpixel((x, y))
      if (r, g, b) != (255,255,255):
        # bw_value = int(round(sum(pixels[x, y]) / float(len(pixels[x, y]))))
        # bw_value = 254 - bw_value
        # if bw_value < 0: bw_value = 0
        # luma = (0.3 * pixels[x, y][0]) + (0.59 * pixels[x, y][1]) + (0.11 * pixels[x, y][2])
        # luma = int(math.ceil(luma))
        value = r * 0.299 + g * 0.587 + b * 0.114
        value = 255 - int(value)
        # if luma > 254: luma = 254
        # bw_value = 254 - luma
        # if bw_value < 0: bw_value = 0
        # if round(sum(cpixel)) / float(len(cpixel)) > 127: bw_127 = cpixel
        # print "(%d, %d) - %s" % (x,y,pixels[x, y])
        # print "(%d, %d) - %s" % (x,y,luma)
        # print x, y, r, g, b, value
        raster_draw_grey_pixel(ser, x, y, value, speed_s)
        # print x, y, r, g, b, value
    if y+1 < height:
      if debug: print( "\t\tReversing Direction")
      for x in range(width-1, -1, -3):
        pixel = i.getpixel((x, y))
        r = pixel[0]
        g = pixel[1]
        b = pixel[2]
        # r, g, b = i.getpixel((x, y+1))
        if (r, g, b) != (255,255,255):
          value = r * 0.299 + g * 0.587 + b * 0.114
          value = 255 - int(value)
          # print x, y, r, g, b, value
          raster_draw_grey_pixel(ser, x, y+1, value, speed_s)
  stop_laser_raster_grey_mode(ser)

# example_raster_draw_grey_picture(None, "test.png")
# print "\nDone\n"
# sys.exit()

# draw an angle with raster positions with different skip
def example_raster_draw_angle(ser, skip=1):
  stop_laser_raster_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 200)
  set_laser_box(ser, 0, 0, 512, 512) # quick calibration
  time.sleep(2)
  set_laser_position(ser, 0,0)
  time.sleep(3)
  set_fan_speed(ser, 10)
  start_laser_raster_mode(ser)
  for x in range(0,513, skip):
    raster_draw_pixel(ser, x, x, 0, 0.2)
  stop_laser_raster_mode(ser)
  set_laser_power(ser,1)
  fan_3_sec(ser)



# draw an angle with raster positions with different skip
def example_raster_draw_h_line(ser, skip=1):
  stop_laser_raster_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 105)
  set_laser_box(ser, 0, 0, 512, 512) # quick calibration
  time.sleep(2)
  set_laser_position(ser, 0,0)
  time.sleep(3)
  set_fan_speed(ser, 10)
  start_laser_raster_mode(ser)
  for x in range(0,513, skip):
    raster_draw_pixel(ser, x, 10, 0, 0.105)
  stop_laser_raster_mode(ser)
  set_laser_power(ser,1)
  fan_3_sec(ser)




# draw an angle with raster positions with different skip
def example_raster_draw_v_line(ser, skip=1):
  stop_laser_raster_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 105)
  set_laser_box(ser, 0, 0, 512, 512) # quick calibration
  time.sleep(2)
  set_laser_position(ser, 0,0)
  time.sleep(3)
  set_fan_speed(ser, 10)
  start_laser_raster_mode(ser)
  for y in range(0,513, skip):
    raster_draw_pixel(ser, 10, y, 0, 0.105)
  stop_laser_raster_mode(ser)
  set_laser_power(ser,1)
  fan_3_sec(ser)



# Example to Vector Write the word Hi using Raster API
def example_raster_vector_hi(ser, skip=1, delay=0.105):
  stop_laser_raster_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 105)
  set_laser_box(ser, 0, 0, 512, 512) # quick calibration
  time.sleep(2)
  set_laser_box(ser, 64, 132, 148, 235) # outline the area we are going to draw
  time.sleep(2)
  # Draw H
  set_laser_position(ser,64, 223)
  time.sleep(3)
  start_laser_raster_mode(ser)
  draw_line_raster(ser, 64, 223, 84, 126, delay, skip)
  # set_laser_position(ser, 73, 170)
  # time.sleep(move_speed_move_delay)
  draw_line_raster(ser, 73, 170, 113, 176, delay, skip)
  # set_laser_position(ser, 125, 132)
  # time.sleep(move_speed_move_delay)
  draw_line_raster(ser, 125, 132, 100, 230, delay, skip)
  # Draw i
  # set_laser_position(ser, 129, 235)
  # time.sleep(move_speed_move_delay)
  draw_line_raster(ser, 129, 235, 144, 182, delay, skip)
  # set_laser_position(ser, 148, 165)
  # time.sleep(move_speed_move_delay)
  draw_line_raster(ser, 148, 165, 150, 158, delay, skip)
  stop_laser_raster_mode(ser)
  set_laser_power(ser, 1)
  fan_3_sec(ser)




# Example to Vector Write the word Hi
# if you blink, you let it move, then fire, so the results look a lot better, but more pixlie due to non-continuo s beam
def example_vector_hi(ser, blink=False, skip=1, delay=0.105):
  move_speed_delay = delay # set to the same as the laser speed or longer for best results
  move_speed_move_delay = 1 # move_speed_delay * 25
  laser_strength = 8
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 105)
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_laser_box(ser, 0, 0, 512, 512)  # quick calibration
  time.sleep(3)
  set_laser_box(ser, 64, 132, 148, 235) # outline the area we are going to draw
  time.sleep(2)
  # Draw H
  set_laser_position(ser,64, 223)
  time.sleep(move_speed_move_delay)
  draw_line(ser, 64, 223, 84, 126, move_speed_delay, laser_strength, blink, skip)
  set_laser_position(ser, 73, 170)
  time.sleep(move_speed_move_delay)
  draw_line(ser, 73, 170, 113, 176, move_speed_delay, laser_strength, blink, skip)
  set_laser_position(ser, 125, 132)
  time.sleep(move_speed_move_delay)
  draw_line(ser, 125, 132, 100, 230, move_speed_delay, laser_strength, blink, skip)
  # Draw i
  set_laser_position(ser, 129, 235)
  time.sleep(move_speed_move_delay)
  draw_line(ser, 129, 235, 144, 182, move_speed_delay, laser_strength, blink, skip)
  set_laser_position(ser, 148, 165)
  time.sleep(move_speed_move_delay)
  draw_line(ser, 148, 165, 150, 158, move_speed_delay, laser_strength, blink, skip)
  set_laser_power(ser, 1)
  fan_3_sec(ser)


# draw an angle with vector positions with different skip
# this can be replaced with the draw_line function, but kept as an example of manual positioning
# this shows how inaccurate the cnc really is with angles \ and pathing
# if you blink, you let it move, then fire, so the results look a lot better, but more pixlie due to non-continuous beam
def example_vector_draw_angle(ser, skip=1, blink=False):
  stop_laser_raster_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 105)
  set_laser_box(ser, 0, 0, 512, 512) # quick calibration
  time.sleep(2)
  set_laser_position(ser, 0,0)
  time.sleep(3)
  set_fan_speed(ser, 10)
  if not blink: 
    set_laser_power(ser, 9)
  else:
    set_laser_power(ser, 1)
  for x in range(0,513, skip):
    set_laser_position(ser, x, x)
    if blink: 
      time.sleep(0.105) # set to the same as the laser speed or longer for best results
      set_laser_power(ser, 9)
      time.sleep(0.105) # set to the same as the laser speed or longer for best results
      set_laser_power(ser, 0)
    else:
      time.sleep(0.105) # set to the same as the laser speed or longer for best results
  set_laser_power(ser,1)
  fan_3_sec(ser)


# draw an horizontal with vector positions with different skip
# this can be replaced with the draw_line function, but kept as an example of manual positioning
def example_vector_draw_h_line(ser, skip=1):
  stop_laser_raster_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 105)
  set_laser_box(ser, 0, 0, 512, 512) # quick calibration
  time.sleep(2)
  set_laser_position(ser, 0, 10)
  time.sleep(3)
  set_fan_speed(ser, 10)
  set_laser_power(ser, 9)
  for x in range(0,513, skip):
    set_laser_position(ser, x, 10)
    time.sleep(0.105) # set to the same as the laser speed or longer for best results
  set_laser_power(ser,1)
  fan_3_sec(ser)


# draw an vertical with vector positions with different skip
# this can be replaced with the draw_line function, but kept as an example of manual positioning
def example_vector_draw_v_line(ser, skip=1):
  stop_laser_raster_mode(ser) # make sure not in raster mode
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  set_fan_speed(ser, 10)
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 105)
  set_laser_box(ser, 0, 0, 512, 512) # quick calibration
  time.sleep(2)
  set_laser_position(ser, 10, 0)
  time.sleep(3)
  set_fan_speed(ser, 10)
  set_laser_power(ser, 9)
  for y in range(0,513, skip):
    set_laser_position(ser, 10, y)
    time.sleep(0.105) # set to the same as the laser speed or longer for best results
  set_laser_power(ser,1)
  fan_3_sec(ser)


# Make the laser move around
# below is a sample dance of the laser to show how to use some things
# parts can be replaced with the draw_line function, but kept as an example of manual positioning
def example_chinese_laser_dance(ser):
  print "\nAre you ready for the Chinese Laser Dance?"
  raw_input("Press Enter to start the dance...")
  set_motor_speed(ser, 65)
  set_laser_speed(ser, 15)
  set_laser_power(ser, 1) # just a visible laser, nothing really will cut
  time.sleep(0.1)
  set_fan_speed(ser, 10)
  time.sleep(0.1)
  print "it's good to go 0,0 -> 512,512, 0,0 for calibration of motors before tasks, you can also draw boxes"
  set_laser_position(ser, 0,0)
  time.sleep(3)
  set_laser_position(ser, 512,512)
  time.sleep(3)
  print "set_laser_power 1... pew"
  set_laser_power(ser, 1)
  time.sleep(1)
  print "set_laser_position(0,0)"
  set_laser_position(ser, 0,0)
  time.sleep(3)
  print "Top left to bottom right, angle"
  for x in range(0,513):
    set_laser_position(ser, x,x)
    time.sleep(0.01)
  time.sleep(2)
  set_fan_speed(ser, 1)
  time.sleep(0.1)
  set_laser_position(ser, 513,0)
  time.sleep(3)
  print "bottom left to top right, angle"
  for x in range(0,513):
    set_laser_position(ser, 513-x,x)
    time.sleep(0.01)
  time.sleep(2)
  set_laser_position(ser, 0,513)
  time.sleep(3)
  print "bottom left to top left, angle, switcheroo"
  for x in range(0,513):
    if x > 256:
      set_laser_position(ser, 513-x,513-x)
    else:
      set_laser_position(ser, x,513-x)
    time.sleep(0.01)
  time.sleep(2)
  set_laser_position(ser, 30,20)
  time.sleep(3)
  parse_init_resp(laser_reboot(ser))
  time.sleep(3)
  set_fan_speed(ser, 5)
  time.sleep(0.1)
  set_laser_box(ser, 100,100,150,150)
  time.sleep(2)
  set_laser_box(ser, 0,0,150,150)
  time.sleep(2)
  set_laser_box(ser, 10,100,50,50)
  time.sleep(2)
  print "Machine Gun #1"
  set_laser_box(ser, 10,10,20,20)
  time.sleep(2)
  print "Machine Gun #2"
  set_laser_box(ser, 100,50,105,55)
  time.sleep(2)
  print "Fax Machine"
  set_laser_box(ser, 0,0,512,0)
  time.sleep(4)
  print "Flatbed Scanner"
  set_laser_box(ser, 0,0,0,512)
  time.sleep(2)
  set_laser_box(ser, 25,10,150,50)
  time.sleep(2)
  set_fan_speed(ser, 10)
  time.sleep(0.1)
  set_laser_position(ser, 200,403)
  time.sleep(2)
  print "Rebooting laser, because why not"
  parse_init_resp(laser_reboot(ser))
  time.sleep(2)
  set_laser_power(ser, 0)
  time.sleep(1)
  print "pew"
  set_laser_power(ser, 10)
  time.sleep(1)
  print "set_laser_power 0"
  set_laser_power(ser, 0)
  time.sleep(1)
  print "{pew} pew"
  set_laser_power(ser, 10)
  time.sleep(1)
  set_laser_power(ser, 0)
  time.sleep(1)
  print "{pew pew} pew"
  set_laser_power(ser, 10)
  time.sleep(1)
  set_laser_power(ser, 0)
  time.sleep(1)
  set_laser_position(ser, 512,220)
  print "set_fan_speed 0"
  set_fan_speed(ser, 0)
  time.sleep(0.1)
  print '\nDone, now wasn\'t that dance fun?'








def main(argv):
  action = ''
  serial_port = ''
  ser = False
  initial_calibrate = True

  help_info = '''
pyLaser
------------------------
Expected Syntax:
  %s (-p <serial_port>) (-a <action>) (-nc)
    -p  = serial port, if not provided, it will ask
    -a  = action from action menu, if not provided, it will show menu and ask  * ignore options for now
    -c = no initial calibration
  ''' % os.path.basename(__file__)

  try:
    opts, args = getopt.getopt(argv,"hp:a:c",[])
  except getopt.GetoptError:
    print(help_info)
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
       print(help_info)
       sys.exit()
    elif opt in ("-c"):
       initial_calibrate = False
    elif opt in ("-a"):
       action = arg
    elif opt in ("-p"):
       serial_port = arg
    else:
      print 'unrecognized option: ' + opt



  if serial_port == '':
    print("Please wait (getting avail serial ports)...")
    avail_com_ports = get_avail_serial_ports()
    if len(avail_com_ports) == 0:
        print 'Fatal Error: No available serial ports detected.'
        sys.exit(1)      
    elif len(avail_com_ports) == 1:
      print('Connecting to: ' + avail_com_ports[0])
      ser = serial_connect(avail_com_ports[0])
      if not ser:
        print('Fatal Error: Unable to connect to the only available detected com port.')
        sys.exit(1)
    while not ser:
      print("Available Com Ports (restart the app to get new list)")
      print(avail_com_ports)
      print("\nQ to quit.")
      user_input = raw_input("\nWhat com port should we connect to? (case sensitive) ")
      if user_input.upper()=='Q':
        sys.exit()
      elif user_input in avail_com_ports:
        ser = serial_connect(user_input)
        if not ser:
          print('Error: could not connect to selected com port...')
  else:
    ser = serial_connect(serial_port)
    if not ser:
      print('Fatal Error: Unable to connect to the provided com port: ' + serial_port)
      sys.exit(1)


  print("\nInit Laser...")
  parse_init_resp(init_laser(ser))
  
  if initial_calibrate:
    print("\nCalibrating Laser...")
    laser_reset_calibrate(ser)

  if action == '':
    while True:
      print(r'''
        Action Menu:
          1) Chinese Laser Dance
          2) Vector Draw: Hi (delay 0.2)
           21) Vector Draw: Hi (Blink, delay 0.2)
           22) Vector Draw: Hi (Blink, skip 5, delay 0.2)
           23) Vector Draw: Hi (skip 5, delay 0.2)
          3) Vector Draw: Horizontal Line \ (skip 3, fast)
           31) Vector Draw: Horizontal Line \ (skip 1, slow)
           32) Vector Draw: Horizontal Line \ (skip 2, med)
          4) Vector Draw: Verticle Line \ (skip 3, fast)
           41) Vector Draw: Verticle Line \ (skip 1, slow)
           42) Vector Draw: Verticle Line \ (skip 2, med)
          5) Vector Draw: Angle Line \ (skip 3, fast) * Very inaccurate
           51) Vector Draw: Angle Line \ (skip 1, slow) * Very inaccurate
           52) Vector Draw: Angle Line \ (skip 2, med) * Very inaccurate
          6) Vector Draw: Angle Line \ (Blink, skip 3, fast) * More inaccurate
           61) Vector Draw: Angle Line \ (Blink, skip 1, slow) * More inaccurate
           62) Vector Draw: Angle Line \ (Blink, skip 2, med) * More inaccurate
          7) Raster Draw: Line with break         9) Raster Draw: Angle Line \       9B) Raster Draw: Vertical Line
          8) Raster Draw: Draw Shade Boxes        9A) Raster Draw: Horizontal Line   9C) Raster Draw: Vector Hi (skip 2)
          8B) Raster Draw: Grey Image #1 (hi)     8C) Raster Draw: Grey Image #2 (gradients) 8D) Raster Draw: test-nukecola.png
          * reset seems to be needed after some vector actions
        Lower Level Functions:
          I) Init Laser
          B) Reboot Laser       S) Stop Laser Raster Mode
          C) Calibrate/Reboot Laser
          P) Laser Power 0
            P#) Laser Power 0-10
          L) Laser Location (256, 256)     L5) Laser Location (0, 256)    L10) Laser Location (128, 128)
            L1) Laser Location (0, 0)      L6) Laser Location (256, 256)  L11) Laser Location (128, 384)
            L2) Laser Location (0, 512)    L7) Laser Location (256, 512)  L12) Laser Location (384, 384)
            L3) Laser Location (512, 512)  L8) Laser Location (512, 256)  L13) Laser Location (384, 128)
            L4) Laser Location (512, 0)    L9) Laser Location (256, 0)      
          R) Read Serial
          Q) Quit
        ''')

      user_input = raw_input("\nWhat action would you like to perform? ").upper()

      if user_input=='1':
        example_chinese_laser_dance(ser)
      elif user_input=='2':
        example_vector_hi(ser, False, 1, 0.2)
      elif user_input=='21':
        example_vector_hi(ser, True, 1, 0.2)
      elif user_input=='22':
        example_vector_hi(ser, True, 5, 0.2)
      elif user_input=='23':
        example_vector_hi(ser, False, 5, 0.2)
      elif user_input=='3':
        example_vector_draw_h_line(ser, 3)
      elif user_input=='31':
        example_vector_draw_h_line(ser, 1)
      elif user_input=='32':
        example_vector_draw_h_line(ser, 2)
      elif user_input=='4':
        example_vector_draw_v_line(ser, 3)
      elif user_input=='41':
        example_vector_draw_v_line(ser, 1)
      elif user_input=='42':
        example_vector_draw_v_line(ser, 2)
      elif user_input=='5':
        example_vector_draw_angle(ser, 3)
      elif user_input=='51':
        example_vector_draw_angle(ser, 1)
      elif user_input=='52':
        example_vector_draw_angle(ser, 2)
      elif user_input=='6':
        example_vector_draw_angle(ser, 3, True)
      elif user_input=='61':
        example_vector_draw_angle(ser, 1, True)
      elif user_input=='62':
        example_vector_draw_angle(ser, 2, True)
      elif user_input=='7':
        example_raster_draw_line_break(ser)
      elif user_input=='8':
        example_raster_draw_shades(ser, 1)
      elif user_input=='8B':
        example_raster_draw_grey_picture(ser, "test.png")
      elif user_input=='8C':
        example_raster_draw_grey_picture(ser, "test2.png")
      elif user_input=='8D':
        example_raster_draw_grey_picture(ser, "test-nukecola.png")
      elif user_input=='9':
        example_raster_draw_angle(ser, 2)
      elif user_input=='9A':
        example_raster_draw_h_line(ser, 2)
      elif user_input=='9B':
        example_raster_draw_v_line(ser, 2)
      elif user_input=='9C':
        example_raster_vector_hi(ser, 2, 0.105)
      elif user_input=='I':
        parse_init_resp( init_laser(ser) )
      elif user_input=='C':
        laser_reset_calibrate(ser)
      elif user_input=='S':
        stop_laser_raster_mode(ser)
        stop_laser_raster_grey_mode(ser)
      elif user_input=='B':
        parse_init_resp( laser_reboot(ser) )
      elif user_input=='P':
        set_laser_power(ser, 1)
      elif user_input=='P0':
        set_laser_power(ser, 0)
      elif user_input=='P1':
        set_laser_power(ser, 1)
      elif user_input=='P2':
        set_laser_power(ser, 2)
      elif user_input=='P3':
        set_laser_power(ser, 3)
      elif user_input=='P4':
        set_laser_power(ser, 4)
      elif user_input=='P5':
        set_laser_power(ser, 5)
      elif user_input=='P6':
        set_laser_power(ser, 6)
      elif user_input=='P7':
        set_laser_power(ser, 7)
      elif user_input=='P8':
        set_laser_power(ser, 8)
      elif user_input=='P9':
        set_laser_power(ser, 9)
      elif user_input=='P10':
        set_laser_power(ser, 10)
      elif user_input=='L':
        set_laser_position(ser, 256, 256)
      elif user_input=='L1':
        set_laser_position(ser, 0, 0)
      elif user_input=='L2':
        set_laser_position(ser, 0, 512)
      elif user_input=='L3':
        set_laser_position(ser, 512, 512)
      elif user_input=='L4':
        set_laser_position(ser, 512, 0)
      elif user_input=='L5':
        set_laser_position(ser, 0, 256)
      elif user_input=='L6':
        set_laser_position(ser, 256, 256)
      elif user_input=='L7':
        set_laser_position(ser, 256, 512)
      elif user_input=='L8':
        set_laser_position(ser, 512, 256)
      elif user_input=='L9':
        set_laser_position(ser, 256, 0)
      elif user_input=='L10':
        set_laser_position(ser, 128, 128)
      elif user_input=='L11':
        set_laser_position(ser, 128, 384)
      elif user_input=='L12':
        set_laser_position(ser, 384, 384)
      elif user_input=='L13':
        set_laser_position(ser, 384, 128)
      elif user_input=='R':
        print( "Payload=" + serial_read(ser) )
      elif user_input=='Q':
        sys.exit()
      else:
        print('Error: Invalid input received\n')


if __name__ == "__main__":
   main(sys.argv[1:])

