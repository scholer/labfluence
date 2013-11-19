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



from model.page import WikiPage, WikiPageFactory
from model.experiment import Experiment
from model.experiment_manager import ExperimentManager
#from model.confighandler import ExpConfigHandler
#from model.server import ConfluenceXmlRpcServer


## Test doubles:
from tests.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
from tests.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer



import sys
import time
start = time.clock()
def report():
    print "Clock: {}".format(time.clock()-start)

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


def setup1():
    confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    em = ExperimentManager(confighandler=confighandler, VERBOSE=1)
    return em, confighandler

def setup2():
    confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
    em = ExperimentManager(confighandler=confighandler, VERBOSE=1)
    server = ConfluenceXmlRpcServer(autologin=True, ui=None, confighandler=confighandler, VERBOSE=0)
    confighandler.Singletons['server'] = server
    return em, confighandler, server


def test_getLocalExperiments(store=True):
    em, ch = setup1()
    exps = em.getLocalExperiments(store=store)
    print "Experiments:"
    print "\n".join( "{exp.Foldername} : props={exp.Props}".format(exp=exp) for exp in exps )
    return em, exps

def test_makeExperimentsByIdMap(em=None):
    exps = None
    if em is None:
        #em, ch = setup1()
        em, exps = test_getLocalExperiments()
    print "len(exps): {}".format(len(exps) if exps else 'None')
    print "\ntest_makeExperimentsByIdMap: invoking em.makeExperimentByExpIdMap"
    expbyid = em.makeExperimentByExpIdMap(exps, updateSelf=True)
    print "len(em.ExperimentsById) = {}".format(len(em.ExperimentsById))
    print "\n".join( "{} : {}".format(expid, exp.Props.get('exp_titledesc')) for expid, exp in sorted(expbyid.items()) )
    return em, expbyid

def test_getExperimentsIndices(em=None):
    if em is None:
        print "\n\nMaking new experimentmanager and confighandler...:"
        em, ch = setup1()
    #em.makeExperimentByExpIdMap()
    print "\ntest_getExperimentsIndices: invoking em.getExperimentsIndices() "
    indices = em.getExperimentsIndices()
    print "\nExperiment indices:"
    print indices

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

def test_getServerInfo(em=None):
    print "\n\n >>>>>>>>>>>>>>>> test_getCurrentWikiExperiments() >>>>>>>>>>>>> \n"
    if em is None:
        em, ch, server = setup2()
    print "Server info: {}".format(em.getServerInfo )
    print "\n<<<<< finished test_getCurrentWikiExperiments() <<<<<<<<<<<< \n"
    return em, ch


#em = None
#em, exps = test_getLocalExperiments()
#report()
#em, expbyid = test_makeExperimentsByIdMap(em)
#report()
#test_getExperimentsIndices(em)
test_getServerInfo()
report()
#test_getCurrentWikiExperiments()
report()
