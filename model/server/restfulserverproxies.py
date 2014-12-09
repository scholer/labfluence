#!/usr/bin/env python3
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
# pylint: disable-msg=C0103,C0301,R0201,R0904,W0142
"""

XmlRpc serverproxy module.

Provides classes to access e.g. a Confluence server through xmlrpc.

Implements XML-RPC based ServerProxies from AbstractServerProxy base class.

Currently the only supported XML-RPC server API is the Confluence XML-RPC API,
which is now deprecated.

Since the focus for most wiki instances seems to be to support RESTful
APIs, this module will probably not receive much care in the future.
Consider that an eary deprecation warning.

Some parts of this is inspired/derived/taken from the projects:
    * legoktm/supersimplemediawiki  (copyright Kunal Mehta)
    * goldsmith/Wikipedia  (copyright Jonathan Goldsmith)
    * Riamse/ceterach (copyright Andrew Wang <andrewwang43@gmail.com>)
All of this has been released to the public domain.


"""

from __future__ import print_function, division
import requests

import logging
logger = logging.getLogger(__name__)

# Labfluence modules and classes:

# Decorators:

defaultsockettimeout = 3.0

from abstractserverproxy import AbstractServerProxy


class RESTError(Exception):
    """Any error"""


class RestfulServerProxy(AbstractServerProxy):
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
        super(RestfulServerProxy, self).__init__(serverparams=serverparams, username=username,
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




class RestfulConfluenceServerProxy(RestfulServerProxy):
    """

    Server interface to the REST API of a Confluence instance.
    Introduced summer 2014.

    These methods are part of the standard 'labfluence server' API,
    defined by AbstractServerProxy (asterix marks platform-dependent methods):
    - login
    - logout
    - getServerInfo
    - getSpaces (if applicable)
    - getUser
    - createUser
    - getGroups*
    - getGroup*
    - getPages
    - getPage
    - movePage
    - removePage
    - getChildren*
    - getDescendents*
    - getComments*
    - getComment*
    - addComment*
    - editComment*
    - removeComment*
    - getPageAttachments
    - getAttachment
    - getAttachmentData
    - addAttachment
    - moveAttachment
    - removeAttachment
    - storePage (or should I have add/save/updatePage methods?)
    - addPage
    - savePage
    - updatePage

    Addotionally, RESTful serverproxies should provide generic query methods
    to the REST API. (This will usually be the case anyways...)

    One thing I might consider: Implement REST API via an extremely SIMPLE
    ServerProxy which SIMULATES the XML-RPC format.
    Then consume this through ConfluenceXmlRpcServerProxy,
    specifying self.RpcServer as this simulating server.
    Then I would't have to change a thing in the rest of the
    labfluence code, it would "just work".
    On the other hand: Since logging in and error/exception handling
    is so different - and since that is mostly what this feature would
    utilize, this is probably a poor strategy.
    It is probably better to implement the REST api from scratch,
    keeping things as simple as possible.
    Methods could take a
       dataformat="confluencexmlrpc"
    parameter, which would ensure that the returned data format is compatible
    with the data returned by Confluence's old xml-rpc api.

    """
    pass


class RestfulMediawikiServerProxy(RestfulServerProxy):
    """

    Server interface to the REST API of a MediaWiki instance.
    Introduced summer 2014.


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
        super(RestfulMediawikiServerProxy, self).__init__(serverparams=serverparams, username=username,
                                                          password=password, logintoken=logintoken,
                                                          confighandler=confighandler, autologin=autologin)
        self._defaultparams = dict(port='80', urlpostfix='/w/api.php', protocol='http')
        self.setup_rest_api()

"""

=== MediaWiki API libs: ===

In general, the libs that uses requests module tends to be simple, while those using urllib/urllib2 has a lot of extra "parsing".
Mediawiki evaluation also generally suggests using requests module over urllib2 plus self-made functions.

I suggest the following:
1) Make a generic "RestfulServerProxy" class using code from the requests-based projects (Wikipedia, ceterach, supersimplemediawiki).
    * It would be nice if this could derive/subclass from the main AbstractServerProxy class....
2) From this, derive your MediaWikiRestServerProxy and ConfluenceRestServerProxy classes
    * These (and preferably only these) will then import the correct abstraction classes for pages, etc.

Using the requests module:
 * http://docs.python-requests.org/en/latest/user/advanced/
 * https://github.com/kennethreitz/requests/
 * Using requests.session()  - or requests.Session() ?
    * Yes, definitely use a session object. requests.session() function simply returns a requests.Session object with no parameters.

Regarding AUTH:
 * http://docs.python-requests.org/en/latest/user/authentication/
 * See https://github.com/Riamse/ceterach/blob/master/ceterach/api.py
 * https://github.com/yuvipanda/python-mwapi/blob/master/mwapi/__init__.py


