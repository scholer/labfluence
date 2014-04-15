
REM Python invocation arguments:
REM -i : Inspect interactively after running script.
REM -v : Increase python (stack trace) verbosity. Can be applied several times.
REM -m pdb : Run script through the python debugger. (Usually only used if you really want to debug; not for normal use).

REM Labfluence arguments:
REM -h, --help : print help
REM -i : (Run in interactive mode - not implemented yet)
REM --loglevel <level> : What log info level (ERROR/40, WARN/30, INFO/20, DEBUG/10) to print to stderr, e.g. "--loglevel DEBUG". Can also be an integer.
REM --debug <module> : Print debug log messages for <module>, e.g. "--debug model.server" to debug the server module.
REM NOTES:
REM - Labfluence will per default write log info to logs/labfluence_debug.log - This should also be affected by --loglevel.
REM - Labfluence can also be invoked with ipython --gui=tk (DEPENDS ON YOUR IPYTHON VERSION)

python -i labfluence.py --loglevel DEBUG
