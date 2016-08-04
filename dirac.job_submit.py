import os,re,sys,argparse

from DIRAC.Core.Base import Script
Script.parseCommandLine()

from DIRAC.Interfaces.API.Job import Job
from DIRAC.Interfaces.API.Dirac import Dirac

def get_filepaths(directory):
    file_paths = []  # List which will store all of the full filepaths.
    for root, directories, files in os.walk(directory):     # Walk the tree.
        for filename in files:
            root = os.path.realpath(root)   ## get full path of the argument dir
            filepath = os.path.join(root, filename)  # Join the two strings in order to form the full filepath.
            file_paths.append(filepath)  # Add it to the list.
    return file_paths

######################################
##     BEGIN VARIABLES SETUP
######################################

## path="simulation_run_test_tag_XYZ_v3"

if (len(sys.argv) < 2) :
    print 'the input directory should be specified'
    sys.exit(os.EX_USAGE)

path = sys.argv[1]
print "Input directory: '{0}'".format(path)

full_file_paths = get_filepaths(path)
input_files = full_file_paths

## Variable definitions
se = "dpm1.egee.cesnet.cz"
ce1 = "cream1.grid.cesnet.cz"
ce2 = "cream2.grid.cesnet.cz"
ce3 = "cream1.farm.particle.cz"
site = "prague_cesnet_lcg2"
se_dirac = "CESNET-disk"
site_dirac = "LCG.CESNET.cz"
corsika_version = "CORSIKA-74100_Fluka.2011.2c.2"
corsika_bin = "corsika74100Linux_QGSII_fluka_thin"

## root dir for job output storage
grid_basedir_output = "/grid/auger/user/asevcenc/"

##  MAIN LOOP OVER ALL INPUT FILES
for input_file in input_files:
    print "Input file is : '{0}'".format(input_file)

    ## GET RUN NUMBER FROM INPUT FILE
    f = open(input_file, 'r')
    runnr = -1

    for line in f:
            line = line.strip()
            columns = line.split()
            runnr = columns[1]
            break

    f.close()

    if runnr == -1 :
        print "Something is wrong with determination of run number from input file"
        break

    print "runnr = '{0}'".format(runnr)

    ######################################
    ##     BEGIN JOB DESCRIPTION
    ######################################
    dirac = Dirac(withRepo=True, repoLocation='jobid.list', useCertificates=False)
    j = Job(script=None, stdout='submission.out', stderr='submission.err')

    j.setInputSandbox(input_file)
    input_file_base = os.path.basename(input_file)

    ## prepare the list of output files
    run_log = input_file_base + ".log"
    dat = input_file_base.replace('aug', 'DAT')
    datlong = dat + ".long"
    output_files= [run_log, 'fluka11.out', 'fluka15.err', dat, datlong ]

    ## prepare the output location in GRID storage; the input path will be the used also for GRID storage
    outdir = grid_basedir_output + path + "/" + str(runnr)

    ## ALWAYS, INFO, VERBOSE, WARN, DEBUG
    j.setLogLevel('debug')

    j.setName('AUGER test simulation')

    j.setDestinationCE(ce1)
    ##    j.setDestination(site_dirac)

    j.setCPUTime(345600) ## 4 days

    ## download the script for preparing corsika input file for usage with cvmfs
    j.setExecutable( 'curl', arguments = ' -fsSLkO http://issaf.spacescience.ro/adrian/AUGER/make_run4cvmfs',logFile='cmd_logs.log')
    j.setExecutable( 'chmod', arguments = ' +x make_run4cvmfs',logFile='cmd_logs.log')

    ## create the simulation script configured for use with cvmfs
    ## set the make_run4cvmfs arguments to include the corsika_version and corsika_bin
    make_run4cvmfs_arg = input_file_base + " " + corsika_version + " " + corsika_bin
    j.setExecutable( './make_run4cvmfs', arguments = make_run4cvmfs_arg, logFile='cmd_logs.log')

    ## run simulation
    j.setExecutable( './execsim',logFile='cmd_logs.log')

    j.setOutputSandbox(output_files)
    j.setOutputData(output_files, outputSE=se, outputPath=outdir)

    ##j.runLocal()  ## test local

    jobID = dirac.submit(j)
    print 'Submission Result: ',jobID

    id = str(jobID) + "\n"

    with open('jobids.list', 'a') as f_id_log:
        f_id_log.write(jobID.Value + '\n')


