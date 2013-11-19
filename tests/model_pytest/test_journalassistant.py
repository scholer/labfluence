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
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)



from model.experiment import Experiment
from model.experiment_manager import ExperimentManager
#from model.confighandler import ExpConfigHandler
#from model.server import ConfluenceXmlRpcServer

## Test doubles:
from tests.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
from tests.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer



## classical xunit setup in pytest: http://pytest.org/latest/xunit_setup.html
## Alternatively, consider using fixtures: http://pytest.org/latest/fixture.html
# module-level setup:
def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    ldir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
    ch = ExpConfigHandler(pathscheme='test1')
    rootdir = confighandler.get("local_exp_subDir")
    server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=1, autologin=True)

# per-function setup:
def setup_function(function):
    e = Experiment(confighandler=ch, server=server, localdir=ldir, VERBOSE=10)
    e.attachWikiPage(dosearch=True)
    ja = e.JournalAssistant
    ja.Current_subentry_idx = 'c'


## I think using fixtures is a bit cleaner, for every test, you specify the name of
## a fixture as a required argument. pytest will do the code inspection and see what needs to be filled in,
## searching for functions marked with @pytest.fixture

def test_addEntry():
    ja.addEntry("Buffer: 10/100 mM HEPES/KCl pH with 0.5 mM biotin."+random_string(5))
    ja.addEntry("""Adding 100 ul buffer to RS102b and running through amicon 3k filter. I dont dilute to 400 ul because I want to be able to trace unreacted DBCO-ddUTP.
Washing retentate 4 more times with 400 ul buffer, collecting filt2-3 and filt4-6.""")
    ja.addEntry("""Doing UVvis quant on nanodrop (if it is still running during the chemists move).
- EDIT: Nanodrop is down due to move, so no quant. I will assume we have 75% yield and recovery during synthesis, so 1.5 nmol in 30 ul giving a concentration of 1500pmol/30ul = 50 uM. (?)""")

def test_getCacheContent():
    print ja.getCacheContent()

def test_flush():
    ja.addEntry("test entry for flush test"+random_string(10))
    ja.flush()
