#!/bin/env python

##################################
###   STEERING VARIABLES
##################################
DO_NOT_SUBMIT = 0
TEST_JOB = 0
USE_DIRAC_CE_SE = 0
JOB_CPUTIME = 432000
JOB_NAME = 'AUGER simulation'

##################################
## this corsika versions will be used from CVMFS
#corsika_version = "corsika-76400_p1"
#corsika_bin = "corsika76400Linux_QGSII_fluka_thin"

corsika_version = "CORSIKA-74100_Fluka.2011.2c.2"
corsika_bin = "corsika74100Linux_QGSII_fluka_thin"

## Variable definitions
ce1 = "cream1.grid.cesnet.cz"
ce2 = "cream2.grid.cesnet.cz"
ce3 = "cream1.farm.particle.cz"

se_dirac_cesnet  = "CESNET-disk"
se_dirac_iss = "ROISS-disk"

site_dirac_cesnet = "LCG.CESNET.cz"
site_dirac_iss = "LCG.ROISS.ro"

##################################
# DEFINE WHERE THE JOB WILL BE RUN AND WHERE THE DATA WILL BE STORED
se = se_dirac_iss

site_dirac = []
site_dirac.append(site_dirac_iss)
##site_dirac.append(site_dirac_cesnet)

##################################
##################################
import os,re,sys,pprint

from DIRAC.Core.Base import Script
from COMDIRAC.Interfaces import DSession
from COMDIRAC.Interfaces import ConfigCache

Script.parseCommandLine()

from DIRAC.Interfaces.API.Job import Job
from DIRAC.Interfaces.API.Dirac import Dirac

import DIRAC.Core.Security.ProxyInfo as ProxyInfo

import DIRAC.FrameworkSystem.Client.ProxyGeneration as ProxyGeneration

from DIRAC.Core.Security import Locations, VOMS
from DIRAC.Core.Utilities.PrettyPrint import printTable

##################################
##################################
## Current pwd
session = DSession()
PWD = session.getCwd( )

## printer
pp = pprint.PrettyPrinter(indent=4)

## PROXY MANAGEMENT STUFF - before anything else
def _getProxyLocation():
  return Locations.getProxyLocation()

def _getProxyInfo( proxyPath = False ):
    if not proxyPath:
        proxyPath = _getProxyLocation()
    proxy_info = ProxyInfo.getProxyInfo( proxyPath, False )
    return proxy_info

proxy_info = _getProxyInfo()
if not proxy_info[ "OK" ]:
    print proxy_info[ "Message" ]
    sys.exit(os.EX_USAGE)

proxy_content_info = proxy_info[ "Value" ]
group = proxy_content_info["group"]

if ( group == "auger_prod"  ):
    print("user role : prod")
elif ( group == "auger_user"):
    print("user role : user")
else:
    print ("unknown role (not auger_prod nor auger_user) -> exiting..")
    sys.exit(os.EX_USAGE)

##################################
##################################
## Set base directory for storage of output files based on user role

prod_path = "/auger/prod"
base_output_path = ""

if ( group == "auger_prod"  ):
    base_output_path = prod_path
else:
    base_output_path = PWD

########################################################################################
########################################################################################
## CREATE LIST OF CORSIKA INPUT FILES
def get_filepaths(directory):
    file_paths = []  # List which will store all of the full filepaths.
    for root, directories, files in os.walk(directory):     # Walk the tree.
        files.sort()
        for filename in files:
            root = os.path.realpath(root)   ## get full path of the argument dir
            filepath = os.path.join(root, filename)  # Join the two strings in order to form the full filepath.
            file_paths.append(filepath)  # Add it to the list.
    return file_paths

######################################
##     BEGIN VARIABLES SETUP
######################################
arg2 = 0
arg3 = 0

if (len(sys.argv) < 2) :
    print ('the input directory should be specified')
    print ('if existent the 2nd argument (int) will be taken as index of the first job (inclusive)')
    print ('if existent the 3rd argument (int) will be taken as index of the last job (inclusive)')
    print ('example : ./dirac.job_submit.py <directory_with_corsika_files> <from_index> <to_index>')
    print ('example : ./dirac.job_submit.py ContpFeHeNQGSJETII4_20180417 1 500')
    print ('make both arguments equal to send a single job with the index of arguments')

    sys.exit(os.EX_USAGE)

path = sys.argv[1]
PROD_NAME = os.path.basename(os.path.normpath(path))

print ("Input directory: '{0}'".format(path))

##############################################################
full_file_paths = get_filepaths(path)
input_files = full_file_paths

## read the args for job range
if (len(sys.argv) >= 3) :
    arg2 = int(sys.argv[2])
    arg2 = max(arg2, 0) # if negative use 0

