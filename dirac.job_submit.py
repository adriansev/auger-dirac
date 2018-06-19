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
#se = ""

site_dirac = []
site_dirac.append(site_dirac_iss)
site_dirac.append(site_dirac_cesnet)

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

    j.setInputSandbox(input_file)
    input_file_base = os.path.basename(input_file)

    ## prepare the list of output files
    run_log = input_file_base + ".log" ## Name of log file based on input file name
    dat = input_file_base.replace('aug', 'DAT') ## final name of data file based on input file name
    datlong = dat + ".long" ## name of long files based on input file name

    ## colection of log files
    log_files_list = [ run_log, 'fluka11.out', 'fluka15.err',  input_file_base ]
    log_files = " ".join(log_files_list) ## convert list to string
    log_compress_args = "logs.tar.gz" + " " + log_files ## more log files can be added

    ## collection of data file(s)
    dat_compressed = dat + ".tar.gz"
    data_files_list = [ dat, datlong ]
    data_files = " ".join(data_files_list) ## convert list to string
    data_compress_args = dat_compressed + " " + data_files ## more data files can be added

    output_files = [ dat_compressed, 'logs.tar.gz' ]

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

    ### download the script for preparing corsika input file for usage with cvmfs
###    j.setExecutable( 'curl', arguments = ' -fsSLkO https://raw.githubusercontent.com/adriansev/auger-dirac/master/make_run4cvmfs',logFile='cmd_logs.log')
###    j.setExecutable( 'chmod', arguments = ' +x make_run4cvmfs',logFile='cmd_logs.log')

    ### create the simulation script configured for use with cvmfs
    ### set the make_run4cvmfs arguments to include the corsika_version and corsika_bin
    make_run4cvmfs_arg = input_file_base + " " + corsika_version + " " + corsika_bin
    j.setExecutable( '/cvmfs/auger.egi.eu/utils/make_run4cvmfs', arguments = make_run4cvmfs_arg, logFile='cmd_logs.log')

    ### run simulation
    j.setExecutable( './execsim',logFile='cmd_logs.log')

    ## compress logs/secondary files in a single archive
    j.setExecutable( 'tar -cvzf ', arguments = log_compress_args, logFile='cmd_logs.log')

    ## compress the data file(s)
    j.setExecutable( 'tar -cvzf ', arguments = data_compress_args, logFile='cmd_logs.log')

    if (TEST_JOB) :
        jobID = dirac.submit(j,mode='local')
    else :
        jobID = dirac.submit(j)

    id = str(jobID) + "\n"
    print 'Submission Result: ',jobID
    with open('jobids.list', 'a') as f_id_log:
        f_id_log.write(id + '\n')


