#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2013-2014 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
##
##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##
# pylint: disable=C0103,W0212

import os
import logging
import logging.handlers
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)
def getLoglevelInt(loglevel, defaultlevel=None):
    """
    Used to ensure that a value is a valid loglevel integer.
    If loglevel is already an integer, or a string representation of an interger, this integer is returned.
    If loglevel is a registrered level NAME (e.g. DEBUG, INFO, WARNING, ERROR), the correspoinding integer value is returned.
    If anything fails, falls back to defaultlevel (if provided), or else logging.WARNING.
    """
    if defaultlevel is None:
        defaultlevel = logging.WARNING
    try:
        loglevel = int(loglevel)
    except ValueError:
        loglevel = getattr(logging, loglevel.upper(), defaultlevel)
    except AttributeError:
        # no loglevel argument defined by argparse
        loglevel = defaultlevel
    return loglevel




def init_logging(argsns, prefix="labfluence"):
    """
    Set up standard Labfluence logging system based on values provided by argsns, namely:
    - loglevel
    - logtofile
    - testing

    """

    # Examples of different log formats:
    #logfmt = "%(levelname)s: %(filename)s:%(lineno)s %(funcName)s() > %(message)s"
    #logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    # loguserfmt = format of log displayed to the user; logfilefmt = format of log messages written to logfile.
    loguserfmt = "%(asctime)s %(levelname)-5s %(name)20s:%(lineno)-4s%(funcName)20s() %(message)s"
    logfilefmt = '%(asctime)s %(levelname)-6s - %(name)s:%(lineno)s - %(funcName)s() - %(message)s'
    logdatefmt = "%Y%m%d-%H:%M:%S" # "%Y%m%d-%Hh%Mm%Ss"
    logtimefmt = "%H:%M:%S" # Output to user in console
    logfiledir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(logfiledir):
        os.mkdir(logfiledir)
    if argsns.logtofile:
        logfilepath = argsns.logtofile
    else:
        logfilenameformat = '{}_testing.log' if getattr(argsns, 'testing', False) else '{}_debug.log'
        logfilename = logfilenameformat.format(prefix)
        logfilepath = os.path.join(logfiledir, logfilename)

    loglevel = getLoglevelInt(argsns.loglevel)

    # Logging concepts based on:
    # - http://docs.python.org/2/howto/logging.html
    # - http://docs.python.org/2/howto/logging-cookbook.html
    # Notice: If basicConfig level is set to INFO, it is as though no levels below
    # INFO level will ever be printet regardless of what streamhandler is used.
    # And that makes sense, c.f. http://docs.python.org/2/howto/logging.html#logging-flow
    # Even though a *handler* has a low log level, the log item enters via a *logger*, which
    # generally is simply the root logger (which is the logger used by debug(), info(), etc...)
    # (you can set a logger's .propagate attribute to False to prevent the item from being
    # passed to the logger's parent...)
    # If the loglevel of the *logger* is above the item's level, the logger simply rejects the log item.
    # To change this, you should change the root-logger's level: logging.getLogger('').setLevel(...)
    # You can retrieve individual handlers specifically from <rootlogger>.handlers.

    # Set up basic logging using a file (FileHandler):
    # logging.basicConfig(level=logging.DEBUG, format=logfilefmt, datefmt=logdatefmt, filename=logfilepath)
    # Note: basicConfig does not do anything super special, it simply: (c.f. source)
    # - checks if root.handlers is empty
    # - creates a FileHandler or StreamHandler, and a Formatter
    # - hdlr.setFormatter(fmt) and then root.addHandler(hdlr)

    # Set up custom file logger:
    #rootlogger = logging.root
    logging.root.setLevel(logging.DEBUG)
    #logfilehandler = logging.FileHandler(logfilepath)
    logfilehandler = logging.handlers.RotatingFileHandler(logfilepath, maxBytes=2*2**20, backupCount=3)
    logfileformatter = logging.Formatter(fmt=logfilefmt, datefmt=logdatefmt)
    logfilehandler.setFormatter(logfileformatter)
    logging.root.addHandler(logfilehandler)

    # Add a custom StreamHandler for outputting to the user (default level is 0 = ANY)
    logstreamhandler = logging.StreamHandler()
    logging.root.addHandler(logstreamhandler)
    logstreamformatter = logging.Formatter(loguserfmt, logtimefmt)
    logstreamhandler.setFormatter(logstreamformatter)

    # And a special log handler for debug messages:
    # This is added to the loggers of individual modules in order to output
    # debug info even if the root logger is set to a higher loglevel.
    logdebughandler = logging.StreamHandler()
    logdebughandler.setFormatter(logstreamformatter)

    # Determine and set loglevel for streamhandler (outputs to sys.stderr)
    if argsns.debug is None:
        # --debug is NOT specified...
        logstreamhandler.setLevel(loglevel)
        if loglevel < logfilehandler.level:
            logfilehandler.setLevel(loglevel)
    elif argsns.debug: # argsns.debug is a non-empty list:
        # Edit: Initially, here I would just decrease the loglevel of individual loggers.
        # However, c.f. the log flowchart, even if individual loggers are set to DEBUG level,
        # the item will still be discarted by the root logger or the logstreamhandler if any
        # of these have a loglevel higher than DEBUG (e.g. INFO). Thus, you will need to set up
        # another handler for these loggers and possibly also set up a filter or something.
        # If you set modulelogger.propagate=False, then you need to make sure the logfilehandler
        # is added to the modulelogger in addition to the new streamhandler.
        logstreamhandler.setLevel(loglevel)
        for modlogger in (logging.getLogger(mod) for mod in argsns.debug):
            logger.info("Enabling logging debug messages for module: %s", modlogger.name)
            #modlogger.setLevel(logging.DEBUG) # Should have no effect; new loggers have a default level of 0.
            modlogger.addHandler(logdebughandler)
            modlogger.addHandler(logfilehandler)
            modlogger.propagate = False
    else: # argsns.debug is an empty list:
        logstreamhandler.setLevel(logging.DEBUG)

    return {"filehandler": logfilehandler, "streamhandler": logstreamhandler, "debughandler": logdebughandler}