if (len(sys.argv) >= 4) :
    arg3 = int(sys.argv[3])
    arg3 = max(arg3, 0) # if negative use 0
    if (arg3 < arg2) :
        # protection in case that last index in range is lower than the first
        print ('WARNING !!!! :: second element in range smaller than the end element of range! setting arg3 = arg2')
        arg3 = arg2 + 1

first_job = int(0)
last_job = int(len(full_file_paths))

if (arg2 > 0) : first_job = arg2 - 1 # first file corespond to index 0
if (arg3 > 0) : last_job = arg3 # last index is array lenght - not included in loop

##  MAIN LOOP OVER ALL INPUT FILES
for idx, input_file in enumerate ( input_files[int(first_job):int(last_job)] ) :
#    print "Input file is : {}".format(input_file)
    print '\nInput file is : ', input_file

    ## GET RUN NUMBER FROM INPUT FILE
    f = open(input_file, 'r')
    runnr = -1
    e_min = -1
    e_max = -1
    theta_min = -1
    theta_max = -1
    prmpar = -999
    nr_line = 0

    # READ VARIABLES FOR CORSIKA INPUT FILE FOR DETERMINATION OF OUTPUT PATH
    for line in f:
        nr_line += 1
        line = line.strip()
        columns = line.split()
        if ( columns[0] == "RUNNR" ) :
            runnr = columns[1]
        if ( columns[0] == "PRMPAR" ) :
            prmpar = columns[1]
        if ( columns[0] == "ERANGE" ) :
            e_min = columns[1]
            e_max = columns[2]
        if ( columns[0] == "THETAP" ) :
            theta_min = columns[1]
            theta_max = columns[2]

    f.close()

    if runnr == -1 :
        print "Something is wrong with determination of run number from input file"
        break

    print "runnr = '{0}'".format(runnr)
    print "prmpar = '{0}'".format(prmpar)
    print "Energy Min = '{0}'".format(e_min)
    print "Energy Max = '{0}'".format(e_max)
    print "Theta Min = '{0}'".format(theta_min)
    print "Theta Max = '{0}'".format(theta_max)

    ######################################
    ##     BEGIN JOB DESCRIPTION
    ######################################
    dirac = Dirac(withRepo=True, repoLocation='jobid.list', useCertificates=False)
    j = Job(script=None, stdout='submission.out', stderr='submission.err')

    input_files_list = []
    input_files_list.append(input_file)
    j.setInputSandbox(input_files_list)
    input_file_base = os.path.basename(input_file)

    # set the list of output files
    output_files = [ 'data.tar.gz', 'logs.tar.gz' ]

    ## prepare the output location in GRID storage; the input path will be the used also for GRID storage
    # outdir = grid_basedir_output + PROD_NAME + "/" + str(e_min) + "_" + str(e_max) + "/" + str(theta_min) + "_" + str(theta_max) + "/" + str(prmpar) + "/" + str(runnr)
    # outdir = "/" + PROD_NAME + "/" + str(e_min) + "_" + str(e_max) + "/" + str(theta_min) + "_" + str(theta_max) + "/" + str(prmpar) + "/" + str(runnr)
    outdir = "/" + PROD_NAME + "/" + str(e_min) + "/" + str(theta_min) + "/" + str(prmpar) + "/" + str(runnr)

    print 'SE = ',se

    lfns_list = []
    if ( group == "auger_prod"  ):
        base_output_path = prod_path
        ## add base directory to each file to have a list of lfns
        for f in output_files:
            lfn = "LFN:" + base_output_path + outdir + "/" + f
            lfns_list.append(lfn)

        j.setOutputData(lfns_list, outputSE=se)
        print 'Output - list of lfns :'
        pp.pprint (lfns_list)
    else:
##        base_output_path = PWD
        j.setOutputData(output_files, outputSE=se, outputPath=outdir)
        print 'Output files = ', output_files
        print 'outputPath = ', outdir

#####################
##   PREPARE JOB   ##
#####################
    if (DO_NOT_SUBMIT):
        sys.exit(os.EX_USAGE)

    ### ALWAYS, INFO, VERBOSE, WARN, DEBUG
    j.setLogLevel('debug')

    j.setDestination(site_dirac)

    JOB_IDX = first_job + 1 + idx
    JOB_NAME = PROD_NAME + " IDX_" + str(JOB_IDX)
    print '\nJOB NAME is : ', JOB_NAME

    j.setName(JOB_NAME)
    j.setCPUTime(JOB_CPUTIME) ## 4 days

    run_corsika_sim_args = input_file_base + " " + corsika_version + " " + corsika_bin
    j.setExecutable( './run_corsika_sim', arguments = run_corsika_sim_args, logFile='run_sim.log')

    if (TEST_JOB) :
        jobID = dirac.submit(j,mode='local')
    else :
        jobID = dirac.submit(j)

    id = str(jobID) + "\n"
    print 'Submission Result: ',jobID
    with open('jobids.list', 'a') as f_id_log:
        f_id_log.write(id + '\n')


