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
This module provides a command-line interface to various features, including:
* Fetching a page struct or page content (xhtml) from server.


"""

import os
import socket
import argparse
import logging
logging.addLevelName(4, 'SPAM')
logger = logging.getLogger(__name__)


### MODEL IMPORT ###
from model.confighandler import ExpConfigHandler
from model.experimentmanager import ExperimentManager
from model.experiment import Experiment
from model.server import ConfluenceXmlRpcServer
from model.page import WikiPage


### TEST DOUBLES IMPORT ###
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer


confighandler = None



def getPage(pageId):
    """
    Returns a WikiPage instance with <pageId>
    """
    if confighandler is None:
        logger.error("No confighandler defined, aborting...")
        return
    page = WikiPage(pageId, confighandler=confighandler)
    return page

def getPageStruct(pageId):
    """
    Returns a page struct obtained using pageId <pageId>.
    """
    page = getPage(pageId)
    return page.Struct

def getPageXhtml(pageId):
    """
    Returns xhtml content of a page obtained using pageId <pageId>.
    """
    page = getPage(pageId)
    if page.Struct:
        xhtml = page.Struct.get('content')
        logger.debug("Page with pageId '%s' obtained, returning xhtml of length: %s", pageId, len(xhtml) if xhtml else '<none>')
        return xhtml
    else:
        logger.info("getPage(%s) returned page with no struct. Page is: %s", pageId, page)



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Labfluence command line interface.")


    ######################################
    ### Simple command line functions ####
    ######################################

    parser.add_argument('--getpagestruct', metavar="<PageId>", type=int,
                        help="Retrieve a page (struct) from the wiki.")

    parser.add_argument('--getpagexhtml', metavar="<PageId>",
                        help="Retrieve a page (struct) from the wiki.")


    ##################################
    ### Other command line options ###
    ##################################

    parser.add_argument('--testing', action='store_true', help="Start labfluence in testing environment.")
    parser.add_argument('--logtofile', action='store_true', help="Log logging outputs to files.")
    parser.add_argument('--debug', metavar='<MODULES>', nargs='*', # default defaults to None.
                        help="Specify modules where you want to display logging.DEBUG messages.")
    parser.add_argument('--pathscheme', help="Specify a particulra pathscheme to use for the confighandler.")

    argsns = parser.parse_args() # produces a namespace, not a dict.



    # Set up logging:
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
            fh = logging.FileHandler('logs/labfluence_cmd_testing.log')
        else:
            fh = logging.FileHandler('logs/labfluence_cmd_debug.log')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logging.getLogger('').addHandler(fh)  #  logging.root == logging.getLogger('')


    # Set up confighandler, etc (depending on whether testing mode is requested...)
    if argsns.testing:
        logging.getLogger("model.model_testdoubles.fake_confighandler").setLevel(logging.DEBUG)
        logging.getLogger("model.model_testdoubles.fake_server").setLevel(logging.DEBUG)
        logging.getLogger(__name__).setLevel(logging.DEBUG)
        pathscheme = argsns.pathscheme or 'test1'
        logger.info( "Enabling testing environment...:" )
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
            print "This should not happen; autologin is shielded by try-clause. Perhaps network issues?"
            exit(1)
    confighandler.Singletons['server'] = server


    if argsns.getpagexhtml:
        pageid = str(argsns.getpagexhtml)
        assert pageid
        xhtmlcontent = getPageXhtml(pageid)
        print xhtmlcontent

    if argsns.getpagestruct:
        pageid = str(argsns.getpagexhtml)
        assert pageid
        pagestruct = getPageStruct(pageid)
        print pagestruct
