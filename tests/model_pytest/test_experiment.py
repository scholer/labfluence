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
# pylint: disable-msg=F0401,C0103,C0301,C0111,W0613,W0621,W0142




import pytest
from collections import OrderedDict
import re
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
# Note: Switched to using pytest-capturelog, captures logging messages automatically...

from model.experiment import Experiment

## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
#from model.model_testdoubles.fake_server import FakeConfluenceServer

## Also consider mocking all other objects not part of the SUT (system under test, i.e. the Experiment class)
# In addition to server and confighandler, this includes:
# - WikiPage and WikiPageFactory
# - JournalAssistant
# - ExperimentManager


TESTDATADIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_data', 'test_filestructure', 'labfluence_data_testsetup', '2013_Aarhus')

pagexhtml1 = """
<h3>About</h3><p><strong>Purpose:</strong></p><p><strong>Summary:</strong></p><p><strong>Lessons:</strong></p><p><strong>Project(s):</strong></p><p><strong>Previous experiments and related pages:</strong></p><p><strong>Overview/outline:&nbsp;</strong></p><p><strong>Samples:</strong></p><h2>Experimental section</h2>
Something...
<h4>RS189a Pipetting TR SS MBL staples for MV </h4><h6>Plan, setup, mixing schemes, etc</h6><h6>Journal, 20140109</h6><p>RS189a journal</p>

<h4>RS189-b Pipetting TR ss-col410-bg staples with Anders  (20140108)</h4><h6>Plan, setup, mixing schemes, etc</h6><h6>Journal, 20140108</h6>
<p>RS189b journal</p>
<h4>RS189_c Pipetting TR.SS cols with new IDT_Jan14 staples (201405)</h4><h6>Plan, setup, mixing schemes, etc</h6><h6>Journal, 20140115</h6><p>RS189c journal</p>
<h2>Results and discussion</h2><h6>Gallery</h6><p>X-gal</p><h6>Observations</h6><h6>Discussion</h6><h6>Conclusion</h6><h6>Lessons learned</h6><h6>Outlook</h6><h2>Attachments</h2><p>Hello</p>
"""
# date is pop'ed if it is None. expid is not included parsed but is constant in the format()ed regex.
# Remember that kwargs is not a good way to define an ordered dict ;-)
pagexhtml1_expectedprops = OrderedDict([('a', dict(subentry_idx='a', subentry_titledesc="Pipetting TR SS MBL staples for MV")),
                                        ('b', dict(subentry_idx='b', date=datetime.strptime("20140108", "%Y%m%d"), subentry_titledesc="Pipetting TR ss-col410-bg staples with Anders")),
                                        ('c', dict(subentry_idx='c', subentry_titledesc="Pipetting TR.SS cols with new IDT_Jan14 staples (201405)"))])

@pytest.fixture
def expprops():
    expprops = dict(expid='RS099', exp_titledesc="Pytest titledesc", exp_subentries=OrderedDict())
    return expprops

@pytest.fixture
def exppropsRS189():
    return dict(expid='RS189', exp_titledesc="Pipetting TR SS staples for MBL and col410", exp_subentries=OrderedDict())



@pytest.fixture
def exp_no_wikipage_or_subentries(expprops):
    confighandler = ExpConfigHandler( pathscheme='test1' )
    experiment = Experiment(confighandler=confighandler,
                            props=expprops,
                            autoattachwikipage=False,
                            doparseLocaldirSubentries=False)
    return experiment


