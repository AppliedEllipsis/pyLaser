#!/usr/bin/env python2

import os, sys, getopt, re


module_info = {
'NAME': "Process Grey Raster data from parsed AccessPort Com Save",
'ORIGINAL_AUTHOR': "Applied Ellippsis", # leave this
'AUTHOR': "Applied Ellipsis", # change this to you
'DESCRIPTION': '''
Tool to take the parsed AccessPort data and show coordinates and grey values as integers for easier analysis.
''',
'REPO_URL': 'https://github.com/AppliedEllipsis/pyLaser',
'VERSION': "0.1a",
'LICENSE': "See License.txt, but GPLv3 for the lazy",
}


def parse_AccessPort_output(dat):
  output = ""
  for line in dat.split("\n"):
    # print len(line)
    if 'WRITE=' in line and len(line)==26:
      try:
        output += line + "\t\t\t\t(" + str( (ord(line[9:11].decode("hex")) * 100) + ord(line[12:14].decode("hex")) ) + "," + str( ord(line[15:17].decode("hex")) * 100 + ord(line[18:20].decode("hex")) ) + ") = " + str( ord(line[21:23].decode("hex")) ) + "\n"
      except:
        output += line + "\t\t\t\tError\n"
    else:
      output += line + "\n"
  return output




def main(argv):
  file_in = ''
  file_out = '' 


  help_info = '''
Parse AccessPort Output
------------------------
Expected Syntax:
  %s -i <file_in> (-o <file_out>)
    -i  = input file * required
    -o  = output file * if not provided, it will output to screen
  ''' % os.path.basename(__file__)

  try:
    opts, args = getopt.getopt(argv,"hi:o:",[])
  except getopt.GetoptError:
    print(help_info)
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
       print(help_info)
       sys.exit()
    elif opt in ("-i"):
       file_in = arg
    elif opt in ("-o"):
       file_out = arg
  if file_in == '' and not os.path.isfile(file_in):
    print(help_info)
    print("Error: Missing file_in")
    sys.exit()
  if file_out != '':
    if os.path.isfile(file_out):
      i = raw_input("\nWARNING: file_out already exists, type Y{enter} to overwrite or enter stop.  ").upper()
      if i != 'Y':
        print "\n\tNo file written"
        sys.exit()

  with open(file_in, 'r') as f:
    dat = f.read() 
  dat = parse_AccessPort_output(dat)

  if file_out != '':
    with open(file_out, 'w') as f:
      f.write(dat) 
  else:
    print(dat)

if __name__ == "__main__":
   main(sys.argv[1:])

