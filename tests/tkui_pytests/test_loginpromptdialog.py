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
# pylint: disable-msg=C0111,W0621


import pytest
import logging
logger = logging.getLogger(__name__)
# Note: Switched to using pytest-capturelog, captures logging messages automatically...



##############################
#######    SUT     ###########
##############################

from tkui.views.loginprompt import LoginPrompt

## Test doubles:
#from model.model_testdoubles.fake_confighandler import FakeConfighandler
#from model.model_testdoubles.fake_server import FakeConfluenceServer

# Non-faked dependencies:
#from model.experimentmanager import ExperimentManager
import Tkinter as tk


#@pytest.fixture
#def ch_with_server_and_manager():
#    ch = FakeConfighandler()
#    server = FakeConfluenceServer(confighandler=ch)
#    ch.Singletons.setdefault('server', server)
#    em = ExperimentManager(ch)
#    ch.Singletons.setdefault('experimentmanager', em)
#    return ch

@pytest.fixture
def tkroot():
    try:
        logging.debug("Instantiating tk root:")
        root = tk.Tk()
    except tk.TclError as e:
        logger.warning("Tk could not initialize, probably because there is no display available: %s", e)
        return
    return root


def test_loginprompt_nofieldvarsinput(tkroot):
    print "loginprompt test started..."
    if not tkroot:
        pytest.skip("No tkroot available for testing - are you running through terminal?")
        return
    print "loginprompt test got tkroot, initiating dialog..."
    # Something is causing the dialog to halt the test, likely one of:
    # initial_focus, grab_set(), protocol, geometry, initial_focus.focus_set(), wait_window()
    dia = LoginPrompt(tkroot, username='test_user')
    print "testing loginprompt dialog..."
    assert dia.EntryWidgets['username'].get() == 'test_user'
    assert dia.EntryWidgets['password'].get() == ''
    dia.ok() # should fail
    assert dia.result is None
    dia.EntryWidgets['username'].set('other_user')
    dia.EntryWidgets['password'].set('other_passwd')
    assert dia.EntryWidgets['username'].get() == 'other_user'
    assert dia.EntryWidgets['password'].get() == 'other_passwd'
    dia.ok()
    assert dia.result['username'] == 'other_user'
    assert dia.result['password'] == 'other_passwd'
    dia.EntryWidgets['username'].set('should fail')
    print "loginprompt test finished..."
    assert 0