def test_parseLocaldirSubentries(exp_no_wikipage_or_subentries, monkeypatch):
    e = exp_no_wikipage_or_subentries
    def listdirmock(*args):
        return ["RS191a Subentry test a", "20131224 RS191b Subentry testb",
                "RS191c Subentry test-c (20131225)", "20131226 RS191d Subentry test _d (20131227)"]
    monkeypatch.setattr(os, 'listdir', listdirmock)
    monkeypatch.setattr(os.path, 'isdir', lambda x: True)
    # Discarting e afterwards, so no reason to monkeypatch:
    e.Subentries_regex_prog = re.compile(r"(?P<date1>[0-9]{8})?[_ ]*(?P<expid>RS[0-9]{3})-?(?P<subentry_idx>[^_])[_ ]+(?P<subentry_titledesc>.+?)\s*(\((?P<date2>[0-9]{8})\))?$")
    monkeypatch.setattr(e, 'Localdirpath', 'something unimportant')
    subentries = e.parseLocaldirSubentries()
    assert len(subentries) == 4
    assert subentries.keys() == ['a', 'b', 'c', 'd']
    assert all(subentry['expid'] == 'RS191' for subentry in subentries.values())
    assert [subentry['date'] for subentry in subentries.values()] == [None, '20131224', '20131225', '20131226']
    assert [subentry['subentry_titledesc'] for subentry in subentries.values()] \
            == ['Subentry test a', 'Subentry testb', 'Subentry test-c', 'Subentry test _d']


def test_getFoldernameAndParentdirpath(exp_no_wikipage_or_subentries, monkeypatch):
    e = exp_no_wikipage_or_subentries
    # test 1: value from confighandler:
    monkeypatch.setattr(e.Confighandler, 'get', lambda key: TESTDATADIR)
    localtestdir = "RS105 TR STV-col11 Origami v3"
    foldername, parentdirpath, localdir = e._getFoldernameAndParentdirpath(localtestdir)
    logger.debug("foldername, parentdirpath, localdir = %s, %s, %s", foldername, parentdirpath, localdir)
    assert foldername == localtestdir
    assert parentdirpath == TESTDATADIR
    assert os.path.join(parentdirpath, foldername) == localdir

    # Test 2: cwd based (via os.path.abspath)
    monkeypatch.setattr(e.Confighandler, 'get', lambda key: "/tmp/config")
    monkeypatch.setattr(os.path, 'abspath', lambda path: os.path.join(TESTDATADIR, localdir))
    foldername, parentdirpath, localdir = e._getFoldernameAndParentdirpath(localtestdir)
    logger.debug("foldername, parentdirpath, localdir = %s, %s, %s", foldername, parentdirpath, localdir)
    assert foldername == localtestdir
    assert parentdirpath == TESTDATADIR

    # Test 3: Parentdirpath based
    #monkeypatch.setattr(e.Confighandler, 'get', lambda key: "/tmp")
    monkeypatch.setattr(os.path, 'abspath', lambda path: "/tmp/abspath")
    e.Parentdirpath = TESTDATADIR
    foldername, parentdirpath, localdir = e._getFoldernameAndParentdirpath(localtestdir)
    logger.debug("foldername, parentdirpath, localdir = %s, %s, %s", foldername, parentdirpath, localdir)
    assert foldername == localtestdir
    assert parentdirpath == TESTDATADIR

    # Test 4: All fails -- should rely on exp_root_subDir from config.
    #monkeypatch.setattr(e.Confighandler, 'get', lambda key: "/tmp")
    #monkeypatch.setattr(os.path, 'abspath', lambda path: "/tmp")
    e.Parentdirpath = '/tmp/pardirpath'
    foldername, parentdirpath, localdir = e._getFoldernameAndParentdirpath(localtestdir)
    logger.debug("foldername, parentdirpath, localdir = %s, %s, %s", foldername, parentdirpath, localdir)
    assert foldername == localtestdir
    assert parentdirpath == '/tmp/config'



