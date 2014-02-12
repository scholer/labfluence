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
# pylint: disable-msg=W0621,C0111,W0212
"""
Tests for the labfluence_cmd.py command line interface module.

"""

import pytest
import os
from collections import OrderedDict
#import tempfile
import logging
logger = logging.getLogger(__name__)
from datetime import datetime


## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer
from tkui.tkui_testdoubles.fake_tkroot import FakeLimsTkroot


#########################
### System under test ###
#########################
#from limsapp import LimsApp
from tkui import lims_app




# setting scope="module" can reduce test time.
# In the current case, reduces time with 75%,
# however, individual tests are no longer independent...!
# "function" (default), "class", "module", "session".
@pytest.fixture(scope="module")
def fakeconfighandler():
    return FakeConfighandler()


@pytest.fixture(scope="module")
def fakeserver(fakeconfighandler):
    return FakeConfluenceServer(fakeconfighandler)


@pytest.fixture(scope="module")
def fakeserver_nocache(fakeconfighandler):
    return FakeConfluenceServer(fakeconfighandler)


@pytest.fixture
def confighandler_with_server(fakeserver):
    ch = fakeserver.Confighandler
    ch.Singletons['server'] = fakeserver
    return ch

@pytest.fixture
def limsapp_nodeps():
    app = lims_app.LimsApp()
    return app


@pytest.fixture
def limsapp_deps(monkeypatch, confighandler_with_server):
    monkeypatch.setattr(lims_app, 'LimsTkRoot', FakeLimsTkroot)
    app = lims_app.LimsApp(confighandler_with_server)
    app.FilesToAdd = (os.path.join(os.getcwd(), 'tests', 'test_data', 'attachments', fn) for fn in ('visualization.pdf', ))
    return app



def test_nextfile(limsapp_deps):
    app = limsapp_deps
    nf = app.nextfile()
    assert nf == os.path.join(os.getcwd(), 'tests', 'test_data', 'attachments', 'visualization.pdf')
    nf = app.nextfile()
    assert nf is None
    nf = app.nextfile()
    assert nf is None

def test_getLimsFields(limsapp_deps):
    app = limsapp_deps
    def mock_getheaderfields():
        return ['date', 'product name', 'comment', 'Order file(s)']
    app.WikiLimsPage.getTableHeaders = mock_getheaderfields
    #monkeypatch.setattr(self.WikiLimsPage.getTableHeaders)
    expected = OrderedDict([('date', datetime.now().strftime("%Y%m%d")), ('product name', ''), ('comment', ''), ('Path to order file', ''), ('Attachment name', '')])
    hf = app.getLimsFields()
    print hf
    assert hf == expected

def test_repopulatePrompt(limsapp_deps):
    app = limsapp_deps
    #def mock_getheaderfields():
    #    return ['date', 'product name', 'comment', 'Order file(s)']
    ## does not work, app has already invoked getLimsFields and created ui...
    #app.WikiLimsPage.getTableHeaders = mock_getheaderfields
    # Refer to test data set instead...
    # Date (yyyymmdd)</p></th><th><p>Compound name</p></th><th><p>Amount</p></th><th><p>Price
    #  (dkk)</p></th><th><p>Ordered by</p></th><th><p>Manufacturer / distributor</p></th><th><p>Comments</p></th>
    app.repopulatePrompt()
    app.Tkroot.Fieldvars['Date (yyyymmdd)'][0].set('hej der')
    assert app.Tkroot.Fieldvars['Date (yyyymmdd)'][0].get() == 'hej der'
    app.Tkroot.Fieldvars['Amount'][0].set('some amount')
    assert app.Tkroot.Fieldvars['Amount'][0].get() == 'some amount'
    app.repopulatePrompt()
    assert app.Tkroot.Fieldvars['Date (yyyymmdd)'][0].get() == 'hej der'
    assert app.Tkroot.Fieldvars['Amount'][0].get() == ''


def test_start(limsapp_deps):
    app = limsapp_deps
    app.start()

def test_set_entry_added_message(limsapp_deps):
    app = limsapp_deps
    entry_info = dict()
    assert app.Tkroot.Message.get() == ''
    app.set_entry_added_message(entry_info, dict())
    print app.Tkroot.Message.get()
    assert app.Tkroot.Message.get() == 'Entry None added; add new...'

