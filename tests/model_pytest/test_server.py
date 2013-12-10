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
"""

Most of this is done using the fake-server.

Actually, I should create a fake xmlrpc API, which responds
exactly the same as the normal xmlrpclib does.
This could then be used to test the server implementation.
And, it would be rather easy, since I could use the existing
FakeConfluenceServer and just have a light-weight
fakexmlrpclib which acts as a proxy, routing all calls to
FakeConfluenceServer.


"""


import pytest


import logging
logger = logging.getLogger(__name__)
# Note: Switched to using pytest-capturelog, captures logging messages automatically...


#########################
### System Under Test ###
#########################
#import model.server
from model.server import ConfluenceXmlRpcServer


#####################
## Test doubles:   ##
#####################
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_xmlrpclib import FakeXmlRpcServerProxy
#from model.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer


@pytest.fixture
def server_fake_ch_and_proxy(monkeypatch):
    """
    Creates a testable server object that uses:
    - Fake ServerProxy from xmlrpclib
    - Fake confighandler.
    """
    ch = FakeConfighandler()
    ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
    #monkeypatch.setattr(model.server, 'login_prompt', lambda **x: ('fakeusername', 'fakepassword'))
    server = ConfluenceXmlRpcServer(autologin=False, confighandler=ch)
    def prompt_mock(**kwargs):
        logger.info("Call to promptForUserPass with kwargs %s intercepted by monkeypatched attribute, returning 'fakeuser', 'fakepassword'", kwargs)
        return 'fakeuser', 'fakepassword'
    monkeypatch.setattr(server, 'promptForUserPass', prompt_mock)
    fake_proxy = FakeXmlRpcServerProxy('https://some.url')
    monkeypatch.setattr(server, 'RpcServer', fake_proxy)
    #monkeypatch.setattr(server, 'Logintoken', lambda x: 'avalidtoken23456')
    return server


def test_promptForUserPass(server_fake_ch_and_proxy):
    s = server_fake_ch_and_proxy
    username, password = s.promptForUserPass()
    assert (username, password) == ('fakeuser', 'fakepassword')



def test_login(server_fake_ch_and_proxy):
    s = server_fake_ch_and_proxy
    assert s.login() is None
    assert s.login(prompt=True) == 'very_random_token'


def test_autologin(server_fake_ch_and_proxy):
    s = server_fake_ch_and_proxy
    token = s.autologin()
    assert token == 'very_random_token'
    #assert s.autologin(prompt=True) == 'very_random_token'

def test_getSpaces(server_fake_ch_and_proxy):
    s = server_fake_ch_and_proxy
    s._autologin = True
    spaces = s.getSpaces()
    print spaces
    assert {space['key'] for space in spaces} ==  {'ds', '~scholer', 'TSP'}

def test_fixture(server_fake_ch_and_proxy):
    s = server_fake_ch_and_proxy
    assert s._connectionok is None
    assert s.login() == None
    s._autologin = True # autologin must be set, otherwise the server will refuse to login automatically.
    serverinfo = s.getServerInfo()
    assert 'majorVersion' in serverinfo







@pytest.mark.skipif(True, reason="Not ready yet")
def test_loginAndSetToken(ch=None, persist=False):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1')
    ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
#        ch.setkey('wiki_password', 'http://10.14.40.245:8090/rpc/xmlrpc')
    print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
    server = ConfluenceXmlRpcServer(confighandler=ch, autologin=False)
    token = server.Logintoken
    print "\ntoken (before forced login):\t{}".format(token)
    token = server.login(dopersist=persist, prompt=True)
    print "token (after login):\t\t{}".format(token)
    if token:
        token_crypt, crypt_iv, crypt_key = server.saveToken(token, persist=persist)
        print "token_crypt, iv, key:\t{}".format((token_crypt, crypt_iv, crypt_key))
        token_decrypt = server.getToken(token_crypt)
        print "token_decrypt:\t\t\t{}".format(token_decrypt)

@pytest.mark.skipif(True, reason="Not ready yet")
def test_loadToken(ch=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1')
    ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
    print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
    # Deactivating autologin...
    server = ConfluenceXmlRpcServer(confighandler=ch, autologin=False)
    token = server.find_and_test_tokens()
    print "\nFound token: {}".format(token)
    print "server.Logintoken: {}".format(token)
    return server


@pytest.mark.skipif(True, reason="Not ready yet")
def test_getServerInfo(ch=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1')
    ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
    print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
    # Deactivating autologin...
    server = ConfluenceXmlRpcServer(confighandler=ch, autologin=False)
    token = server.find_and_test_tokens()
    print "\nFound token: {}".format(token)
    print "server.Logintoken: {}".format(token)
    if token is None:
        token = server.login(prompt=True)
    ret = server._testConnection()
    print "\n_testConnection returned:\n{}".format(ret)
    serverinfo = server.getServerInfo()
    print "\nServer info:"
    print serverinfo


@pytest.mark.skipif(True, reason="Not ready yet")
def test_getPageById(ch=None, server=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1')
    if server is None:
        server = ConfluenceXmlRpcServer(confighandler=ch)
    spaceKey = "~scholer"
    pageId = 524310
    pageId_erroneous = '504310'
    page_struct1 = server.getPage(pageId=pageId)
    print "\npage_struct1:"
    print page_struct1
    try:
        page_struct_err = server.getPage(pageId=pageId_erroneous)
        print "\npage_struct_err:"
        print page_struct_err
    except xmlrpclib.Fault as e:
        print "Retrival of on-existing pages by id raises error as expected."

@pytest.mark.skipif(True, reason="Not ready yet")
def test_getPageByName(ch=None, server=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1')
    if server is None:
        server = ConfluenceXmlRpcServer(confighandler=ch)
    spaceKey = "~scholer"
    title = "RS001 First test page CzkTW"
    title_err = "RS001 First test page CzTW"
    page_struct1 = server.getPage(spaceKey=spaceKey, pageTitle=title)
    print "\npage_struct1:"
    print page_struct1
    try:
        page_struct_err = server.getPage(spaceKey=spaceKey, pageTitle=title_err)
        print "\npage_struct_err:"
        print page_struct_err
    except xmlrpclib.Fault as e:
        print "Retrival of on-existing pages by id raises error as expected."


@pytest.mark.skipif(True, reason="Not ready yet")
def test_movePage1(ch=None, server=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1')
    if server is None:
        server = ConfluenceXmlRpcServer(confighandler=ch)
    spaceKey = "~scholer"
    title = "RS001 First test page CzkTW"
    page = server.getPage(spaceKey=spaceKey, pageTitle=title)
    pageId = page['id']
    #pageId = 524310  # edit, testing getPage as well...
    rootPageTitle = "RS Experiments"
    rootPage = server.getPage(spaceKey=spaceKey, pageTitle=rootPageTitle)
    print "\nrootPage:"
    print rootPage
    targetPageId = rootPage['id'] # Remember, 'id' and not 'pageId' !
    server.movePage(pageId, targetPageId=targetPageId)




#test_login() # currently does not work; the server needs a confighandler.
##server = test_config1()
#test_getServerInfo()
#test_loginAndSetToken(persist=True)
#test_loadToken()
#test_movePage1()
#test_getPageById()
#test_getPageByName()
