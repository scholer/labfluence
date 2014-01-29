#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2013 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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
#pylint: disable-msg=W0212
"""

Labfluence module for adding and managing of an inventory page,
i.e. a primitive Laboratory Inventory Management System (LIMS).

"""

import argparse
import os


### MODEL IMPORT ###
from model.confighandler import ExpConfigHandler
from model.server import ConfluenceXmlRpcServer

### TEST DOUBLES IMPORT ###
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer

from tkui.lims_app import LimsApp

import logging
import logging.handlers
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Labfluence LIMS mode.")
    #parser.add_argument('-o', '--outputfilenamefmt', help="How to format the filename of the robot output file (*.dws)")
    #parser.add_argument('--plateconc', metavar='<conc_in_uM>', help="Specify the concentration of the plates. Used as information in the report file.")
    #parser.add_argument('--nofiltertips', action='store_true', help="Do not use filter-tips. Default is false (= do use filter tips)")
    #parser.add_argument('-r', '--rackfiles', nargs='*', help="Specify which rackfiles to use. If not specified, all files ending with *.rack.csv will be used. This arguments will take all following arguments, and can thus be used as staplemixer -r *.racks")
    parser.add_argument('--testing', action='store_true', help="Start labfluence in testing environment.")
    parser.add_argument('--logtofile', help="Log logging outputs to this file.")
    parser.add_argument('--loglevel', default=logging.WARNING, help="The log level printed to stderr.")
    parser.add_argument('--debug', metavar='<MODULES>', nargs='*', # default defaults to None.
                        help="Specify modules where you want to display logging.DEBUG messages.")
    parser.add_argument('--pathscheme', default='default1', help="Specify a particular pathscheme to use for the confighandler, e.g. 'default1', 'test1', etc....")
    parser.add_argument('--pageid', help="Specify a costum pageId for the Wiki LIMS page. \
                        If not specified, will use wiki_lims_pageid from config.")
    parser.add_argument('files', nargs='*', help="Order file(s) to add. \
                        Use --singlebatch if all files are for a single LIMS entry. \
                        (default: one new entry per file.)")


    argsns = parser.parse_args() # produces a namespace, not a dict.


    # Examples of different log formats:
    #logfmt = "%(levelname)s: %(filename)s:%(lineno)s %(funcName)s() > %(message)s"
    logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    logfilefmt = '%(asctime)s %(levelname)6s - %(name)s:%(lineno)s - %(funcName)s() - %(message)s'
    datefmt = "%Y%m%d-%H:%M:%S" # "%Y%m%d-%Hh%Mm%Ss"
    if not os.path.exists('logs'):
        os.mkdir('logs')
    if argsns.logtofile:
        logfilepath = argsns.logtofile
    else:
        logfilepath = 'logs/labfluence_lims_testing.log' if argsns.testing else 'logs/labfluence_lims_debug.log'

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
    # logging.basicConfig(level=logging.DEBUG, format=logfilefmt, datefmt=datefmt, filename=logfilepath)
    # Note: basicConfig does not do anything super special, it simply: (c.f. source)
    # - checks if root.handlers is empty
    # - creates a FileHandler or StreamHandler, and a Formatter
    # - hdlr.setFormatter(fmt) and then root.addHandler(hdlr)

    # Set up custom file logger:
    rootlogger = logging.getLogger('')
    rootlogger.setLevel(logging.DEBUG)
    #logfilehandler = logging.FileHandler(logfilepath)
    logfilehandler = logging.handlers.RotatingFileHandler(logfilepath, maxBytes=2*2**20, backupCount=3)
    logfileformatter = logging.Formatter(fmt=logfilefmt, datefmt=datefmt)
    logfilehandler.setFormatter(logfileformatter)
    rootlogger.addHandler(logfilehandler)

    # Add a custom StreamHandler for outputting to the user (default level is 0 = ANY)
    logstreamhandler = logging.StreamHandler()
    rootlogger.addHandler(logstreamhandler)
    logstreamformatter = logging.Formatter(logfmt)
    logstreamhandler.setFormatter(logstreamformatter)
    # Determine and set loglevel for streamhandler (outputs to sys.stderr)
    if argsns.debug is None:
        try:
            loglevel = int(argsns.loglevel)
        except ValueError:
            loglevel = getattr(logging, argsns.loglevel.upper(), None)
        logstreamhandler.setLevel(loglevel)
    elif argsns.debug: # argsns.debug is a non-empty list:
        logstreamhandler.setLevel(logging.INFO)
        for mod in argsns.debug:
            logger.info("Enabling logging debug messages for module: %s", mod)
            logging.getLogger(mod).setLevel(logging.DEBUG)
    else: # argsns.debug is an empty list:
        logstreamhandler.setLevel(logging.DEBUG)

    # Set up environments: (testing / production)
    if argsns.testing:
        # Other modules should be enabled with --debug <modules>.
        logging.getLogger("model.server").setLevel(logging.DEBUG)
        logging.getLogger("model.limspage").setLevel(logging.DEBUG)
        logging.getLogger("model.page").setLevel(logging.DEBUG)
        logging.getLogger("model.model_testdoubles.fake_confighandler").setLevel(logging.DEBUG)
        logging.getLogger("model.model_testdoubles.fake_server").setLevel(logging.DEBUG)
        logging.getLogger("tkui.lims_app").setLevel(logging.DEBUG)
        logging.getLogger("tkui.lims_tkroot").setLevel(logging.DEBUG)
        #logging.getLogger("tkui.views.lims_frame").setLevel(logging.DEBUG)
        logging.getLogger(__name__).setLevel(logging.DEBUG)
        logger.debug("Loggers setting to debug level...")
        pathscheme = argsns.pathscheme or 'test1'
        logger.info( "Enabling testing environment..." )
        confighandler = FakeConfighandler(pathscheme=pathscheme)
        # set basedir for exp:
        confighandler.ConfigPaths['exp'] = os.path.join('tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup', '.labfluence.yml')
        server = FakeConfluenceServer(confighandler=confighandler)
    else:
        logger.debug(">>>>>> Initiating real confighandler and server... >>>>>>")
        pathscheme = argsns.pathscheme or 'default1'
        confighandler = ExpConfigHandler(pathscheme=argsns.pathscheme)
        logger.debug("Confighandler instantiated, Initiating server... >>>>>>")
        # setting autologin=False during init should defer login attempt...
        server = ConfluenceXmlRpcServer(autologin=False, confighandler=confighandler)
        server._autologin = True
    confighandler.Singletons['server'] = server
    logger.debug(">>>>>> Server instantiated, starting LimsApp... >>>>>>")
    limsapp = LimsApp(confighandler)
    logger.debug(">>>>>> LimsApp instantiated, adding files: %s... >>>>>>", argsns.files)
    limsapp.FilesToAdd = argsns.files
    #limsapp.addEntriesForFiles(argsns.files)
    logger.debug("Starting LIMS app loop...")
    #limsapp.start()
    limsapp.main()
    logger.debug("lims complete.")
