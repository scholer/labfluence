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
"""

Main labfluence module for starting labfluence with Tkinter GUI.

"""

from __future__ import print_function

# Other standard lib modules:
import socket
import argparse
import os

import logging
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)

try:
    import readline, rlcompleter
except ImportError:
    print("readline module not available...")
    readline = None

from __init__ import init_logging

### MODEL IMPORT ###
from model.confighandler import ExpConfigHandler
from model.experimentmanager import ExperimentManager
from model.server import ConfluenceXmlRpcServer

### TEST DOUBLES IMPORT ###
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer

### GUI IMPORTS ###
from tkui.labfluence_tkapp import LabfluenceApp





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




    ###########################
    #### ARG PARSING ##########
    ###########################

    parser = argparse.ArgumentParser(description="Labfluence - Experiment manager with Confluence connector.")
    parser.add_argument('--logtofile', help="Log logging outputs to this file.")
    parser.add_argument('--loglevel', default=logging.WARNING,
                        help="Logging level to use. Higher log levels results in less output. \
                             Can be specified either as string (debug, info, warning, error), \
                             or as an integer (10, 20, 30, 40). \
                             Loglevel defaults to logging.WARNING (30), unless \
                             --debug is set, in which case log level will be min(logging.DEBUG, argsns.loglevel).")
    parser.add_argument('--debug', metavar='<MODULES>', nargs='*', # default defaults to None.
                        help="Specify modules where you want to display logging.DEBUG messages.\
                             Note that modules specified after --debug are not affected by the --loglevel \
                             argument, but always defaults to logging.DEBUG.\
                             (technically, because the module's logger directs messages directly to the loghandlers\
                             and does not rely on propagation to the root logger...)\
                            Special: If no modules are specified, '--debug' will produce same effect as '--loglevel DEBUG'.")
    parser.add_argument('--pathscheme', help="Specify a particular pathscheme to use for the confighandler.\
                        Can be used to switch between different configs. In practice mostly used for development testing.")
    parser.add_argument('--testing', action='store_true', help="Start labfluence in testing environment. Will set pathscheme\
                        to default testing pathscheme and set loglevel of a range of loggers to DEBUG.")

    argsns = parser.parse_args() # produces a namespace, not a dict.


    #######################################
    ### Set up standard logging system ####
    #######################################
    loghandlers = init_logging(argsns, prefix="labfluence")


    ####################################################################################
    # Set up confighandler, etc (depending on whether testing mode is requested...) ####
    ####################################################################################
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
        logging.getLogger("model.server").setLevel(logging.DEBUG)
        logging.getLogger("model.model_testdoubles.fake_confighandler").setLevel(logging.DEBUG)
        logging.getLogger("model.model_testdoubles.fake_server").setLevel(logging.DEBUG)
        logging.getLogger("tkui.labfluence_tkapp").setLevel(logging.DEBUG)
        logging.getLogger("tkui.labfluence_tkroot").setLevel(logging.DEBUG)
        logging.getLogger("tkui.mainframe").setLevel(logging.DEBUG)
        logging.getLogger(__name__).setLevel(logging.DEBUG)
        logger.debug("Loggers setting to debug level...")

        pathscheme = argsns.pathscheme or 'test1'

        logger.info( "Enabling testing environment..." )
        confighandler = FakeConfighandler(pathscheme=pathscheme)
        # set basedir for exp:
        confighandler.ConfigPaths['exp'] = os.path.join('tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup', '.labfluence.yml')
        server = FakeConfluenceServer(confighandler=confighandler)

    else:
        logger.debug(" >>>>>> Initiating real confighandler and server... >>>>>>")
        pathscheme = argsns.pathscheme or 'default1'
        confighandler = ExpConfigHandler(pathscheme='default1')
        try:
            logger.debug("Confighandler instantiated, Initiating server... >>>>>>")
            # setting autologin=False during init should defer login attempt...
            server = ConfluenceXmlRpcServer(autologin=False, confighandler=confighandler)
            server._autologin = True
        except socket.error as e:
            logger.error( "Socket error during server init ('%s'). This should not happen; autologin is shielded by try-clause.", e)
            server = None

    confighandler.Singletons['server'] = server
    logger.debug(" >>>>>> Server instantiated, initiating ExperimentManager... >>>>>> ")
    manager = ExperimentManager(confighandler=confighandler, autoinit=('localexps', ))
    confighandler.Singletons['experimentmanager'] = manager
    logger.debug(" >>>>>> ExperimentManager instantiated, starting LabfluenceApp... >>>>>>")

    app = LabfluenceApp(confighandler=confighandler)
    logger.debug(" >>>>>> LabfluenceApp instantiated, connecting with server >>>>>>")
    server.autologin()


    # How to maximize / set window size:
    # http://stackoverflow.com/questions/15981000/tkinter-python-maximize-window
    # You can use tkroot.(wm_)state('zoomed') on windows to maximize. Does not work on unix.
    # You can bind tkroot.bind("<Configure>", method_handle)
    # This will invoke method_handle with event with attributes including width, height.

    #confighandler = app.Confighandler
    em = confighandler.Singletons.get('experimentmanager', None)
    if em:
        logger.info( "em.ActiveExperiments: %s", em.ActiveExperiments )
        logger.info( "em.RecentExperiments: %s", em.RecentExperiments )

    exps = app.ActiveExperiments
    logger.info("GUI init (almost) finished...")
    if exps:
        logger.info("Showing exp: %s", exps[0])
        notebook, expid, experiment = app.show_notebook(exps[0])
        #notebook.tab(1, state="enabled")
        #notebook.select(2)
    else:
        logger.info("No active experiments(?) - app.ActiveExperiments = %s", exps)

    if readline:
        readline.parse_and_bind("tab: complete")
    logger.debug("Invoking app.start()")
    print("Note: If starting in interactive mode (e.g. with python -i), please do not exit() until you have closed the tk application.")
    app.start()
    # After initiating start_loop, it will not go further until tkroot is destroyed.

    # If this script was invoked with python -i, then the interpreter will be available
    # for interactive inspection after the script has completed:
    print("Main application run complete!")


