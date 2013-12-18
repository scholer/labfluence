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
# pylint: disable-msg=W0621,C0111
"""
Tests for the labfluence_cmd.py command line interface module.

"""

import pytest
import os
import tempfile
import logging
logger = logging.getLogger(__name__)

import labfluence_cmd


## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer



@pytest.fixture
def testpagestruct():
    pagestruct = {'content': '<p><ac:macro ac:name="children" /></p>',
 'contentStatus': 'current',
 'created': "'20130924T08:45:28'",
 'creator': 'admin',
 'current': 'true',
 'homePage': 'false',
 'id': '524308',
 'modified': "'20130924T08:45:28'",
 'modifier': 'admin',
 'parentId': '524296',
 'permissions': '0',
 'space': '~scholer',
 'title': '2013_Aarhus',
 'url': 'http://10.14.40.245:8090/display/~scholer/2013_Aarhus',
 'version': '1'}
    return pagestruct

@pytest.fixture
def tempfiledir():
    newpath = tempfile.mkdtemp() # Returns path to new temp directory, e.g. /tmp/tmpQ938Rj
    return newpath

@pytest.fixture
def fakeconfighandler_tempdir(monkeypatch, tempfiledir):
    ch = FakeConfighandler(pathscheme='test1')
    #testdir = os.path.join(os.getcwd(), 'tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup')
    testdir = os.path.join(tempfiledir, '2013_exp_subdir_test')
    monkeypatch.setattr(ch, 'getConfigDir', lambda x: testdir)
    ch.setkey('local_exp_subDir', testdir)
    ch.setkey('local_exp_rootDir', os.path.dirname(testdir))
    return ch

@pytest.fixture
def fakeconfighandler():
    ch = FakeConfighandler(pathscheme='test1')
    server = FakeConfluenceServer(autologin=True, ui=None, confighandler=ch)
    ch.Singletons['server'] = server
    return ch


def test_getPage(monkeypatch, fakeconfighandler, testpagestruct):
    monkeypatch.setattr('labfluence_cmd.confighandler', fakeconfighandler)
    #524308
    page = labfluence_cmd.getPage('524308')
    assert page.Struct == testpagestruct


def test_getPageStruct(monkeypatch, fakeconfighandler, testpagestruct):
    monkeypatch.setattr('labfluence_cmd.confighandler', fakeconfighandler)
    #524308
    pagestruct = labfluence_cmd.getPageStruct('524308')
    assert pagestruct == testpagestruct

def test_getPageXhtml(monkeypatch, fakeconfighandler, testpagestruct):
    monkeypatch.setattr('labfluence_cmd.confighandler', fakeconfighandler)
    #524308
    xhtml = labfluence_cmd.getPageXhtml('524308')
    assert xhtml == testpagestruct['content']