def test_experiment_basics(exp_no_wikipage_or_subentries, expprops):
    """
    This test case has the following assumptions:
    * No ExperimentManager is available to the experiment
    * No Server is available.
    * No wikipage has been attached.
    * No subentries has been loaded.
    Basic test, since it cannot interact with a manager, wikipage or server, and
    only receives faked responses from FakeConfighandler.
    """
    e = exp_no_wikipage_or_subentries
    sub_regex = r'(?P<expid>RS[0-9]{3})-?(?P<subentry_idx>[^_ ])[_ ]+(?P<subentry_titledesc>.+?)\s*(\((?P<date2>[0-9]{8})\))?$'
    e.setConfigEntry('exp_subentry_regex', sub_regex)

    assert e.getConfigEntry('exp_subentry_regex') == sub_regex
    assert e.Props == expprops
    assert e.Subentries == OrderedDict()
    assert e.Expid == expprops['expid']
    assert e.Wiki_pagetitle == None
    assert e.PageId == None
    assert e.Attachments == list()
    assert e.Server == None
    assert e.Manager == None
    assert e.WikiPage == None
    assert e.Fileshistory == dict()
    assert e.Subentries_regex_prog == re.compile(sub_regex)
    assert e.Status == None
    assert e.isactive() == False
    assert e.isrecent() == False
    assert e.getUrl() == None

    assert e.archive() == None  # should return None when no experimentmanager is available.
    assert e.saveAll() == None  # Currently lways returns None, subject to change.

    #assert e.getAbsPath() == None
    assert e.saveIfChanged() == None
    assert e.saveProps() == False # No localdir defined, so should return False.



def test_getFoldernameFromFmtAndProps(exp_no_wikipage_or_subentries, expprops):
    e = exp_no_wikipage_or_subentries
    assert e.getFoldernameFromFmtAndProps() == 'RS099 Pytest titledesc'


def test_parseSubentriesFromWikipage(exp_no_wikipage_or_subentries, exppropsRS189):
    """
    parseSubentriesFromWikipage
    """
    e = exp_no_wikipage_or_subentries
    e.Props.update(exppropsRS189)
    wiki_experiment_section = r'(?P<experiment_info>.*?)(?P<exp_section_header><h2>Experimental section</h2>)(?P<exp_section_body>.*?)(?=<h[1-2]>.+?</h[1-2]>|\Z)'
    wiki_subentry_regex_fmt = r'(<h4>{expid}[_-]*{subentry_idx}\s+(?P<subentry_titledesc>.+?)\s*(\((?P<subentry_date_string>\d{{8}})\))?</h4>)(?P<subentry_xhtml>.*?)(?=<h[1-4]>.+?</h[1-4]>|\Z)'
    e.setConfigEntry('wiki_experiment_section', wiki_experiment_section)
    e.setConfigEntry('wiki_subentry_regex_fmt', wiki_subentry_regex_fmt)
    wiki_subentries = e.parseSubentriesFromWikipage(xhtml=pagexhtml1)
    assert wiki_subentries == pagexhtml1_expectedprops




@pytest.mark.skipif(True, reason="Not ready yet")
def test_setLocaldirpathAndFoldername():
    assert False

@pytest.mark.skipif(True, reason="Not ready yet")
def test__getFoldernameAndParentdirpath():
    assert False

@pytest.mark.skipif(True, reason="Not ready yet")
def test_makeLocaldir():
    assert False

@pytest.mark.skipif(True, reason="Not ready yet")
def test_changeLocaldir():
    assert False



@pytest.mark.skipif(True, reason="Not ready yet")
def test_saveProps(e=None):
    if not e:
        e = setup1()
    e.Props['test_key'] = datetime.now().strftime("%Y%m%d-%H%M%S") # you can use strptime to parse a formatted date string, or you can use "{:%Y%m%d-%H%M%S}".format(datetime)
    print "\n\nSaving props:"
    e.saveProps()
    return e

"""
Wiki page tests:
"""
@pytest.mark.skipif(True, reason="Not ready yet")
def test_attachWikiPage(e=None):
    if not e:
        e = setup1()
    if e.WikiPage:
        print "\nPage already attached: {}".format(e.WikiPage)
    else:
        e.attachWikiPage(dosearch=True)
        print "\nPage attached: {}".format(e.WikiPage)
    return e

