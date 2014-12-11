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
# pylint: disable-msg=C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221,E1101,W0402,E0202,W0201
# pylint: disable-msg=C0111,W0613,W0621,W0612,W0212

import pytest
import os
import time
import tempfile
import inspect
from collections import OrderedDict
start = time.clock()
def report():
    print "Clock: {}".format(time.clock()-start)

import logging
logger = logging.getLogger(__name__)

# Note: Switched to using pytest-capturelog, captures logging messages automatically...
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
#logging.getLogger("__main__").setLevel(logging.DEBUG)
#logging.getLogger(__name__).setLevel(logging.DEBUG)
#logging.getLogger("model.model_testdoubles.fake_confighandler").setLevel(logging.DEBUG)
#logging.getLogger("model.experimentmanager").setLevel(logging.DEBUG)
#logging.getLogger("model.experiment").setLevel(logging.DEBUG)
#logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
#logfmt = "%(levelname)s:%(name)s: %(funcName)s() :: %(message)s"
#logging.basicConfig(filename='/tmp/test.log', level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(funcName)s |%(message)s')
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(funcName)s |%(message)s')
#logging.basicConfig(level=logging.INFO, format=logfmt)
#logging.getLogger("views.expjournalframe").setLevel(logging.DEBUG)
#logging.getLogger("views.shared_ui_utils").setLevel(logging.DEBUG)
#logging.getLogger("views.explistboxes").setLevel(logging.DEBUG)
#logging.getLogger("model.journalassistant").setLevel(logging.DEBUG)
#logging.getLogger("model.experiment").setLevel(logging.DEBUG)
#logging.getLogger("model.experiment_manager").setLevel(logging.DEBUG)
#logging.getLogger("__main__").setLevel(logging.DEBUG)



#from model.page import WikiPage, WikiPageFactory
#from model.experiment import Experiment
from model.experimentmanager import ExperimentManager


## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
FakeConfighandler = ExpConfigHandler
from model.model_testdoubles.fake_server import FakeConfluenceServer
FakeConfluenceServer = FakeConfluenceServer



@pytest.fixture()
def tempfiledir():
    newpath = tempfile.mkdtemp() # Returns path to new temp directory, e.g. /tmp/tmpQ938Rj
    return newpath

@pytest.fixture()
def tempfilefile():
    _, newpath = tempfile.mkstemp() # returns (filenumber, filepath)
    #newpath = tempfile.TemporaryFile() # returns an open file handle
    return newpath


@pytest.fixture
def fakeconfighandler(monkeypatch):
    ch = FakeConfighandler(pathscheme='test1')
    testdir = os.path.join(os.getcwd(), 'tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup')
    monkeypatch.setattr(ch, 'getConfigDir', lambda x: testdir)
    return ch


@pytest.fixture
def experimentmanager_with_confighandler(monkeypatch, fakeconfighandler):
    confighandler = fakeconfighandler
    em = ExperimentManager(confighandler=confighandler)
    return em

@pytest.fixture
def em_with_ch_localexpparsing_disabled(monkeypatch, fakeconfighandler):
    confighandler = fakeconfighandler
    em = ExperimentManager(confighandler=confighandler)
    return em


@pytest.fixture
def em_with_ch_and_autoloaded_exps(fakeconfighandler):
    confighandler = fakeconfighandler
    em = ExperimentManager(confighandler=confighandler)
    return em


@pytest.fixture
def em_with_ch_with_fakeserver():
    confighandler = ExpConfigHandler(pathscheme='test1')
    server = FakeConfluenceServer(autologin=True, ui=None, confighandler=confighandler)
    confighandler.Singletons['server'] = server
    em = ExperimentManager(confighandler=confighandler)
    return em, confighandler, server

def test_basics(experimentmanager_with_confighandler):
    pass


