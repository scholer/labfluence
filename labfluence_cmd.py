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
# pylint: disable-msg=W0621

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
#from model.experimentmanager import ExperimentManager
#from model.experiment import Experiment
from model.server import ConfluenceXmlRpcServer
from model.page import WikiPage

from model.utils import attachmentTupFromFilepath

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



##################################################################
## Functions that simply use the args namespace from argparse:  ##
##################################################################


def getpagestruct(args):
    """
    Returns a page struct obtained using pageId <pageId>.
    """
    ret = list()
    for pageId in args.pageid:
        page = getPage(pageId)
        print page.Struct
        ret.append(page.Struct)
    return ret

def getpagexhtml(args):
    """
    Returns xhtml content of a page obtained using pageId <pageId>.
    """
    ret = list()
    for pageId in args.pageid:
        page = getPage(pageId)
        if page.Struct:
            xhtml = page.Struct.get('content')
            logger.debug("Page with pageId '%s' obtained, returning xhtml of length: %s", pageId, len(xhtml) if xhtml else '<none>')
            print xhtml
            ret.append(xhtml)
        else:
            logger.info("getPage(%s) returned page with no struct. Page is: %s", pageId, page)
    return ret


def getserverinfo(_=None):
    """
    Queries the server instance for server info and returns as struct.
    """
    server = confighandler.Singletons['server']
    info = server.getServerInfo()
    print info
    return info

#def addAttachment(pageId, fp):
#    attachmentInfo, attachmentData = attachmentTupFromFilepath(fp)
#    page = getPage(pageId)
#    att_info = page.addAttachment(attachmentInfo, attachmentData)
#    return att_info

def addattachment(args):
    """
    Adds attachments to a page.
    args should be a namespace object created by argparse.
    Should have attributes 'pageid' and 'files'.
    """
    logger.info("Pageid is: %s (type: %s), files are: %s",
                args.pageid, type(args.pageid), args.files)
    page = getPage(str(args.pageid))
    # NOTE: If pageid is int, some methods may work, while others will fail...
    attinfos = list()
    for fp in args.files:
        attachmentInfo, attachmentData = attachmentTupFromFilepath(fp)
        att_info = page.addAttachment(attachmentInfo, attachmentData)
        attinfos.append(att_info)
    print "Attachments added:\n- "
    print "\n- ".join(str(info) for info in attinfos)
    return attinfos




if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Labfluence command line interface.")


    # Creating sub-parsers for each command:
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='sub-command help')

    ######################################
    ### Simple command line functions ####
    ######################################

    # getpagestruct command:
    subparser = subparsers.add_parser('getpagestruct', help='Retrieve one or more page structs from the server.')
    subparser.set_defaults(func=getpagestruct)
    subparser.add_argument('pageid', metavar="<PageId>", type=int, nargs='+', help='PageId(s) of the pages to obtain.')

    # getpagestruct command:
    subparser = subparsers.add_parser('getpagexhtml', help='Retrieve xhtml for one or more pages from the server.')
    subparser.set_defaults(func=getpagexhtml)
    subparser.add_argument('pageid', metavar="<PageId>", type=int, nargs='+', help='PageId(s) of the pages to obtain.' )

    # getpagestruct command:
    subparser = subparsers.add_parser('getserverinfo', help='Retrieve server info from the server.')
    subparser.set_defaults(func=getserverinfo)


    ########################################
    ### Advanced command line functions ####
    ########################################

    # addattachments command:
    addattachmentsparser = subparsers.add_parser('addattachments',
                                                 help='Add one or more attachments to a page. \
Use "addattachments --help" to see help information for this command.')
    addattachmentsparser.add_argument('pageid', type=int,
                                      help='PageId of the page that you want to add the attachment to.')
    addattachmentsparser.add_argument('files', nargs='+',
                                      help='Paths for the files to upload.')
    addattachmentsparser.set_defaults(func=addattachment)



    ##################################
    ### Other command line options ###
    ##################################

    parser.add_argument('--testing', action='store_true', help="Start labfluence in testing environment.")
    parser.add_argument('--logtofile', action='store_true', help="Log logging outputs to files.")
    parser.add_argument('--loglevel', default=logging.INFO,
                        help="Logging level to use. Higher log levels results in less output. \
                             Can be specified either as string (debug, info, warning, error), \
                             or as an integer (10, 20, 30, 40). \
                             Loglevel defaults to logging.INFO (= 20), unless \
                             --debug is set, the log level will be min(logging.DEBUG, argsns.loglevel).")
    parser.add_argument('--debug', metavar='<MODULES>', nargs='*', # default defaults to None.
                        help="Specify modules where you want to display logging.DEBUG messages.\
                             Note that modules specified after --debug are not affected by the --loglevel \
                             argument, but always defaults to logging.DEBUG.")
    parser.add_argument('--pathscheme', help="Specify a particular pathscheme to use for the confighandler.")




    ##############################
    ###### Parse arguments: ######
    ##############################

    argsns = parser.parse_args() # produces a namespace, not a dict.



    ############################
    #### Set up logging:    ####
    ############################
    logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    try:
        loglevel = int(argsns.loglevel)
    except ValueError:
        loglevel = argsns.loglevel.upper()
    #logfmt = "%(levelname)s:%(name)s: %(funcName)s() :: %(message)s"
    if argsns.debug is None:
        #and 'all' in argsns.debug:
        logging.basicConfig(level=loglevel, format=logfmt)
    # argsns.debug is a list (possibly empty)
    elif argsns.debug:
    # argsns.debug is a non-empty list
        logging.basicConfig(level=loglevel, format=logfmt)
        for mod in argsns.debug:
            logger.info("Enabling logging debug messages for module: %s", mod)
            logging.getLogger(mod).setLevel(logging.DEBUG)
    else:
        # argsns.debug is an empty list
        logging.basicConfig(level=min(logging.DEBUG, loglevel), format=logfmt)
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


    ####################################################################################
    # Set up confighandler, etc (depending on whether testing mode is requested...) ####
    ####################################################################################
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
        confighandler = ExpConfigHandler(pathscheme=pathscheme)
        try:
            server = ConfluenceXmlRpcServer(autologin=True, confighandler=confighandler)
        except socket.error:
            print "This should not happen; autologin is shielded by try-clause. Perhaps network issues?"
            exit(1)

    confighandler.Singletons['server'] = server


    # Test if default func is defined after parsing:
    func = getattr(argsns, 'func', None)
    if func:
        logger.debug("Executing function %s with argsns %s", func, argsns)
        ret = func(argsns)
    else:
        logger.error("No func specified...?")
