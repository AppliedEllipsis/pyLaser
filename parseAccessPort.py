#!/usr/bin/env python2

import os, sys, getopt, re


module_info = {
'NAME': "Parse AccessPort Com Save",
'ORIGINAL_ARTHOR': "Applied Ellippsis", # leave this
'ARTHOR': "Applied Ellipsis", # change this to you
'DESCRIPTION': '''
Tool to convert the output of AccessPort to something more usable.
''',
'REPO_URL': 'https://github.com/AppliedEllipsis/pyLaser',
'VERSION': "0.1a",
'LICENSE': "See License.txt, but GPLv3 for the lazy",
}


def parse_AccessPort_output(dat):
  # remove header
  dat = dat.split("( Hex )")
  if (len(dat) > 1):
    dat = dat[1]
  else:
    dat = dat[0]
  # remove control lines
  dat = re.sub(r'.*IOCTL_SERIAL_WAIT_ON_MASK.*\n|.*IOCTL_SERIAL_PURGE.*\n','',dat)
  # simplify read/write lines
  dat = re.sub(r'.*IRP_MJ_(READ|WRITE).*Data: (.{2}).*\n',r'\1=\2\n',dat)
  # bring FF to the previous line
  dat = re.sub(r'\n(READ|WRITE)=FF\n',r' FF\n',dat)
  # bring FF FF to previous line
  dat = re.sub(r'\nREAD=(.+FF)\n+READ=FF\n',r'\nREAD=\1 FF\n\n',dat)
  dat = re.sub(r'\nWRITE=(.+FF)\n+WRITE=FF\n',r'\nWRITE=\1 FF\n\n',dat)
  # merge multiple writes to single write
  p = re.compile(r'WRITE=(.*)(?<!FF)\n+WRITE=')
  while True:
    tmp_dat = p.subn(r'\nWRITE=\1 ',dat)
    dat = tmp_dat[0]
    if tmp_dat[-1] == 0:
      break
  # # merge multiple reads to single read
  p = re.compile(r'READ=(.*)(?<!FF)\n+READ=')
  while True:
    tmp_dat = p.subn(r'\nREAD=\1 ',dat)
    dat = tmp_dat[0]
    if tmp_dat[-1] == 0:
      break
  #remove multiple spacing
  p_space = re.compile(r'\n\n')
  while True:
    tmp_dat = p_space.subn(r'\n',dat)
    dat = tmp_dat[0]
    if tmp_dat[-1] == 0:
      break 
  dat = re.sub(r'\n\n',r' \n',dat)
  return dat


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

