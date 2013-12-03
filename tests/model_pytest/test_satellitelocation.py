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

import pytest
import os
import logging
logger = logging.getLogger(__name__)
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)



from model.satellite_location import SatelliteFileLocation

## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
from model.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer









#from confighandler import ExpConfigHandler
#ch = ExpConfigHandler(pathscheme='default1')
satpath = "/home/scholer/Documents/labfluence_satellite_tests/cdnaafm_cftp"
#sfl = SatelliteFileLocation(satpath, ch)
#


@pytest.fixture
def satellitelocation1():
    sl = SatelliteFileLocation("/home/scholer/Documents/labfluence_satellite_tests/cdnaafm_cftp")

def test_init():
    print "\n>>>>> test_init() -----------------"
    print sfl.__dict__ # equivalent to vars(sfl)
    print "<<<<< completed test_init() -------"

def test_findDirs():
    print "\n>>>>> test_findDirs() -----------------"
#        regexpat = ch.get('exp_subentry_regex').format(expid=RS115, subentry_idx=
    regexpat = ch.get('exp_subentry_regex')
    all_subentries = sfl.findDirs(regexpat)
    print 'all_subentries:'
    print "\n".join(all_subentries)
    print "<<<<< completed test_findDirs() -------"

def test_findSubentries():
    print "\n>>>>> test_findSubentries() -----------------"
#        regexpat = ch.get('exp_subentry_regex').format(expid=RS115, subentry_idx=
    regexpat = ch.get('exp_subentry_regex')
    all_subentries = sfl.findSubentries(regexpat)
    print 'all_subentries:'
    print "\n".join(all_subentries)
    print "<<<<< completed test_findSubentries() -------"



def test_syncToLocalDir1():
    print "\n>>>>> test_syncToLocalDir1() -----------------"
    destdir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/"
    sfl.syncToLocalDir("20130222 RS115g Dry-AFM of transferin TR",
            "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1")
    print "<<<<< completed test_syncToLocalDir1() -------"

def test_syncToLocalDir2():
    print "\n>>>>> test_syncToLocalDir2() -----------------"
    # Testing sync-into with trailing '/' on source:
    destdir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1/RS115g Dry-AFM of Transferrin TR (20130222)"
    if not os.path.exists(destdir):
        os.makedirs(destdir)
    sfl.syncToLocalDir("20130222 RS115g Dry-AFM of transferin TR/", destdir)
    print "<<<<< completed test_syncToLocalDir2() -------"

def test_syncFileToLocalDir():
    print "\n>>>>> test_syncFileToLocalDir() -----------------"
    sfl.syncFileToLocalDir("20130222 RS115g Dry-AFM of transferin TR/RS115g_c5-grd1_TRctrl_130222_105519.mi",
                "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1/20130222 RS115g Dry-AFM of transferin TR (old)")
    print "<<<<< completed test_syncFileToLocalDir() -------"




def test_test():
    pass

print "\n------- starting satellite_locations testing... ----------- "
test_init()
test_findSubentries()
test_findDirs()
#    test_syncFileToLocalDir()
#    test_syncToLocalDir1()
test_syncToLocalDir2()
print "\n------- satellite_locations testing complete ----------- "
