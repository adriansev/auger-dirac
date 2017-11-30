#!/bin/env python

import sys

from DIRAC.Core.Base import Script
Script.parseCommandLine()

from DIRAC.Interfaces.API.Job import Job
from DIRAC.Interfaces.API.Dirac import Dirac

dirac = Dirac()
jobid = sys.argv[1]

print dirac.status(jobid)

summary_file = str(jobid) + "_summary.txt"
dirac.getJobSummary(jobid, outputFile=summary_file, printOutput=True)

print dirac.getJobDebugOutput(jobid)

print dirac.getJobLoggingInfo(jobid, printOutput=False)