"""

For interactive mode, enable readline with:
    import readline, rlcompleter
    readline.parse_and_bind("tab: complete")

If this is run from e.g. inside a function, you may want to specify the namespace manually:
    ns = globals().update(locals())
    readline.set_completer(rlcompleter.Completer(ns).complete)


REFS:
* http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/index.html
* http://effbot.org/tkinterbook (maybe a bit old...)


Other Confluence interface implementations:
* https://github.com/RaymiiOrg/confluence-python-cli/blob/master/confluence.py



OLD OBSOLETE:


    # Examples of different log formats:
    #logfmt = "%(levelname)s: %(filename)s:%(lineno)s %(funcName)s() > %(message)s"
    logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    #logfmt = "%(levelname)s:%(name)s: %(funcName)s() :: %(message)s"
    if argsns.debug is None:
        #and 'all' in argsns.debug:
        logging.basicConfig(level=logging.INFO, format=logfmt)
    # argsns.debug is a list (possibly empty)
    elif argsns.debug:
    # argsns.debug is a non-empty list
        logging.basicConfig(level=logging.INFO, format=logfmt)
        for mod in argsns.debug:
            logger.info("Enabling logging debug messages for module: %s", mod)
            logging.getLogger(mod).setLevel(logging.DEBUG)
    else:
        # argsns.debug is an empty list
        logging.basicConfig(level=logging.DEBUG, format=logfmt)
    logging.getLogger("__main__").setLevel(logging.DEBUG)

    if argsns.logtofile or True: # always log for now...
        # based on http://docs.python.org/2/howto/logging-cookbook.html
        if not os.path.exists('logs'):
            os.mkdir('logs')
        if argsns.testing:
            fh = logging.FileHandler('logs/labfluence_testing.log')
        else:
            fh = logging.FileHandler('logs/labfluence_debug.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)s - %(funcName)s() - %(message)s')
        fh.setFormatter(formatter)
        #  logging.root == logging.getLogger('')
        logging.getLogger('').addHandler(fh)


"""
