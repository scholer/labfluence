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



import logging
logger = logging.getLogger(__name__)
logging.getLogger(__name__).setLevel(logging.DEBUG)
logging.getLogger("__main__").setLevel(logging.DEBUG)


from model.server import ConfluenceXmlRpcServer
logging.getLogger("model.server").setLevel(logging.DEBUG)


## Test doubles:
from tests.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
#from tests.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer







def test1():
    logger.info("\n>>>>>>>>>>>>>> test_getLocalFilelist() started >>>>>>>>>>>>>")
    username = 'scholer'
    username, password = login_prompt()
    url = 'http://10.14.40.245:8090/rpc/xmlrpc'
    server = ConfluenceXmlRpcServer(url=url, username=username, password=password)


def test_login():
    username = 'scholer'
    url = 'http://10.14.40.245:8090/rpc/xmlrpc'
    server = ConfluenceXmlRpcServer(url=url, username=username)


def test_config1():
    paths = [ os.path.join(os.path.dirname(os.path.abspath(__file__)), '../test/config', cfg) for cfg in ('system_config.yml', 'user_config.yml', 'exp_config.yml') ]
    ch = ExpConfigHandler(*paths, VERBOSE=5)
    ch.setdefault('user', 'scholer') # set defaults only sets if not already set.
    #ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc') # setkey overrides.
    print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
    server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)
    if server.test_token():
        print "Succesfully connected to server (retrieved serverinfo)!"
    else:
        print "Failed to obtain valid token from server !!"

def test2():
    confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
    print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
    server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)

def test_loginAndSetToken(ch=None, persist=False):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
#        ch.setkey('wiki_password', 'http://10.14.40.245:8090/rpc/xmlrpc')
    print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
    server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5, autologin=False)
    token = server.Logintoken
    print "\ntoken (before forced login):\t{}".format(token)
    token = server.login(dopersist=persist, prompt=True)
    print "token (after login):\t\t{}".format(token)
    if token:
        token_crypt, crypt_iv, crypt_key = server.saveToken(token, persist=persist)
        print "token_crypt, iv, key:\t{}".format((token_crypt, crypt_iv, crypt_key))
        token_decrypt = server.getToken(token_crypt)
        print "token_decrypt:\t\t\t{}".format(token_decrypt)

def test_loadToken(ch=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
    print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
    # Deactivating autologin...
    server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5, autologin=False)
    token = server.find_and_test_tokens()
    print "\nFound token: {}".format(token)
    print "server.Logintoken: {}".format(token)
    return server


def test_getServerInfo(ch=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
    print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
    # Deactivating autologin...
    server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5, autologin=False)
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


def test_getPageById(ch=None, server=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    if server is None:
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)
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

def test_getPageByName(ch=None, server=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    if server is None:
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)
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


def test_movePage1(ch=None, server=None):
    if ch is None:
        ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    if server is None:
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)
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