@pytest.mark.skipif(True, reason="Not ready yet")
def test_makeNewWikiPage(e=None):
    if not e:
        e = setup1()
    pagestruct = e.WikiPage or e.attachWikiPage(dosearch=True)
    if not pagestruct:
        print "e.WikiPage, before: {}".format(e.WikiPage)
        e.makeWikiPage()
        print "e.WikiPage, after: {}".format(e.WikiPage)
    return e


"""
Subentry-related tests:
"""
@pytest.mark.skipif(True, reason="Not ready yet")
def test_addNewSubentry(e=None, subentry_idx=None):
    if not e:
        e = setup1()
    if not subentry_idx:
        subentry_idx = e.getNewSubentryIdx()
    e.addNewSubentry(subentry_titledesc="AFM of RS102e TR")
    return e

@pytest.mark.skipif(True, reason="Not ready yet")
def test_addNewSubentry2(e=None, subentry_idx=None):
    if not e:
        e = setup1()
    if not subentry_idx:
        subentry_idx = e.getNewSubentryIdx()
    e.addNewSubentry(subentry_titledesc="Strep NHS-N3 activation", subentry_idx='a', subentry_date="20130103")
    return e

@pytest.mark.skipif(True, reason="Not ready yet")
def test_addNewSubentry3(e=None, subentry_idx=None):
    if not e:
        e = setup1()
    if not subentry_idx:
        subentry_idx = e.getNewSubentryIdx()
    e.addNewSubentry(subentry_titledesc="Strep-N3 DBCO-dUTP conj", subentry_idx='b', subentry_date="20130103", makefolder=True, makewikientry=True)
    return e

@pytest.mark.skipif(True, reason="Not ready yet")
def test_addNewSubentry4(e=None, subentry_idx=None):
    if not e:
        e = setup1()
    if not subentry_idx:
        subentry_idx = e.getNewSubentryIdx()
    e.addNewSubentry(subentry_titledesc="Amicon pur and UV quant of Strep-ddUTP", subentry_idx='c', subentry_date="20130104", makefolder=True, makewikientry=True)
    return e

@pytest.mark.skipif(True, reason="Not ready yet")
def test_makeSubentryFolder(e=None, subentry_idx=None):
    if not e:
        e = setup1()
    if not subentry_idx:
        subentry_idx = e.getNewSubentryIdx()
    e.makeSubentryFolder(subentry_idx='a')
    return e

@pytest.mark.skipif(True, reason="Not ready yet")
def test_makeNewWikiSubentry(e=None, subentry_idx=None):
    if not e:
        e = setup1()
    if not subentry_idx:
        subentry_idx = e.getNewSubentryIdx()
    res = e.makeWikiSubentry(subentry_idx)
    print "\nResult of makeWikiSubentry() :\n{}".format(res)
    return e