def test_get_result(limsapp_deps):
    app = limsapp_deps
    app.Tkroot.Fieldvars['Amount'][0].set('a lot')
    app.Tkroot.Fieldvars['Compound name'][0].set('x-mas present')
    res = app.Tkroot.get_result()
    assert res['Amount'] == 'a lot'
    assert res['Compound name'] == 'x-mas present'


def test_add_entry(limsapp_deps):
    app = limsapp_deps
    # 1:
    app.PersistPageForEveryEntry = True
    app.Tkroot.Fieldvars['Amount'][0].set('a lot')
    app.Tkroot.Fieldvars['Compound name'][0].set('x-mas present')
    app.add_entry()
    logger.debug( " app.WikiLimsPage.Content: %s", app.WikiLimsPage.Content )
    assert 'x-mas present' in app.WikiLimsPage.Content
    # 2:
    app.PersistPageForEveryEntry = False
    app.Tkroot.Fieldvars['Amount'][0].set('some more')
    app.Tkroot.Fieldvars['Compound name'][0].set('easter bunny')
    #oldfun = app.next_entry
    #app.next_entry = lambda x: None
    app.add_entry(addNewEntryWithSameFile=True)
    assert 'easter bunny' not in app.WikiLimsPage.Content
    assert app.EntriesToAdd[0]['Amount'] == 'some more'
    assert app.EntriesToAdd[0]['Compound name'] == 'easter bunny'
    # 3:
    app.Tkroot.Fieldvars['Amount'][0].set('alotta stuff')
    app.Tkroot.Fieldvars['Compound name'][0].set('loch_ness')
    #oldfun = app.next_entry
    app.next_entry = lambda *x: None
    app.add_entry(addNewEntryWithSameFile=False)
    assert 'easter bunny' not in app.WikiLimsPage.Content
    assert app.EntriesToAdd[1]['Amount'] == 'alotta stuff'
    assert app.EntriesToAdd[1]['Compound name'] == 'loch_ness'



def test_next_entry(limsapp_deps):
    app = limsapp_deps
    app.Tkroot.Fieldvars['Amount'][0].set('a lot')
    app.Tkroot.Fieldvars['Compound name'][0].set('new-year present')
    app.next_entry()
    assert app.Tkroot.Fieldvars['Amount'][0].get() == ''
    assert app.Tkroot.Fieldvars['Compound name'][0].get() == ''
    app.Tkroot.Fieldvars['Amount'][0].set('a lot')
    app.Tkroot.Fieldvars['Compound name'][0].set('new-year present')
    print " app.WikiLimsPage.Content: "
    print  app.WikiLimsPage.Content
    # calling next_entry should NOT add the entry, only prepare the form for next entry.
    assert 'new-year present' not in app.WikiLimsPage.Content

    # There should not be any more files.
    # this should persist the page, but not add any further changes to the content.
    app.next_entry()
    assert app.Tkroot.Fieldvars['Amount'][0].get() == 'a lot'
    assert app.Tkroot.Fieldvars['Compound name'][0].get() == 'new-year present'
    assert app.Tkroot._destroyed == True
    # I am currently scoping fixtures on module level, so 'x-mas present' will be present...
    assert 'new-year present' not in app.WikiLimsPage.Content


def test_flush_entries_cache(limsapp_deps):
    app = limsapp_deps
    app.WikiLimsPage.addEntries = lambda *x: None
    app.save_entries = lambda *x: None
    app.EntriesToAdd = list()
    assert app.flush_entries_cache() == False
    assert app.EntriesToAdd == list()
    app.EntriesToAdd = [{'Amount': 'a_lot', 'Compound name': 'new-year present'},
                        {'Amount': 'some_more', 'Compound name': 'easter_present'}]
    assert app.flush_entries_cache() == True
    assert app.EntriesToAdd == list()



def test_pageid_argument(monkeypatch, confighandler_with_server):
    monkeypatch.setattr(lims_app, 'LimsTkRoot', FakeLimsTkroot)
    app = lims_app.LimsApp(confighandler_with_server, pageId='123456')
    app.FilesToAdd = (os.path.join(os.getcwd(), 'tests', 'test_data', 'attachments', fn) for fn in ('visualization.pdf', ))
    assert app.LimsPageId == '123456' # app uses 'LimsPageId', the page object attribute is just PageId.
