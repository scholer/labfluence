#!/bin/bash

# Python invocation arguments:
# -i : Inspect interactively after running script.
# -v : Increase python (stack trace) verbosity. Can be applied several times.
# -m pdb : Run script through the python debugger. (Usually only used if you really want to debug; not for normal use).

# Labfluence arguments:
# -h, --help : print help
# -i : (Run in interactive mode - not implemented yet)
# --loglevel <level> : What log info level (ERROR/40, WARN/30, INFO/20, DEBUG/10) to print to stderr, e.g. "--loglevel DEBUG". Can also be an integer.
# --debug <module> : Print debug log messages for <module>, e.g. "--debug model.server" to debug the server module.
# NOTES:
# - Labfluence will per default write log info to logs/labfluence_debug.log - This should also be affected by --loglevel.
# - Labfluence can also be invoked with ipython --gui=tk (DEPENDS ON YOUR IPYTHON VERSION)

scriptpath=$(readlink -f $0)
scriptdir=`dirname $scriptpath`
echo "Scriptpath: $scriptpath"
echo "Scriptdir: $scriptdir"

# You should NOT change directory or anyting like that, since the user might expect local files from the current directory to be available.
python -i $scriptdir/labfluence.py --loglevel DEBUG
