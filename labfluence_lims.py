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
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)

#from labfluence import init_logging
from __init__ import init_logging


if __name__ == '__main__':


    #####################################
    ### Basic command line arguments ####
    #####################################

    parser = argparse.ArgumentParser(description="Labfluence LIMS mode.")
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


    #######################################
    ### Set up standard logging system ####
    #######################################
    init_logging(argsns, prefix="labfluence_lims")


    ####################################################################################
    # Set up confighandler, etc (depending on whether testing mode is requested...) ####
    ####################################################################################
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
        logger.debug("<<<<< Confighandler instantiated, Initiating server... >>>>>")
        # setting autologin=False during init should defer login attempt...
        server = ConfluenceXmlRpcServer(autologin=False, confighandler=confighandler)
        server._autologin = True

    # Init server and application:
    confighandler.Singletons['server'] = server
    logger.debug("<<<<< Server instantiated, starting LimsApp... >>>>>")
    limsapp = LimsApp(confighandler)
    logger.debug("LimsApp instantiated, adding files: %s", argsns.files)
    limsapp.FilesToAdd = argsns.files
    #limsapp.addEntriesForFiles(argsns.files)

    # Start main application loop:
    logger.debug(">>>> Starting LIMS app main loop >>>>")
    limsapp.main()
    logger.debug("<<<<<< LIMS APP COMPLETE <<<<<<<")
