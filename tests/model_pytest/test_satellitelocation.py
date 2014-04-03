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
# pylint: disable=C0103

import pytest
import os
import yaml
import logging
logger = logging.getLogger(__name__)
# Note: Switched to using pytest-capturelog, captures logging messages automatically...



from model.satellite_location import SatelliteFileLocation

## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
from model.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer

from directorymockstructure import DirectoryMockstructure

# /tests/model_pytest/test_satellitelocation.py
testdatadir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'test_data')


#from confighandler import ExpConfigHandler
#ch = ExpConfigHandler(pathscheme='default1')
#satpath = "/home/scholer/Documents/labfluence_satellite_tests/cdnaafm_cftp"
#sfl = SatelliteFileLocation(satpath, ch)
#

testconfig = yaml.load(r"""
exp_folder_regexs:
  experiment: (?P<expid>RS[0-9]{3})[_ ]+(?P<exp_titledesc>.+)
  subentry: (?P<expid>RS[0-9]{3})-?(?P<subentry_idx>[^_])[_ ]+(?P<subentry_titledesc>.+?)\s*(\((?P<date>[0-9]{8})\))?$
  expidx_from_expid: RS(?P<exp_series_index>[0-9]{3,4})
  year: (?P<year>[0-9]{4}).*
satellite_locations:
  CDNA AFM:
    uri: /home/scholer/Documents/labfluence_satellite_tests/cdnaafm_cftp
    folderscheme: ./subentry/
    protocol: file
    rootdir: .
  Typhoon:
    protocol: file
    uri: /home/scholer/Documents/labfluence_satellite_tests/typhoon_cftp
    folderscheme: ./subentry/
    mountcommand: curlftpfs ftp://user:password@10.17.75.109 /mnt/typhoon_ftp
    rootdir: .
  LocalWin:
    protocol: file
    uri: /home/scholer/Documents
    folderscheme: ./year/experiment/subentry/
    rootdir: .
""")

locations1 = testconfig['satellite_locations']


@pytest.fixture
def directorymockstructure_win2014():
    print "testdatadir: ", testdatadir
    fp = os.path.join(testdatadir, 'test_filestructure', 'windirstructure_short.txt')
    assert os.path.isfile(fp)
    ds = DirectoryMockstructure()
    ds.loadFromFlatFile(fp)
    return ds


@pytest.fixture
def satellitelocation_standalone_fswinmock(directorymockstructure_win2014, monkeypatch):
    ds = directorymockstructure_win2014
    locationparams = locations1['LocalWin']
    monkeypatch.setattr(SatelliteFileLocation, 'isMounted', lambda dirpath: 1)
    sl = SatelliteFileLocation(locationparams)
    sl.Regexs = testconfig['exp_folder_regexs']
    # sl.Rootdir = '.' # Is set by locationparams...
    # Patch the methods:
    sl.listdir = ds.listdir
    sl.isdir = ds.isdir
    sl.join = ds.join
    sl.getRealPath = ds.getRealPath
    sl.rename = ds.rename
    return sl



##############################
## SatelliteLocation tests ###
##############################

def test_basics(monkeypatch):
    locationparams = locations1['Typhoon']
    monkeypatch.setattr(SatelliteFileLocation, 'isMounted', lambda dirpath: 1)
    sl = SatelliteFileLocation(locationparams)
    sl.Regexs = testconfig['exp_folder_regexs']


logging.getLogger('directorymockstructure').setLevel(logging.INFO)
logging.getLogger('tests.model_pytest.directorymockstructure').setLevel(logging.INFO)
logging.getLogger('labfluence.tests.model_pytest.directorymockstructure').setLevel(logging.INFO) # this works...



def test_genPathmatchTupsByPathscheme(satellitelocation_standalone_fswinmock):
    """
    genPathmatchTupsByPathscheme
    """
    sl = satellitelocation_standalone_fswinmock
    pathmatchtups = sl.genPathmatchTupsByPathscheme(regexs=None, basedir=None, folderscheme=None)
    # path scheme is ./experiment/subentry
    pathmatchnumbers = 0
    for pathmatchtup in pathmatchtups:
        pathmatchnumbers += 1
        assert len(pathmatchtup) == 2
        assert set(pathmatchtup[1].keys()) == set("year/experiment/subentry".split('/'))
    assert pathmatchnumbers > 0

def test_getSubentryFoldersByExpIdSubIdx(satellitelocation_standalone_fswinmock):
    """
    getSubentryFoldersByExpIdSubIdx
    expsubfolders is dict-based datastructure:
        expsubfolders[<expid>][<subentry_idx>] = subentry folderpath
    e.g.
        expsubfolders['RS195']['b'] = '2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V from a (20140210)'
    """
    sl = satellitelocation_standalone_fswinmock
    expsubfolders = sl.getSubentryFoldersByExpIdSubIdx()
    assert expsubfolders['RS195']['b'] == './2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V from a (20140210)'


@pytest.mark.skipif(True, reason="Not ready yet")
def test_init():
    print "\n>>>>> test_init() -----------------"
    print sfl.__dict__ # equivalent to vars(sfl)
    print "<<<<< completed test_init() -------"

@pytest.mark.skipif(True, reason="Not ready yet")
def test_findDirs():
    print "\n>>>>> test_findDirs() -----------------"
#        regexpat = ch.get('exp_subentry_regex').format(expid=RS115, subentry_idx=
    regexpat = ch.get('exp_subentry_regex')
    all_subentries = sfl.findDirs(regexpat)
    print 'all_subentries:'
    print "\n".join(all_subentries)
    print "<<<<< completed test_findDirs() -------"

@pytest.mark.skipif(True, reason="Not ready yet")
def test_findSubentries():
    print "\n>>>>> test_findSubentries() -----------------"
#        regexpat = ch.get('exp_subentry_regex').format(expid=RS115, subentry_idx=
    regexpat = ch.get('exp_subentry_regex')
    all_subentries = sfl.findSubentries(regexpat)
    print 'all_subentries:'
    print "\n".join(all_subentries)
    print "<<<<< completed test_findSubentries() -------"



@pytest.mark.skipif(True, reason="Not ready yet")
def test_syncToLocalDir1():
    print "\n>>>>> test_syncToLocalDir1() -----------------"
    destdir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/"
    sfl.syncToLocalDir("20130222 RS115g Dry-AFM of transferin TR",
            "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1")
    print "<<<<< completed test_syncToLocalDir1() -------"

@pytest.mark.skipif(True, reason="Not ready yet")
def test_syncToLocalDir2():
    print "\n>>>>> test_syncToLocalDir2() -----------------"
    # Testing sync-into with trailing '/' on source:
    destdir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1/RS115g Dry-AFM of Transferrin TR (20130222)"
    if not os.path.exists(destdir):
        os.makedirs(destdir)
    sfl.syncToLocalDir("20130222 RS115g Dry-AFM of transferin TR/", destdir)
    print "<<<<< completed test_syncToLocalDir2() -------"

@pytest.mark.skipif(True, reason="Not ready yet")
def test_syncFileToLocalDir():
    print "\n>>>>> test_syncFileToLocalDir() -----------------"
    sfl.syncFileToLocalDir("20130222 RS115g Dry-AFM of transferin TR/RS115g_c5-grd1_TRctrl_130222_105519.mi",
                "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1/20130222 RS115g Dry-AFM of transferin TR (old)")
    print "<<<<< completed test_syncFileToLocalDir() -------"




@pytest.mark.skipif(True, reason="Not ready yet")
def test_test():
    pass
