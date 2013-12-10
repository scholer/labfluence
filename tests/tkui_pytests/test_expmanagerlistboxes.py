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

from tkui.views.expmanagerlistboxes import ActiveExpsListbox, ExpManagerListBox, LocalExpsListbox, RecentExpsListbox, WikiExpsListbox

## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer

# Non-faked dependencies:
from model.experimentmanager import ExperimentManager
import Tkinter as tk


@pytest.fixture
def ch_with_server_and_manager():
    ch = FakeConfighandler()
    server = FakeConfluenceServer(confighandler=ch)
    ch.Singletons.setdefault('server', server)
    em = ExperimentManager(ch)
    ch.Singletons.setdefault('experimentmanager', em)
    return ch

@pytest.fixture
def tkroot():
    root = tk.Tk()
    return root



def test_ExpManagerListBox(ch_with_server_and_manager, tkroot):
    ch = ch_with_server_and_manager
    lb = ExpManagerListBox(tkroot, ch)
    assert lb.update_widget() is None
    assert lb.getExpIds() == list()
    tpl = lb.getTupleList()
    assert hasattr(tpl, '__iter__')
    assert lb.getSelectedIds() == []