@pytest.fixture
def em_with_fake_ch_and_patched_server(monkeypatch):
    """
    Returns
        em, confighandler, server
    where em is an experimentmanager with
    fake confighandler and fake server,
    and where the fake server has patched:
    - getChildren
    """
    confighandler = ExpConfigHandler(pathscheme='test1')
    server = FakeConfluenceServer(autologin=True, ui=None, confighandler=confighandler)
    confighandler.Singletons['server'] = server
    em = ExperimentManager(confighandler=confighandler)
    def test_pagesummaries(self):
        summaries = [
            {'id':'01', 'space':'~scholer', 'parentId':'524296', 'title':'RS001 Testpage01', 'url':None, 'permissions':0},
            {'id':'02', 'space':'~scholer', 'parentId':'524296', 'title':'Testpage02', 'url':None, 'permissions':0},
            {'id':'03', 'space':'~scholer', 'parentId':'524296', 'title':'RS003 Testpage03', 'url':None, 'permissions':0},
        ]
        return summaries
    monkeypatch.setattr(server, 'getChildren', test_pagesummaries)
    return em, confighandler, server


def test_genLocalExperiments(experimentmanager_with_confighandler):
    """
    If this fails, ask someone to email you test_filestructure.zip
    This isn't optimal, but works for now. It will be cleaned up if someone needs it.
    """
    em = experimentmanager_with_confighandler
    expdir = os.path.join(os.getcwd(), 'tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup', '2013_Aarhus')
    assert em.getLocalExpSubDir() == expdir
    exps = em.genLocalExperiments()  # Store is deprechated...
    print "Experiments:"
    print "\n".join( "{exp.Foldername} : props={exp.Props}".format(exp=exp) for exp in exps )
    assert isinstance(exps, list) or inspect.isgenerator(exps)
    expbyidmap = em.ExperimentsById
    assert isinstance(expbyidmap, dict)
    assert em.Server == None
    aexpids = ['RS102', 'RS134', 'RS135']
    rexpids = ['RS103']
    assert em.ActiveExperimentIds == aexpids
    assert em.RecentExperimentIds == rexpids
    assert isinstance(em.ActiveExperiments, list)
    assert len(em.ActiveExperiments) == len(aexpids)
    assert isinstance(em.RecentExperiments, list)
    assert len(em.RecentExperiments) == len(rexpids)





def test_mergeLocalExperiments(em_with_fake_ch_and_patched_server, monkeypatch, tempfiledir):
    """
    First checks that mergeCurrentWikiExperiments works, and then that
    it can also create a new experiment localdir based on the results.
    """
    print "\n\ntempfiledir: %s" % tempfiledir
    em, ch, server = em_with_fake_ch_and_patched_server
    # Modify local_exp_subDir:
    ch.setkey('local_exp_subDir', tempfiledir)
    logger.debug("ch.get('local_exp_subDir'): %s", ch.get('local_exp_subDir'))

    # Create test folders:
    for i, texpid in enumerate(('RS001', 'X002', 'RS003', '', 'RS005'), 1):
        os.mkdir(os.path.join(tempfiledir, " ".join( (texpid, "Test experiment {}".format(i)) )) )


    # getLocalExperimentFolderpaths
    assert set(em.getLocalExperimentFolderpaths()) == {os.path.join(tempfiledir, " ".join( (texpid, "Test experiment {}".format(i)) ))
                                                  for i, texpid in enumerate(('RS001', 'X002', 'RS003', '', 'RS005'), 1)}

    # getLocalExpsDirMatchTuples
    dmtups = em.getLocalExpsDirMatchTuples()
    tup = dmtups.next()
    assert tup[0] == os.path.join(tempfiledir, 'RS001 Test experiment 1')
    del dmtups

    # getLocalExpsDirGroupdictTuples
    dgtups = em.getLocalExpsDirGroupdictTuples()
    tup = dgtups.next()
    assert tup[0] == os.path.join(tempfiledir, 'RS001 Test experiment 1')
    assert tup[1] == dict(expid='RS001', exp_titledesc='Test experiment 1', date=None)

    # mergeLocalExperiments
    assert em._experimentsbyid == None # No init -- should be None..
    em.mergeLocalExperiments()
    assert em.ExperimentsById.keys() == ['RS001', 'RS003', 'RS005']
    assert em.ExperimentsById['RS001'].Localdirpath == os.path.join(tempfiledir, 'RS001 Test experiment 1')

    # Create new experiment:
    os.mkdir(os.path.join(tempfiledir, "RS007 Test experiment 7" ))
    em.mergeLocalExperiments(addtoactive=True)
    assert em.ExperimentsById['RS007'].Localdirpath == os.path.join(tempfiledir, "RS007 Test experiment 7")
    assert 'RS007' in em.ActiveExperimentIds





