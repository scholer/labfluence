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
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)



##############################
#######    SUT     ###########
##############################

#from tkui.views.explistboxes import ActiveExpsListbox, ExpManagerListBox, LocalExpsListbox, RecentExpsListbox, WikiExpsListbox
from tkui.views.explistboxes import ExpListbox, FilelistListbox, LocalFilelistListbox, SubentriesListbox, WikiFilelistListbox

## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer

# Non-faked dependencies:
from model.experimentmanager import ExperimentManager
import Tkinter as tk


@pytest.fixture
def ch_with_server_and_manager():
    ch = FakeConfighandler()
    server = FakeConfluenceServer(ch)
    ch.Singletons.setdefault('server', server)
    em = ExperimentManager(ch)
    ch.Singletons.setdefault('experimentmanager', em)
    return ch

@pytest.fixture
def tkroot():
    root = tk.Tk()
    return root




