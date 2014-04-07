#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2013-2014 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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
# pylint: disable=C0103,C0111,W0212

import pytest
import os
import sys
import yaml
import logging
logger = logging.getLogger(__name__)
# Note: Switched to using pytest-capturelog, captures logging messages automatically...

from pathutils import walkup

approotdir = os.path.join(walkup(os.path.realpath(__file__), 3))
modeldir = os.path.join(approotdir, 'model')
testsdir = os.path.join(approotdir, 'tests')
testdatadir = os.path.join(testsdir, 'test_data')
sys.path.append(approotdir)
sys.path.append(modeldir)


#### SUT ####

from model.satellite_location import SatelliteFileLocation

## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
from model.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer

from directorymockstructure import DirectoryMockstructure

#logging.getLogger('directorymockstructure').setLevel(logging.INFO)
#logging.getLogger('tests.model_pytest.directorymockstructure').setLevel(logging.INFO)
logging.getLogger('labfluence.tests.model_pytest.directorymockstructure').setLevel(logging.INFO) # this works...



#from confighandler import ExpConfigHandler
#ch = ExpConfigHandler(pathscheme='default1')
#satpath = "/home/scholer/Documents/labfluence_satellite_tests/cdnaafm_cftp"
#sfl = SatelliteFileLocation(satpath, ch)

def method_log_counter_decorator(method, invocationcounter=None):
    def replacementmethod(*args, **kwargs):
        logger.info("%s(*args=%s, **kwargs=%s) method routed through log_counter_decorator.",
                    method.__name__, args, kwargs)
        invocationcounter.append(1)
        return method(*args, **kwargs) # remember the return...
    return replacementmethod



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

def test_getSubentryfoldersByExpidSubidx(satellitelocation_standalone_fswinmock):
    """
    getSubentryfoldersByExpidSubidx
    subentryfoldersbyexpidsubidx is dict-based datastructure:
        subentryfoldersbyexpidsubidx[<expid>][<subentry_idx>] = subentry folderpath
    e.g.
        subentryfoldersbyexpidsubidx['RS195']['b'] = '2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V from a (20140210)'
    """
    sl = satellitelocation_standalone_fswinmock
    subentryfoldersbyexpidsubidx = sl.getSubentryfoldersByExpidSubidx()
    expected = os.path.normpath('./2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V from a (20140210)')
    assert subentryfoldersbyexpidsubidx['RS195']['b'] == expected


def test_SubentryfoldersByExpidSubidx(satellitelocation_standalone_fswinmock, monkeypatch):
    """
    SubentryfoldersByExpidSubidx, cached property.
    subentryfoldersbyexpidsubidx is dict-based datastructure:
        subentryfoldersbyexpidsubidx[<expid>][<subentry_idx>] = subentry folderpath
    e.g.
        subentryfoldersbyexpidsubidx['RS195']['b'] = '2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V from a (20140210)'
    """
    sl = satellitelocation_standalone_fswinmock
    subentryfoldersbyexpidsubidx = sl.SubentryfoldersByExpidSubidx
    expected = os.path.normpath('./2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V from a (20140210)')
    assert subentryfoldersbyexpidsubidx['RS195']['b'] == expected
    flagchanged = list()
    def dummymethod(*args, **kwargs):
        #flagchanged += 1
        logger.info("Intercept by dummy method!")
        flagchanged.append(1)
    sl.update_expsubfolders = dummymethod
    # Just creating dummymethod does not work, -- edit: yes it does, if you use a pointer-variable, e.g. a list.
    # the environment in which dummymethod is run does not find flagchanged variable.
    # This does not work either:
#def createdummy():
#    #flagchanged = list()
#    def dummymethod(*args, **kwargs):
#        flagchanged += 1
#    return dummymethod
    #sl.update_expsubfolders = createdummy()
    # This does not work either:
    # monkeypatch.setattr(sl, 'update_expsubfolders', dummymethod)
    # To do this you have two options, either make a closure (returning a closure)
    # or use/modify dummymethod.func_globals
    #dummymethod.func_globals['flagchanged'] = flagchangedchang
    ### AHHH, it is because doing
    #       flagchanged += 1      creates a new variable, i.e. it does work with a pointer but creates a new reference instead.
    # To overcome this, modify a list instead.
    subentryfoldersbyexpidsubidx2 = sl.SubentryfoldersByExpidSubidx
    assert flagchanged == []
    assert subentryfoldersbyexpidsubidx2 == subentryfoldersbyexpidsubidx
    del sl._cache['SubentryfoldersByExpidSubidx']
    expsubfolders3 = sl.SubentryfoldersByExpidSubidx
    assert flagchanged == [1]
    assert expsubfolders3 == subentryfoldersbyexpidsubidx


def test_renamesubentryfolder(satellitelocation_standalone_fswinmock, monkeypatch):
    """
    renamesubentryfolder
    """
    sl = satellitelocation_standalone_fswinmock
    subentryfoldersbyexpidsubidx = sl.SubentryfoldersByExpidSubidx # map [expid][subidx] = path

    # Test using newname with only basename:
    firstpath = os.path.normpath('./2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V from a (20140210)')
    newname = 'RS195b TEM of HCav6V NEW NEW NEW'
    expected = os.path.normpath('./2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V NEW NEW NEW')
    assert os.path.normpath(subentryfoldersbyexpidsubidx['RS195']['b']) == os.path.normpath(firstpath)
    assert sl.ExpidSubidxByFolder[firstpath] == ('RS195', 'b')  # Reverse map: path --> (expid, subidx)
    assert firstpath in sl.Subentryfoldersset
    assert sl.SubentryfoldersByExpidSubidx['RS195']['b'] == firstpath # assert that we do not make a new map
    # Perform rename
    sl.renamesubentryfolder(firstpath, newname)
    # And check:
    assert os.path.normpath(subentryfoldersbyexpidsubidx['RS195']['b']) == expected #
    assert sl.ExpidSubidxByFolder[expected] == ('RS195', 'b')  # Reverse map: path --> (expid, subidx)
    assert expected in sl.Subentryfoldersset
    assert sl.SubentryfoldersByExpidSubidx['RS195']['b'] == expected #
    assert firstpath not in sl.ExpidSubidxByFolder  # Reverse map: path --> (expid, subidx)
    assert firstpath not in sl.Subentryfoldersset

    # Test using newname with full path:
    firstpath = expected
    newname = './2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V NEW 2'
    expected = os.path.normpath('./2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V NEW 2')
    assert os.path.normpath(subentryfoldersbyexpidsubidx['RS195']['b']) == firstpath
    assert sl.ExpidSubidxByFolder[firstpath] == ('RS195', 'b')  # Reverse map: path --> (expid, subidx)
    assert firstpath in sl.Subentryfoldersset
    assert sl.SubentryfoldersByExpidSubidx['RS195']['b'] == firstpath # assert that we do not make a new map
    # Perform rename
    sl.renamesubentryfolder(firstpath, newname)
    # And check:
    assert subentryfoldersbyexpidsubidx['RS195']['b'] == expected #
    assert sl.ExpidSubidxByFolder[expected] == ('RS195', 'b')  # Reverse map: path --> (expid, subidx)
    assert expected in sl.Subentryfoldersset
    assert sl.SubentryfoldersByExpidSubidx['RS195']['b'] == expected #
    assert firstpath not in sl.ExpidSubidxByFolder  # Reverse map: path --> (expid, subidx)
    assert firstpath not in sl.Subentryfoldersset