#########################
## WIKI-RELATED TESTS ###
#########################


def test_getExpRootWikiPages(em_with_fake_ch_and_patched_server):
    em, ch, server = em_with_fake_ch_and_patched_server
    #expdir = os.path.join(os.getcwd(), 'tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup', '2013_Aarhus')
    wikipages = em.getExpRootWikiPages()
    assert isinstance(wikipages, list)
    assert len(wikipages) == 3
    assert wikipages[0]['id'] == '01'


def test_getCurrentWikiExpsPageMatchTuples(em_with_fake_ch_and_patched_server):
    """
    Returns a generator with
         (page, title regex match) tuples
    """
    em, ch, server = em_with_fake_ch_and_patched_server
    pagematchgen = em.getCurrentWikiExpsPageMatchTuples()
    page1, match1 = next(pagematchgen)
    assert page1['id'] == '01'
    assert match1.groupdict()['expid'] == 'RS001'
    page, match = next(pagematchgen)
    # page 02 should NOT match.
    assert page['id'] == '03'
    assert match.groupdict()['expid'] == 'RS003'


def test_getCurrentWikiExpsPageGroupdictTuples(em_with_fake_ch_and_patched_server):
    """
    Returns a generator with
         (page, title_regex_match.groupdict() ) tuples
    """
    em, ch, server = em_with_fake_ch_and_patched_server
    pagematchgen = em.getCurrentWikiExpsPageGroupdictTuples()
    page, gd = next(pagematchgen)
    assert page['id'] == '01'
    assert gd['expid'] == 'RS001'
    page, gd = next(pagematchgen)
    # page 02 should NOT match.
    assert page['id'] == '03'
    assert gd['expid'] == 'RS003'


@pytest.mark.skipif(True, reason="Not ready yet")
def test_getCurrentWikiExperiments():
    assert False