Things to keep in mind when implementing:
 * Client should provide a descriptive User Agent header, e.g. User-Agent: Username/email/framework
 * Make gzip available (should be automatically handled with requests module)
 * Remember the "continue" parameter,https://www.mediawiki.org/wiki/API:Query#Continuing_queries
 * Also, since MediaWiki does not handle "child pages" page structure very well, you should enable the following feature:
    * When a new experiment page is created, add a link to the new page on a dedicated "Experiment summary page".
    * I suggest simply having a new settings variable, "exp_new_add_pagelink_to_summarypage" : None or a pageId number.
    * If this is set (and not None), add a link at the bottom of that page. (or, use a user-defined regex to determine where...)


Main MediaWiki API page:https://www.mediawiki.org/wiki/API:Main_page
MediaWiki REST API reference:https://en.wikipedia.org/w/api.php (yes, this is also the API's main entry point)
MediaWiki API data formats:https://www.mediawiki.org/wiki/API:Data_formats  (not very informative)
MediaWiki API tutorial:https://www.mediawiki.org/wiki/API:Tutorial

A note regarding attachments: I think in mediawiki, "images" may both refer to actual images as well as "page attachments" (attached files) in a broad, general sense.

Fromhttp://www.mediawiki.org/wiki/API:Client_code#Python ::
 * Pywikibot - A collection of python scripts. Seems up to date (Nov 2013) (IRC)(Evaluation)
    * MIT license, Very, very large collection of maintenance tools, provides an autonomous bot system.
    * Uses urllib, NOT requests
    * Last commit 1 day ago. High commit frequency.
 * mwclient - A Python library that makes most of the API functions accessible. (PyPI)(Evaluation)
    * Uses urllib, urllib2, urlparse, httplib, NOT requests
    * Implements a lot of low level classes it self, something that I would think is better suited for a dedicated module (like requests)
    * Use of requests module is allegedly "in progress" c.f. wikipedia, but no sign thereof.
    * Last commit less than a month ago. High commit frequency.
 * wikitools - Provides several layers of abstraction around the API. Should be up to date (PyPI) (Evaluation)
    * GPL
    * Uses urllib2, NOT requests
    * Has abstractions in the form of wiki, page, panelist, user, wikifile, category classes in addition to the basic api module.
    * Last commit less than a month ago. Medium commit frequency.
 * simplemediawiki - A simple, no-abstraction interface to the API. Handles cookies and other extremely basic things. Python 2.6+ and 3.3+ compatible. Docs at http://pythonhosted.org/simplemediawiki/ .(PyPI) (Evaluation)
    * GPL, by RedHat, uses urllib, urllib2, cookielib, but NOT REQUESTS.
    * Handles gzip. No abstractions
    * Last commit a couple of months ago, then 1 year ago. Medium-low commit rate.
 * Wikipedia - A Python library that makes it easy to access and parse data from Wikipedia. (PyPI)
    * Uses requests module
    * Mostly intended for wikipedia.org
    * Does provide some abstraction classes and has a decent amount of examples.
    * Last commit less than a month ago. Medium-high commit frequency.
 * python-mwapi - A simple wrapper around the Mediawiki API, meant to closely mirror its interface (PyPI)
    * Uses requests module, with requests.session()
    * MIT license
    * Also very simple, too simple. No abstractions.
    * Last updated 2 years ago. Very low commit rate.
 * supersimplemediawiki - Similar to simplemediawiki, but does not handle tokens or compression.
    * Uses requests module (without requests.session() )
    * MIT license
    * Very, very simple, no mediawiki api specific stuff or abstractions, just a wrapper for the requests lib, making login, cookies, and new requests more manageable.
    * Last updated 9 months ago. Very low commit frequency.
    * However, this is still a good example of how to consume a REST API from python using the requests module.
    * Good example: https://github.com/legoktm/supersimplemediawiki/blob/master/has_new_messages.py
 * Pattern, [1] - web mining module, has classes for handling MediaWiki API requests, handles continuations
    * Huge project, Very excessive, and a lot bad code.
 * ceterach - Python3 library, fully PEP8 compliant.
    * Uses requests lib with requests.session()  (also urllib.parse.urlparse, but as utility only).
    * Has abstractions in the form of Category, Page, File, User, etc classes.
    * Main MediaWiki class has some okay examples of how to use the mediawiki API with the requests module.
    * Last commit less than a month ago, medium commit frequency.

Other page regarding MediaWiki API client libs:
Frances Hocutt's project page: https://www.mediawiki.org/wiki/Evaluating_and_Improving_MediaWiki_web_API_client_libraries



"""




if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
