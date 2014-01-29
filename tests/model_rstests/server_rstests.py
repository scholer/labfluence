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
# pylint: disable-msg=C0111,C0112,W0212,W0621


import os
import getpass
import sys
import base64
import xmlrpclib
import logging
logger = logging.getLogger(__name__)

sys.path.insert(0, os.getcwd())

from model.utils import getmimetype
from model.simpleserver import SimpleConfluenceXmlRpcServer



def rstest_addAttachment():
    pw = getpass.getpass()
    user = 'scholer'
    url = 'http://10.14.40.245:8090/rpc/xmlrpc'
    server = SimpleConfluenceXmlRpcServer(url, user, pw)
    pageid = '917542'


    fp = 'tests/test_data/attachments/visualization.pdf'
    filename = os.path.basename(fp)
    mimetype = getmimetype(fp)
    # Note: comment not required, I believe.
    attInfo = dict(fileName=filename, contentType=mimetype)
    with open(fp, 'rb') as fd:
        #attData = base64.b64encode(fd.read('rb'))
        # xmlrpclib.Binary also does base64.encode, but adds xml tag before and after.
        attData = xmlrpclib.Binary(fd.read())
    logger.debug("Adding attachment '%s' with base64 encoded attData of length %s to page with id '%s'", attInfo, len(str(attData)), pageid)
    server.addAttachment(pageid, attInfo, attData)


if __name__ == '__main__':
    logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel, format=logfmt)

    rstest_addAttachment()
