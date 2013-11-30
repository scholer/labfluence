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
# pylint: disable-msg=C0111,W0613,W0621




from model.experiment import Experiment

## Test doubles:
from tests.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
from tests.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer

## Also consider mocking all other objects not part of the SUT (system under test, i.e. the Experiment class)
# In addition to server and confighandler, this includes:
# - WikiPage and WikiPageFactory
# - JournalAssistant
# - ExperimentManager

from collections import OrderedDict
import re
import pytest
import logging
logger = logging.getLogger(__name__)
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)



@pytest.fixture
def expprops():
    expprops = dict(expid='RS099', exp_titledesc="Pytest titledesc", exp_subentries=OrderedDict())
    return expprops



@pytest.fixture
def exp_no_wikipage_or_subentries(expprops):
    confighandler = ExpConfigHandler( pathscheme='test1' )
    experiment = Experiment(confighandler=confighandler,
                            props=expprops,
                            autoattachwikipage=False,
                            doparseLocaldirSubentries=False)
    return experiment
#
#
#def setup1(useserver=True):
#    confighandler = ExpConfigHandler( pathscheme='test1', VERBOSE=1 )
#    #em = ExperimentManager(confighandler=confighandler, VERBOSE=1)
#    print "----"
#    rootdir = confighandler.get("local_exp_subDir")
#    print "rootdir: {}".format(rootdir)
#    print "glob res: {}".format(glob.glob(os.path.join(rootdir, r'RS102*')) )
#    ldir = os.path.join(rootdir, glob.glob(os.path.join(rootdir, r'RS102*'))[0] )
#    print "ldir: {}".format(ldir)
#    ldir2 = os.path.join(rootdir, glob.glob(os.path.join(rootdir, "RS105*"))[0] )
#    ldir3 = os.path.join(rootdir, glob.glob(os.path.join(rootdir, "RS177*"))[0] )
#    print "ldir2: {}".format(ldir2)
#    ldir = ldir2
#    #ldir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
##                '/home/scholer/Documents/labfluence_data_testsetup/.labfluence
#    #ldir2 = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS105 TR STV-col11 Origami v3":
#    server = ConfluenceXmlRpcServer(confighandler=confighandler, VERBOSE=4, autologin=True) if useserver else None
#    e = Experiment(confighandler=confighandler, server=server, localdir=ldir, VERBOSE=10)
#    return e

# You cannot import or use ExprimentManager here due to circular imports.
# You will need to create a separate test environment for that.
#def setup2():
#    confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
#    em = ExperimentManager(confighandler=confighandler, VERBOSE=1, autoinit=False)
#    server = ConfluenceXmlRpcServer(autologin=True, ui=None, confighandler=confighandler, VERBOSE=0)
#    confighandler.Singletons['server'] = server
#    rootdir = confighandler.get("local_exp_subDir")
#    print "experiment rootdir: {}".format(rootdir)
#    print "glob res for RS102: {}".format(glob.glob(os.path.join(rootdir, r'RS102*')) )
#    ldir = os.path.join(rootdir, glob.glob(os.path.join(rootdir, r'RS102*'))[0] )
#    e = Experiment(confighandler=confighandler, server=server, localdir=ldir, manager=em, VERBOSE=10)
#    return e


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





def test_setLocaldirpathAndFoldername():
    assert False

def test__getFoldernameAndParentdirpath():
    assert False

def test_makeLocaldir():
    assert False

def test_changeLocaldir():
    assert False

def test_():
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

@pytest.mark.skipif(True, reason="Not ready yet")
def test_parseSubentriesFromWikipage(e=None):
    print "\n>>>>>>>>>>>>>> test_getWikiSubentryXhtml() started >>>>>>>>>>>>>"
    if not e:
        e = setup1()
        wikipage = e.attachWikiPage()
    print "\n\n"
    print e.Server
    print "wikipage: {}".format(wikipage)
    wiki_subentries = e.parseSubentriesFromWikipage(wikipage)
    print "wiki_subentries:"
    print wiki_subentries
    #print "\nInvoked without subentry:"
    #e.getWikiSubentryXhtml()
    print "\n<<<<<<<<<<<<<< test_getWikiSubentryXhtml() finished <<<<<<<<<<<<"
    return e
