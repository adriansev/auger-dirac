#!/bin/env python

import re,sys,json
from StringIO import StringIO

from DIRAC.Core.Base import Script
Script.parseCommandLine()

from DIRAC.Interfaces.API.Job import Job
from DIRAC.Interfaces.API.Dirac import Dirac

if (len(sys.argv) < 2) :
    print 'the input file with ids should be specified'
    print 'if the 3rd argument is <get_output> the job output sandbox will be downloaded'
    sys.exit(os.EX_USAGE)

list = sys.argv[1]

get_output = False
if (len(sys.argv) > 2):
    if (sys.argv[2] == 'get_output'): get_output = True

id_list_file = open(list, 'r')

for line in id_list_file:
##    line = line.strip().decode("utf-8").replace("True","true").replace("False","false")
    line = line.replace("True","true").replace("False","false")
    line = line.replace("'","\"")
    j = json.loads(line)

    dirac = Dirac()
    print dirac.status(j['Value'])

    if get_output: print dirac.getOutputSandbox(j['Value'])

id_list_file.close()

