#!/bin/env python

import sys

from DIRAC.Core.Base import Script
Script.parseCommandLine()

from DIRAC.Interfaces.API.Job import Job
from DIRAC.Interfaces.API.Dirac import Dirac

dirac = Dirac()
jobid = sys.argv[1]
print dirac.status(jobid)