def test_ensuresubentryfoldername(satellitelocation_standalone_fswinmock, monkeypatch):
    """
    ensuresubentryfoldername
    """
    sl = satellitelocation_standalone_fswinmock
    subentryfoldersbyexpidsubidx = sl.SubentryfoldersByExpidSubidx # map [expid][subidx] = path
    rename_invocations = list()
    sl.rename = method_log_counter_decorator(sl.rename, rename_invocations)

    # Test using newname that matches existing name:
    expid, subidx = 'RS195', 'b'
    firstpath = os.path.normpath('./2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V from a (20140210)')
    newname = 'RS195b TEM of HCav6V from a (20140210)'
    # Check that state is correct before:
    expected = os.path.normpath('./2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V NEW NEW NEW')
    assert os.path.normpath(subentryfoldersbyexpidsubidx['RS195']['b']) == os.path.normpath(firstpath)
    assert sl.ExpidSubidxByFolder[firstpath] == ('RS195', 'b')  # Reverse map: path --> (expid, subidx)
    assert firstpath in sl.Subentryfoldersset
    assert sl.SubentryfoldersByExpidSubidx['RS195']['b'] == firstpath # assert that we do not make a new map
    # Perform ensuresubentryfoldername(expid, subidx, subentryfoldername)
    sl.ensuresubentryfoldername(expid, subidx, newname)
    # And check:
    assert rename_invocations == []
    assert sl.ExpidSubidxByFolder[firstpath] == ('RS195', 'b')  # Reverse map: path --> (expid, subidx)
    assert sl.SubentryfoldersByExpidSubidx['RS195']['b'] == firstpath # assert that we do not make a new map


    # Test using a new newname:
    newname = 'RS195b TEM of HCav6V NEW NEW NEW'
    expected = os.path.normpath('./2014_Aarhus/RS195 HCav6V Assembly for MV/RS195b TEM of HCav6V NEW NEW NEW')
    # Perform ensuresubentryfoldername(expid, subidx, subentryfoldername)
    sl.ensuresubentryfoldername(expid, subidx, newname)
    # And verify:
    assert rename_invocations == [1]
    assert os.path.normpath(subentryfoldersbyexpidsubidx['RS195']['b']) == expected #
    assert sl.ExpidSubidxByFolder[expected] == ('RS195', 'b')  # Reverse map: path --> (expid, subidx)
    assert expected in sl.Subentryfoldersset
    assert sl.SubentryfoldersByExpidSubidx['RS195']['b'] == expected #
    assert firstpath not in sl.ExpidSubidxByFolder  # Reverse map: path --> (expid, subidx)
    assert firstpath not in sl.Subentryfoldersset



def test_caching(satellitelocation_standalone_fswinmock):
    """
    Test property caching of slow SubentryfoldersByExpidSubidx property
    which invokes getSubentryfoldersByExpidSubidx() method.
    """
    sl = satellitelocation_standalone_fswinmock
    updateinvocations = list()
    getfolderbyid_invocations = list()
    ## IMPORTANT: THIS WILL NOT WORK. It will start a recursive loop where
    ## when it invokes sl.getSubentryfoldersByExpidSubidx it invokes it self.
    #def getfolderbyid_method(*args, **kwargs):
    #    logger.info("Intercept by getfolderbyid_method dummy method!")
    #    getfolderbyid_invocations.append(1)
    #    return sl.getSubentryfoldersByExpidSubidx(*args, **kwargs)
    ## INSTEAD, use a standard decorator-like closure:

    oldupdatemethod = sl.update_expsubfolders
    oldgetfolderbyidmethod = sl.getSubentryfoldersByExpidSubidx
    #monkeypatch.setattr(sl, 'update_expsubfolders', dummymethod)
    sl.update_expsubfolders = method_log_counter_decorator(sl.update_expsubfolders, invocationcounter=updateinvocations)
    sl.getSubentryfoldersByExpidSubidx = method_log_counter_decorator(sl.getSubentryfoldersByExpidSubidx, invocationcounter=getfolderbyid_invocations)
    logger.debug(" >>> Getting sl.SubentryfoldersByExpidSubidx >>> ")
    subentryfoldersbyexpidsubidx2 = sl.SubentryfoldersByExpidSubidx
    logger.debug(" <<< sl.SubentryfoldersByExpidSubidx received <<< ")
    logger.debug(" >>> Getting sl.ExpidSubidxByFolder >>> ")
    expidsubidxbyfolder = sl.ExpidSubidxByFolder # Reverse map: path --> (expid, subidx)
    logger.debug(" <<< sl.ExpidSubidxByFolder received <<< ")
    logger.debug(" >>> Getting sl.Subentryfoldersset >>> ")
    subentryfoldersset = sl.Subentryfoldersset
    logger.debug(" <<< sl.Subentryfoldersset received <<< ")

    assert updateinvocations == [1]
    assert getfolderbyid_invocations == [1]




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
