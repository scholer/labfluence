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
# pylint: disable-msg=C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221,E1101,W0402,E0202,W0201
# pylint: disable-msg=C0111,W0613
"""
Test module for fake server.
"""


## Test doubles:
# from tests.model_testdoubles.fake_confighandler import FakeConfighandler
from tests.model_testdoubles.fake_server import FakeConfluenceServer


#import os
import copy
#from datetime import datetime
import logging
logger = logging.getLogger(__name__)
logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():: %(message)s\n"
logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)
logging.getLogger("tests.model_testdoubles.fake_server").setLevel(logging.DEBUG)



def test_fakeserver_basics():
    s = FakeConfluenceServer()
    assert isinstance(s.getServerInfo(), dict)
    assert isinstance( s.getSpaces(), list )
    assert isinstance( s.getPages('~scholer'), list )


def test_fakeserver_getpage():
    s = FakeConfluenceServer()
    pid = '524296'
    p = s.getPage(pid)
    assert p['id'] == pid
    assert p['content'] == ''
    assert p['creator'] == 'scholer'

    p2 = s.getPage(pageTitle="2013_Aarhus", spaceKey="~scholer")
    assert p2['id'] == '524308'
    assert p2['creator'] == 'admin'


def test_fakeserver_removepage():
    """
    This is not yet complete, I need to define what happens when removing a non-existing page...
    """
    s = FakeConfluenceServer()
    pid = '524296'
    p = s.getPage(pid)
    assert p['id'] == pid
    #assert s.removePage(pid) == None
    assert s.removePage(pid) == True
    assert s.getPage(pid) == None
    assert s.removePage(pid) == False

def test_fakeserver_getAttachments():
    s = FakeConfluenceServer()
    pid = '917518'
    attachments = s.getAttachments(pid)
    assert isinstance(attachments , list )
    assert len(attachments) > 0
    assert 'fileSize' in attachments[0]

def test_fakeserver_getComments():
    s = FakeConfluenceServer()
    pid = '917518'
    comments = s.getComments(pid)
    assert isinstance(comments , list )
    assert len(comments) > 0
    assert 'id' in comments[0]

def test_fakeserver_getAttachment():
    s = FakeConfluenceServer()
    #aid = '1081345'
    pid = '917518'
    fileName = '2013-11-15 12.00.32_2.jpg'
    attachment = s.getAttachment(pid, fileName)
    assert isinstance(attachment , dict )
    assert len(attachment) > 0
    assert 'fileSize' in attachment

def test_fakeserver_getComment():
    s = FakeConfluenceServer()
    aid = '917540'
    comment = s.getComment(aid)
    assert isinstance(comment , dict )
    assert len(comment) > 0
    assert 'id' in comment

def test_fakeserver_removeComment():
    s = FakeConfluenceServer()
    aid = '917540'
    comment = s.getComment(aid)
    assert isinstance(comment , dict )
    assert s.removeComment(aid) == True
    assert s.getComment(aid) == None
    assert s.removeComment(aid) == False

def test_fakeserver_editComment():
    s = FakeConfluenceServer()
    aid = '917540'
    comment = s.getComment(aid)
    assert isinstance(comment , dict )
    c2 = copy.deepcopy(comment)
    new_comment = dict(c2, content= "Edited content moy bueno.")
    updated = s.editComment(new_comment)
    assert updated['content'] == "Edited content moy bueno."
    assert updated['id'] == '917540'
    assert updated['creator'] == 'scholer'


def test_fakeserver_storePage():
    s = FakeConfluenceServer()
    # Updating an existing page:
    pid = '524296'
    p1 = s.getPage(pid)
    p1_org = copy.deepcopy(p1)
    p2 = copy.deepcopy(p1)
    assert p2['id'] == pid
    p2['content'] = "New content"
    p3 = s.storePage(p2)
    assert p3['content'] == "New content"
    assert p3['creator'] == p1_org['creator']
    assert p3['modifier'] == s.Username
    assert int(p3['version']) == int(p1_org['version']) + 1

    ## Adding a new page:
    new_page = dict(content="new page content", space="~scholer", title="New testing page")
    ret_page = s.storePage(new_page)
    assert ret_page['content'] == "new page content"
    assert ret_page['creator'] == s.Username
    assert ret_page['modifier'] == s.Username
    assert ret_page['version'] == str(1)

    ## TODO: Add test that attempting to store page with existing space:title will fail.
    ## TODO: Add test for version match raises error if not matching that of existing page.
    ## TODO: Add test that specifying a pageid that does not exist raises error.



def test_fakeserver_updatePage():
    s = FakeConfluenceServer()
    # Updating an existing page:
    pid = '524296'
    p1 = s.getPage(pid)
    p1_org = copy.deepcopy(p1)
    p2 = copy.deepcopy(p1)
    assert p2['id'] == pid
    p2['content'] = "New content"
    p3 = s.storePage(p2)
    assert p3['content'] == "New content"
    assert p3['modifier'] == s.Username
    assert int(p3['version']) == int(p1_org['version']) + 1
