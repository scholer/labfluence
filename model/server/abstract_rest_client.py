#!/usr/bin/env python3
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
# pylint: disable=C0103,C0301,W0142,R0902,R0904,R0913,R0201,R0912
"""
Abstract REST client module. Provides Abstract REST client base classes.

Abstract clients serves two purposes:
1) Define a standard "client" interface, specifying what methods and
properties a server is expected to implement.
2) Define some of the basic client functionality which is common
to all implemented server proxies, e.g. properties, etc.

"""


from __future__ import print_function, division
import requests

import logging
logger = logging.getLogger(__name__)


from abstract_clients import AbstractClient


class RESTError(Exception):
    """Any error"""


class AbstractRestClient(AbstractClient):
    """

    Server interface to the REST API of a MediaWiki instance.
    Introduced summer 2014.

    Many parts of this is inspired/derived/taken from the projects:
    * legoktm/supersimplemediawiki  (copyright Kunal Mehta)
    * goldsmith/Wikipedia  (copyright Jonathan Goldsmith)

    """
    def __init__(self, serverparams=None, username=None, password=None, logintoken=None,
                 confighandler=None, autologin=True):
        """
        Use serverparams dict to specify API parameters, which may include entries:
        * appurl : <baseurl>:<urlpostfix>   - main API entry point
        * baseurl : <protocol>:<hostname>[:port]
        * urlpostfix : path to the API, e.g. '/rpc/xmlrpc'
        * hostname : e.g "localhost", "127.0.0.1" or wiki.cdna.au.dk
        * post : e.g. 80, 443, 8080, etc.
        * protocol : e.g. 'http', 'https'.
        * raisetimeouterrors : bool (whether to raise timeout errors during run).
        If e.g. appurl is not explicitly specified, it is generated from the noted sub-components.
        Note that some primitives (e.g. urlpostfix) will vary depending on the server
        implementation (XML-RPC vs REST). These defaults are usually specified in self._defaultparams.
        """

        logger.debug("New %s initializing...", self.__class__.__name__)
        super(AbstractRestClient, self).__init__(serverparams=serverparams, username=username,
                                                 password=password, logintoken=logintoken,
                                                 confighandler=confighandler, autologin=autologin)
        self._default_rest_params = {}  # TODO: Specify default REST parameters.
        self.Cookies = None
        self.Headers = None
        self.Session = None
        self._apiurl = None

    def setup_rest_api(self):
        """
        Performs common REST api setup.
        Call after setting self._defaultparams
        """
        s = self.Session = requests.Session()
        s.headers.update({'User-agent' : self.UserAgent})
        #self.Cookies = dict() # Session handles cookies.
        apiurl = self._apiurl = self.AppUrl # I cache this because I don't want to generate it with every call.
        if not apiurl:
            logger.warning("WARNING: Server's AppUrl is '%s', ABORTING init!", apiurl)
            return None
        logger.info("%s - Using REST API url: %s", self.__class__.__name__, apiurl)
        if self.AutologinEnabled:
            self.autologin()
        logger.debug("%s initialized.", self.__class__.__name__)

    def get(self, params=None, data=None, files=None):
        """
        Make a standard REST API HTTP GET request.
        """
        r = self.Session.get(self._apiurl, params=params, cookies=self.Cookies, headers=self.Headers, files=files, data=data)
        return self.process_request(r)

    def post(self, params=None, data=None, files=None):
        """
        Make a standard REST API HTTP POST request.
        """
        r = self.Session.post(self._apiurl, params=params, cookies=self.Cookies, headers=self.Headers, files=files, data=data)
        return self.process_request(r)

    def process_request(self, request):
        """
        Does brief processing of request, saving cookies and raising errors if needed.
        """
        if not request.ok:
            raise RESTError(request.text)
        #self.Cookies.update(request.cookies) # Session handles cookies.
        return request

