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
# pylint: disable-msg=C0111,W0613,W0621

import pytest
import os
import time
start = time.clock()
def report():
    print "Clock: {}".format(time.clock()-start)

import logging
logger = logging.getLogger(__name__)
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)
logging.getLogger("tests.model_testdoubles.fake_confighandler").setLevel(logging.DEBUG)
logging.getLogger("model.experimentmanager").setLevel(logging.DEBUG)
logging.getLogger("model.experiment").setLevel(logging.DEBUG)



#from model.page import WikiPage, WikiPageFactory
#from model.experiment import Experiment
from model.experimentmanager import ExperimentManager


## Test doubles:
from tests.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
FakeConfighandler = ExpConfigHandler
from tests.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer

logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
#logfmt = "%(levelname)s:%(name)s: %(funcName)s() :: %(message)s"

#logging.basicConfig(filename='/tmp/test.log', level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(funcName)s |%(message)s')
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(funcName)s |%(message)s')
logging.basicConfig(level=logging.INFO, format=logfmt)

#logging.getLogger("views.expjournalframe").setLevel(logging.DEBUG)
#logging.getLogger("views.shared_ui_utils").setLevel(logging.DEBUG)
#logging.getLogger("views.explistboxes").setLevel(logging.DEBUG)
#logging.getLogger("model.journalassistant").setLevel(logging.DEBUG)
#logging.getLogger("model.experiment").setLevel(logging.DEBUG)
#logging.getLogger("model.experiment_manager").setLevel(logging.DEBUG)
#logging.getLogger("__main__").setLevel(logging.DEBUG)


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
    server = ConfluenceXmlRpcServer(autologin=True, ui=None, confighandler=confighandler, VERBOSE=0)
    confighandler.Singletons['server'] = server
    em = ExperimentManager(confighandler=confighandler)
    return em, confighandler, server



def test_getLocalExperiments(experimentmanager_with_confighandler):
    em = experimentmanager_with_confighandler
    expdir = os.path.join(os.getcwd(), 'tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup', '2013_Aarhus')
    assert em.getLocalExpSubDir() == expdir
    exps = em.getLocalExperiments(store=True)  # Store just specifies whether to remember the parsed experiments.
    print "Experiments:"
    print "\n".join( "{exp.Foldername} : props={exp.Props}".format(exp=exp) for exp in exps )
    assert isinstance(exps, list)
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





@pytest.mark.skipif(True, reason="Not ready yet")
def test_makeExperimentsByIdMap(experimentmanager_with_confighandler):
    exps = None
    em = experimentmanager_with_confighandler
    exps = em.getLocalExperiments(store=False)
    print "len(exps): {}".format(len(exps) if exps else 'None')
    print "\ntest_makeExperimentsByIdMap: invoking em.makeExperimentByExpIdMap"
    expbyid = em.makeExperimentByExpIdMap(exps, updateSelf=True)
    print "len(em.ExperimentsById) = {}".format(len(em.ExperimentsById))
    print "\n".join( "{} : {}".format(expid, exp.Props.get('exp_titledesc')) for expid, exp in sorted(expbyid.items()) )


@pytest.mark.skipif(True, reason="Not ready yet")
def test_getExperimentsIndices(em=None):
    if em is None:
        print "\n\nMaking new experimentmanager and confighandler...:"
        em, ch = setup1()
    #em.makeExperimentByExpIdMap()
    print "\ntest_getExperimentsIndices: invoking em.getExperimentsIndices() "
    indices = em.getExperimentsIndices()
    print "\nExperiment indices:"
    print indices

@pytest.mark.skipif(True, reason="Not ready yet")
def test_getCurrentWikiExperiments(em=None):
    # testing def getCurrentWikiExperiments(self, ret='page-structs', useCache=True, store=None):
    print "\n\n >>>>>>>>>>>>>>>> test_getCurrentWikiExperiments() >>>>>>>>>>>>> \n"
    if em is None:
        em, ch, server = setup2()
    rets = ('expriment-object', 'pagestruct', 'regex-match','groupdict','expid','tuple','display-tuple')
    for r in rets:
        print "\n\nTesting ExperimentManager.getCurrentWikiExperiments(ret={})".format(r)
        exps = em.getCurrentWikiExperiments(ret=r)
        print "Experiments:\n"+"\n".join( "- {:70}".format(e) for e in exps)

    print "\n<<<<< finished test_getCurrentWikiExperiments() <<<<<<<<<<<< \n"
    return em, ch

@pytest.mark.skipif(True, reason="Not ready yet")
def test_getServerInfo(em=None):
    print "\n\n >>>>>>>>>>>>>>>> test_getCurrentWikiExperiments() >>>>>>>>>>>>> \n"
    if em is None:
        em, ch, server = setup2()
    print "Server info: {}".format(em.getServerInfo )
    print "\n<<<<< finished test_getCurrentWikiExperiments() <<<<<<<<<<<< \n"
    return em, ch
