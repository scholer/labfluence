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

# python 3.x:
#from tkinter import ttk
# python 2.7:
import Tkinter as tk
import ttk
import tkFont

# Other standard lib modules:
import socket
import argparse
import os

from datetime import datetime
from collections import OrderedDict
import logging
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)



### MODEL IMPORT ###
from model.confighandler import ExpConfigHandler
from model.experimentmanager import ExperimentManager
from model.experiment import Experiment
from model.server import ConfluenceXmlRpcServer

### TEST DOUBLES IMPORT ###
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer

### GUI IMPORTS ###
from tkui.labfluence_tkapp import LabfluenceApp

#from views.expnotebook import ExpNotebook, BackgroundFrame
#from views.experimentselectorframe import ExperimentSelectorWindow
#from views.dialogs import Dialog

#from controllers.listboxcontrollers import ActiveExpListBoxController, RecentExpListBoxController
#from controllers.filemanagercontroller import ExpFilemanagerController
#from ui.fontmanager import FontManager




if __name__ == '__main__':

    ###########################
    #### LOGGER SETUP #########
    ###########################

    #logging.basicConfig(level=logging.DEBUG)
    # basicConfig is intended to quickly set up the logging system for
    # If handlers are already set up, basicConfig should do nothing
    # Invoking basicConfig will also attach default handlers to loggers.
    # arguments are:
    # - filename, filemode [or] stream --> switch to file-based logging, OR use stream instead of stderr
    # - format, datefmt --> default format
    # - level  --> set minimum level to be logged. (logging.DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50)
    # also interesting is: logging.root <- root logger
    # The extended way of setting up the logging system is to instantiate one or more handlers:
    # handler1 = logging.Steamhandler(); handler2 = logging.handlers.HTTPhandler
    # handlers can be associated with loggers with logger.addHandler(handler), including the root loggig.RootLogger
    # each handler can have a custom Formatter associated:
    # formatter1 = logging.Formatter(fmt=<format string>, datefmt=<date format>)
    # msg format use old string interpolation, %(placeholder)s, where placeholder can be a logrecord attribute:
    # LogRecord attributes include: name, levelname, filename, lineno, funcName,
    # debugformatter = logging.Formatter("%(levelname)s: %(filename)s:%(lineno)s %(funcName)s > %(message)")
    # the logging module offers advanced introspection with
    # curframe = logging.currentframe(); traceback = curframe.f_trace

    # Note that attaching custom handler+formatter to a logger is still quite ok even after
    # calling logging.basicConfig(), just make sure to set logger.propagate=0,
    # otherwise any records will be emitted both by the custom handler and the root logger.

    # Examples of different log formats:
    #logfmt = "%(levelname)s: %(filename)s:%(lineno)s %(funcName)s() > %(message)s"
    logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    #logfmt = "%(levelname)s:%(name)s: %(funcName)s() :: %(message)s"
    logging.basicConfig(level=logging.INFO, format=logfmt)



    ###########################
    #### ARG PARSING ##########
    ###########################

    parser = argparse.ArgumentParser(description="Labfluence - Experiment manager with Confluence connector.")
    #parser.add_argument('-o', '--outputfilenamefmt', help="How to format the filename of the robot output file (*.dws)")
    #parser.add_argument('--plateconc', metavar='<conc_in_uM>', help="Specify the concentration of the plates. Used as information in the report file.")
    #parser.add_argument('--nofiltertips', action='store_true', help="Do not use filter-tips. Default is false (= do use filter tips)")
    #parser.add_argument('-r', '--rackfiles', nargs='*', help="Specify which rackfiles to use. If not specified, all files ending with *.rack.csv will be used. This arguments will take all following arguments, and can thus be used as staplemixer -r *.racks")
    parser.add_argument('--testing', action='store_true', help="Start labfluence in testing environment.")
    parser.add_argument('--debug', nargs='*', help="Specify modules where you want to display logging.DEBUG messages.")
    parser.add_argument('--pathscheme', help="Specify a particulra pathscheme to use for the confighandler.")

    argsns = parser.parse_args() # produces a namespace, not a dict.


    if argsns.debug:
        for mod in argsns.debug:
            logger.info("Enabling logging debug messages for module: %s", mod)
            logging.getLogger(mod).setLevel(logging.DEBUG)

    if argsns.testing:
        # These should be enabled with --debug <modules>.
        #logging.getLogger("tkui.views.expjournalframe").setLevel(logging.DEBUG)
        #logging.getLogger("tkui.views.shared_ui_utils").setLevel(logging.DEBUG)
        #logging.getLogger("tkui.views.explistboxes").setLevel(logging.DEBUG)
        #logging.getLogger("controllers.listboxcontrollers").setLevel(logging.DEBUG)
        #logging.getLogger("model.journalassistant").setLevel(logging.DEBUG)
        #logging.getLogger("model.experiment").setLevel(logging.DEBUG)
        #logging.getLogger("model.experiment_manager").setLevel(logging.DEBUG)
        #logging.getLogger("model.confighandler").setLevel(logging.DEBUG)
        #logging.getLogger("model.confighandler").setLevel(logging.DEBUG)
        #logging.getLogger("model.server").setLevel(logging.DEBUG)
        logging.getLogger("model.model_testdoubles.fake_confighandler").setLevel(logging.DEBUG)
        logging.getLogger("model.model_testdoubles.fake_server").setLevel(logging.DEBUG)
        logging.getLogger("tkui.labfluence_tkapp").setLevel(logging.DEBUG)
        logging.getLogger("tkui.labfluence_tkroot").setLevel(logging.DEBUG)
        logging.getLogger("tkui.mainframe").setLevel(logging.DEBUG)
        logging.getLogger(__name__).setLevel(logging.DEBUG)
        logger.debug("Loggers setting to debug level...")

        pathscheme = argsns.pathscheme or 'test1'

        print "Enabling testing environment...:"
        confighandler = FakeConfighandler(pathscheme=pathscheme)
        # set basedir for exp:
        confighandler.ConfigPaths['exp'] = os.path.join('tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup', '.labfluence.yml')
        server = FakeConfluenceServer(confighandler=confighandler)

    else:
        pathscheme = argsns.pathscheme or 'default1'
        confighandler = ExpConfigHandler(pathscheme='default1')
        try:
            server = ConfluenceXmlRpcServer(autologin=True, confighandler=confighandler)
        except socket.error:
            print "This should not happen; autologin is shielded by try-clause."
            server = None
    confighandler.Singletons['server'] = server
    manager = ExperimentManager(confighandler=confighandler, autoinit=('localexps', ))
    confighandler.Singletons['experimentmanager'] = manager



    app = LabfluenceApp(confighandler=confighandler)

    # How to maximize / set window size:
    # http://stackoverflow.com/questions/15981000/tkinter-python-maximize-window
    # You can use tkroot.(wm_)state('zoomed') on windows to maximize. Does not work on unix.
    # You can bind tkroot.bind("<Configure>", method_handle)
    # This will invoke method_handle with event with attributes including width, height.

    #confighandler = app.Confighandler
    em = confighandler.Singletons.get('experimentmanager', None)
    if em:
        print "\nem.ActiveExperiments:"
        print em.ActiveExperiments
        print "\nem.RecentExperiments:"
        print em.RecentExperiments
#    exps self.Confighandler.get('app_recent_experiments')
    print "\nRecent experiments:"
    print "\n".join( "-> {}".format(e) for e in app.RecentExperiments )
    print "\nActive experiments:"
    print "\n".join( "-> {}".format(e) for e in app.ActiveExperiments )

    exps = app.ActiveExperiments
    print "\n\nGUI init (almost) finished..."
    if exps:
        print "\n\nShowing exps: {}".format(exps[0])
        notebook, expid, experiment = app.show_notebook(exps[0])
        #notebook.tab(1, state="enabled")
        #notebook.select(2)
    else:
        print "\n\nNo active experiments? -- {}".format(exps)

    app.start()
    # uh... after initiating start_loop, it will not go further until tkroot is destroyed.


"""


REFS:
* http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/index.html
* http://effbot.org/tkinterbook (maybe a bit old...)


Other Confluence interface implementations:
* https://github.com/RaymiiOrg/confluence-python-cli/blob/master/confluence.py

"""