@pytest.mark.skipif(True, reason="Not ready yet")
def test_getLocalFilelist(e=None):
    print "\n>>>>>>>>>>>>>> test_getLocalFilelist() started >>>>>>>>>>>>>"
    if not e:
        e = setup1(useserver=False)
    print "All local files in exp.Localdirpath: {}".format(e.Localdirpath)
    # oneliner for listing files with os.walk:
    print "\n".join("{}:\n{}".format(dirpath,
            "\n".join(os.path.join(dirpath, filename) for filename in filenames))for dirpath,dirnames,filenames in os.walk(e.Localdirpath) )
    print "\nGetting all local files: e.getLocalFilelist(subentries_only=False)"
    flist = e.getLocalFilelist(subentries_only=False)
    print "\n".join("{}: {}".format(*itm) for itm in flist)
    print "\nGetting all local files matching *.png: e.getLocalFilelist(subentries_only=False, fn_pattern='*.png')"
    flist = e.getLocalFilelist(subentries_only=False, fn_pattern='*.png')
    print "\n".join("{}: {}".format(*itm) for itm in flist)
    print "\nGetting all local files matching r'.*\.dxml': e.getLocalFilelist(subentries_only=False, fn_pattern=r'.*\.dxml', fn_is_regex='regex')"
    flist = e.getLocalFilelist(subentries_only=False, fn_pattern=r'.*\.dxml', fn_is_regex='regex')
    print "\n".join("{}: {}".format(*itm) for itm in flist)
    print "\nGetting subentry files: e.getLocalFilelist(subentries_only=True, relative='filename-only')"
    flist = e.getLocalFilelist(subentries_only=True, relative='filename-only')
    print "\n".join("{}: {}".format(*itm) for itm in flist)
    print "\nGetting files for subentry 'f': e.getLocalFilelist(subentry_idxs=('f',))"
    flist = e.getLocalFilelist(subentry_idxs=('f',))
    print "\n".join("{}: {}".format(*itm) for itm in flist)
    print "\nGetting subentry files matching *.png: e.getLocalFilelist(subentries_only=True, fn_pattern='*.png')"
    flist = e.getLocalFilelist(subentries_only=True, fn_pattern='*.png')
    print "\n".join("{}: {}".format(*itm) for itm in flist)
    print "<<<<<<<<<<<<<< test_getLocalFilelist() finished <<<<<<<<<<<<"
    return e

@pytest.mark.skipif(True, reason="Not ready yet")
def test_getRepr(e=None):
    print "\n>>>>>>>>>>>>>> test_getRept() started >>>>>>>>>>>>>"
    if not e:
        e = setup1(useserver=False)
    print "e.getExpRepr():"
    print e.getExpRepr()
    print "e.getExpRepr(default='WOOORD'):"
    print e.getExpRepr(default='WOOORD')
    print "e.getSubentryRepr():"
    print e.getSubentryRepr()
    print "e.getSubentryRepr(subentry_idx='a'):"
    print e.getSubentryRepr(subentry_idx='a')
    print "e.getSubentryRepr(subentry_idx='a', default='exp'):"
    print e.getSubentryRepr(subentry_idx='a', default='exp')
    print "e.getSubentryRepr(subentry_idx='a', default='What, no a?'):"
    print e.getSubentryRepr(subentry_idx='a', default='What, no a?')
    print "e.getSubentryRepr(subentry_idx='z', default='What, no z?'):"
    print e.getSubentryRepr(subentry_idx='z', default='What, no z?')
    print "e.getSubentryRepr(subentry_idx='z', default='exp'):"
    print e.getSubentryRepr(subentry_idx='z', default='exp')
    print "e.getSubentryRepr(subentry_idx=None, default='exp'):"
    print e.getSubentryRepr(subentry_idx=None, default='exp')
    print "e.getSubentryRepr(default='exp'):"
    print e.getSubentryRepr(default='exp')
    print "e.getSubentryRepr(default='WWWRRR Default'):"
    print e.getSubentryRepr(default='WWWRRR Default')
    print "e.getSubentryRepr():"
    print e.getSubentryRepr()
    print "<<<<<<<<<<<<<< test_getRepr() finished <<<<<<<<<<<<"


@pytest.mark.skipif(True, reason="Not ready yet")
def test_getWikiSubentryXhtml(e=None):
    print "\n>>>>>>>>>>>>>> test_getWikiSubentryXhtml() started >>>>>>>>>>>>>"
    if not e:
        e = setup1()
        e.attachWikiPage()
    print "\n\n"
    print e.Server
    for s in ('a',):#'b','c','e'):
        print "\nFor subentry '{}':".format(s)
        e.getWikiSubentryXhtml(s)
    #print "\nInvoked without subentry:"
    #e.getWikiSubentryXhtml()
    print "\n<<<<<<<<<<<<<< test_getWikiSubentryXhtml() finished <<<<<<<<<<<<"
    return e
