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

import logging
logger = logging.getLogger(__name__)


from abstract_rest_client import AbstractRestClient



class ConfluenceRestClient(AbstractRestClient):
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

