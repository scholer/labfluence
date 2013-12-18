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
Will contact the test server and retrieve and store the data for offline
usage by FakeConfluenceServer instances.

PageSummary datastructs are dicts, with:

Key         Type   Value
-----------------------------------------------------------------------
id          long   the id of the page
space       String the key of the space that this page belongs to
parentId    long   the id of the parent page
title       String the title of the page
url         String the url to view this page online
permissions int    the number of permissions on this page (deprecated: may be removed in a future version)

"""

# This script must be run as a module, invoked from the labfluence application's
# base folder, which contains the folders: "./model/" and "./test/".


from __future__ import print_function
import logging
logger = logging.getLogger(__name__)

import sys
import os
import yaml
import xmlrpclib


sys.path.insert(0, os.getcwd())
try:
    from model.server import ConfluenceXmlRpcServer
    from model.confighandler import ExpConfigHandler
except ImportError as e:
    print("\n\n\n\n\n>>>>> This module must be invoked from the labfluence root directory! <<<<<\n\n\n\n\n\n")
    print("os.getcwd(): %s", os.getcwd())
    print("sys.path: %s", sys.path)
    raise e
#from datetime import datetime


if __name__ == '__main__':

    outputfn = os.path.join(os.path.dirname(__file__), "fakeserver_testdata_large.yml")

    logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
    logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s(): %(message)s\n"
    logging.basicConfig(level=logging.INFO, format=logfmt)
    logging.getLogger("__main__").setLevel(logging.DEBUG)

    ch = ExpConfigHandler(pathscheme='test1')
    server = ConfluenceXmlRpcServer(confighandler=ch)

    ### IMPORT PAGES and attachment (info) ###
    pagesummaries = server.getPages('~scholer')
    pages, comments, attachments = dict(), dict(), dict()

    for i, summary in enumerate(pagesummaries):
        print("Retrieving page {} of {}".format(i, len(pagesummaries)))
        pid = summary['id']
        if pid in pages:
            logger.warning("Duplicate pageId! - This is already in the pages dict: '%s'", pid)
        p = server.getPage(pid)
        if p:
            for k, v in p.items():
                if isinstance(v, xmlrpclib.DateTime):
                    logger.debug("Converting page[%s] xmlrpclib.DateTime object '%s' to string.", k, v)
                    p[k] = repr(v.value)
                    #p[k] = datetime(v.timetuple()) # Use this to convert to datetime.datetime object instead...
            pages[pid] = p
            ## PAGE ATTACHMENTS:
            pageattachments = server.getAttachments(pid)
            if pageattachments:
                for i, info in enumerate(pageattachments):
                    for k, v in info.items():
                        if isinstance(v, xmlrpclib.DateTime):
                            logger.debug("pageattachment %s, Converting attinfo['%s'] xmlrpclib.DateTime object '%s' to string.", info['id'], k, v)
                            info[k] = repr(v.value)
                attachments[pid] = pageattachments
            ## PAGE COMMENTS:
            pagecomments = server.getComments(pid)
            if pagecomments:
                for i, info in enumerate(pagecomments):
                    for k, v in info.items():
                        if isinstance(v, xmlrpclib.DateTime):
                            logger.debug("pagecomment %s, Converting attinfo['%s'] xmlrpclib.DateTime object '%s' to string.", info['id'], k, v)
                            info[k] = repr(v.value)
                comments[pid] = pagecomments
        else:
            logger.warning("could not retrieve page with pageId '%s'. More info:\n-- %s", pid, summary)
    persistdata = dict(pages=pages, attachments=attachments, comments=comments)
    #print persistdata['pages']
    print(type(persistdata['pages']))

    print("\n".join( u"\nPage '{}' >> ".format(page['id'])+
                     u"; ".join(u"{}: {}".format(k,v) for k,v in page.items() if k != 'content')
                        for pid,page in persistdata['pages'].items() ))



    ### server info ###
    persistdata['serverinfo'] = serverinfo = server.getServerInfo()

    ### spaces ###
    persistdata['spaces'] = spaces = server.getSpaces()

    yaml.dump(persistdata, open(outputfn), 'wb')