def test_mergeCurrentWikiExperiments(em_with_fake_ch_and_patched_server, monkeypatch, tempfiledir):
    """
    First checks that mergeCurrentWikiExperiments works, and then that
    it can also create a new experiment localdir based on the results.
    """
    em, ch, server = em_with_fake_ch_and_patched_server
    # Modify local_exp_subDir:
    ch.setkey('local_exp_subDir', tempfiledir)
    logger.debug("ch.get('local_exp_subDir'): %s", ch.get('local_exp_subDir'))
    # Monkeypatch em.genLocalExperiments() and em.makeExperimentByExpIdMap:
    monkeypatch.setattr(em, 'genLocalExperiments', lambda *x: list() )
    monkeypatch.setattr(em, 'mergeLocalExperiments', lambda *x: list() )
    def makeExperimentByExpIdMap_patch(exps, updateSelf=True):
        return OrderedDict()
    monkeypatch.setattr(em, 'makeExperimentByExpIdMap', makeExperimentByExpIdMap_patch )
    assert em.ExperimentsById == None # or OrderedDict() # Empty dict
    em.mergeCurrentWikiExperiments(autocreatelocaldirs=False)
    assert 'RS001' in em.ExperimentsById
    assert em.ExperimentsById['RS001'].PageId == '1' # '01' should be converted to '1' after str(int(pageid)) conversions.

    ## SECOND, test with autocreatelocaldirs=True
    def test_pagesummaries(self):
        summaries = [
            {'id':'01', 'space':'~scholer', 'parentId':'524296', 'title':'RS001 Testpage01', 'url':None, 'permissions':0},
            {'id':'02', 'space':'~scholer', 'parentId':'524296', 'title':'Testpage02', 'url':None, 'permissions':0},
            {'id':'03', 'space':'~scholer', 'parentId':'524296', 'title':'RS003 Testpage03', 'url':None, 'permissions':0},
            {'id':'04', 'space':'~scholer', 'parentId':'524296', 'title':'RS004 Testpage04', 'url':None, 'permissions':0},
        ]
        return summaries
    monkeypatch.setattr(server, 'getChildren', test_pagesummaries)
    em._localexpdirsparsed = True # Act like the local dirs have been parsed.
    # If this is not set, then (as a precaution) em.mergeCurrentWikiExperiments will reset autocreatelocaldirs to False.
    em.mergeCurrentWikiExperiments(autocreatelocaldirs=True) # Defaults to app_autocreatelocalexpdirsfromwikiexps or False
    assert em.ExperimentsById['RS004'].PageId == '4'
    print "\n\ntempfiledir: %s" % tempfiledir
    assert os.listdir(tempfiledir) == ['RS004 Testpage04']


def test_getExperimentsIndices(experimentmanager_with_confighandler):
    em = experimentmanager_with_confighandler
    print "\ntest_getExperimentsIndices: invoking em.getExperimentsIndices() "
    em._experimentsbyid = dict(RS001='Test page 01', RS003='Test page 03')
    indices = em.getExperimentsIndices()
    assert indices == [1, 3]



@pytest.mark.skipif(True, reason="Not ready yet")
def test_():
    assert False


@pytest.mark.skipif(True, reason="Not ready yet")
def test_makeExperimentsByIdMap(experimentmanager_with_confighandler):
    exps = None
    em = experimentmanager_with_confighandler
    exps = em.genLocalExperiments()
    print "len(exps): {}".format(len(exps) if exps else 'None')
    print "\ntest_makeExperimentsByIdMap: invoking em.makeExperimentByExpIdMap"
    expbyid = em.makeExperimentByExpIdMap(exps, updateSelf=True)
    print "len(em.ExperimentsById) = {}".format(len(em.ExperimentsById))
    print "\n".join( "{} : {}".format(expid, exp.Props.get('exp_titledesc')) for expid, exp in sorted(expbyid.items()) )


@pytest.mark.skipif(True, reason="Not ready yet")
def test_getCurrentWikiExperiments2(em_with_fake_ch_and_patched_server):
    # testing def getCurrentWikiExperiments(self, ret='page-structs', useCache=True, store=None):
    print "\n\n >>>>>>>>>>>>>>>> test_getCurrentWikiExperiments() >>>>>>>>>>>>> \n"
    em, ch, server = em_with_fake_ch_and_patched_server
    rets = ('expriment-object', 'pagestruct', 'regex-match', 'groupdict', 'expid', 'tuple', 'display-tuple')
    for r in rets:
        print "\n\nTesting ExperimentManager.getCurrentWikiExperiments(ret={})".format(r)
        exps = em.getCurrentWikiExperiments(ret=r)
        print "Experiments:\n"+"\n".join( "- {:70}".format(e) for e in exps)
    print "\n<<<<< finished test_getCurrentWikiExperiments() <<<<<<<<<<<< \n"


def test_ServerInfo(em_with_ch_with_fakeserver):
    em, ch, server = em_with_ch_with_fakeserver
    print "Server info: {}".format(em.ServerInfo)
    assert em.ServerInfo['developmentBuild'] == 'false'
