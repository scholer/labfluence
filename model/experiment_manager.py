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

import glob
import os
import re
import logging
from operator import attrgetter, itemgetter, methodcaller


from experiment import Experiment
from confighandler import ExpConfigHandler


class ExperimentManager(object):
    def __init__(self, confighandler, server=None, VERBOSE=0):
        self.VERBOSE = VERBOSE
        self.Confighandler = confighandler
        self.Server = server
        self.Experiments = list()
        self.ExperimentsById = dict()    # keyed as 'RS123'
        self.ExperimentsByIndex = dict() # the '123' part of RS123.
#        cfg = self.Confighandler.getConfig(what='combined')
#        self.


    """ CONFIG RELATED """

    def getConfigEntry(self, key):
        return self.Confighandler.get(key)

    def getWikiExpRootSpaceKey(self):
        return self.Confighandler.get('wiki_exp_root_spaceKey')

    def getWikiExpRootPageId(self):
        return self.Confighandler.get('wiki_exp_root_pageId')

    def getLocalExpRootDir(self):
        return self.Confighandler.get('local_exp_rootDir') # e.g. the "_experiment_data/" dir

    def getLocalExpSubDir(self):
        return self.Confighandler.get('local_exp_subDir') # E.g. the "2013_Aarhus/" dir

    def getExpSeriesRegex(self):
        return self.Confighandler.get('exp_series_regex')

    def getExpSubentryRegex(self):
        return self.Confighandler.get('exp_subentry_regex')


    def getRealLocalExpRootDir(self):
        #return os.path.join(self.Confighandler.getConfigDir('exp'), self.getLocalExpRootDir() )
        # edit: I have updated ExpConfigHandler to account for this:
        path = self.getLocalExpRootDir()
        # perhaps perform some kind of check...
        return path

    def getRealLocalExpSubDir(self):
        #return os.path.join(self.Confighandler.getConfigDir('exp'), self.getLocalExpRootDir(), self.getLocalExpSubDir() )
        # edit: I have updated ExpConfigHandler to account for this:
        return self.getLocalExpSubDir()




    def getCurrentWikiExperiments(self):
        if not self.Server:
            print "No server defined."
            logging.info("No server defined.")
            return
        wiki_pages = self.Server.getChildren(self.getWikiExpRootPageId())
        if self.VERBOSE:
            print "wiki_pages:"
            print wiki_pages
        return wiki_pages


    def getLocalExperiments(self, directory=None, store=False):
        if directory is None:
            directory = self.getRealLocalExpSubDir()
        # Consider using glob.re
        localdirs = sorted([dirname for dirname in os.listdir(directory) if os.path.isdir(os.path.abspath(os.path.join(directory, dirname) ) ) ]) #os.listdir(directory)
        if self.VERBOSE > 4:
            print "ExperimentManager.getLocalExperiments() :: searching in directory '{}'".format(directory)
            print "ExperimentManager.getLocalExperiments() :: localdirs = {}".format(localdirs)
        regex_str = self.getExpSeriesRegex()
        if self.VERBOSE > 3:
            print "Regex and localdirs:"
            print regex_str
            print localdirs
        if not regex_str:
            print "ExperimentManager.getLocalExperiments() :: ERROR, no exp_series_regex entry found in config!"
            return
        regex_prog = re.compile(regex_str)
        experiments = list()
        for localdir in localdirs:
            res = regex_prog.match(localdir)
            if self.VERBOSE > 2:
                print "{} found when testing '{}' dirname against regex '{}'".format("MATCH" if res else "No match", localdir, regex_str)
            if res:
                #props = dict(localdir=localdir)
                experiments.append(Experiment(localdir=os.path.join(directory, localdir), regex_match=res, manager=self, confighandler=self.Confighandler) )
        if store:
            self.Experiments = experiments
        return experiments


    def makeExperimentByExpIdMap(self, experiments=None, updateSelf=True):
        if experiments is None:
            experiments = self.Experiments
        elif experiments == 'local':
            experiments = self.getLocalExperiments()
        elif experiments in ('wiki-current', 'wiki'):
            experiments = self.getCurrentWikiExperiments()
        expByIdMap = self.ExperimentsById if updateSelf else dict()
        for experiment in experiments:
            expId = experiment.Props.get('expid')
            # probably do some testing if there is already an exp with this expid !
            if expId in expByIdMap:
                if experiment == expByIdMap[expId]:
                    print "Identical experiment, {}".format(expId)
                else:
                    print "WARNING: Duplicate expId '{}'".format(expId)
                    #expByIdMap[expId].update(experiment) # Not implemented; and should probably do some thorough checking before simply merging.
            else:
                expByIdMap[expId] = experiment
        return expByIdMap



    def getExperimentsIndices(self):
        regex_str = self.getConfigEntry('expid_regex')
        if not regex_str:
            print "No expid regex in config, aborting."
        print "Regex: {}".format(regex_str)
        regex_prog = re.compile(regex_str)
        def matchgroupdummy(*args):
            # Used to avoid calling .group() method of None object:
            return None
        def intConv(str_number):
            try:
                return int(str_number)
            except ValueError:
                return None
        #f = itemgetter('expid'), g = itemgetter('Props') # allows using f(g(exp)) to get exp id, but does not deal well with KeyError exceptions
        #f = methodcaller(1) # does not work, f(a) will call a.1(), not a(1)
        #return [ intConv(getattr(regex_prog(getattr(exp, 'Props', dict()).get('expid', "")), 'group', matchgroupdummy)(1)) for exp in self.Experiments ]
        #return [ getattr(regex_prog.match(expid), 'group', matchgroupdummy)(1) for expid in self.ExperimentsById.keys() ]
        return sorted(filter(lambda x: x is not None, [ intConv(getattr(regex_prog.match(expid), 'group', matchgroupdummy)(1) ) for expid in sorted(self.ExperimentsById.keys()) ] ))
        # The above is basically just a list comprehension of the following:
        


    def getCurrentExperiments(self):
        print "Not implemented."




if __name__ == "__main__":

    import sys
    import time
    start = time.clock()
    def report():
        print "Clock: {}".format(time.clock()-start)
    #logging.basicConfig(filename='/tmp/test.log', level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(funcName)s |%(message)s')
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(funcName)s |%(message)s')
    
    def setup1():
        confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
        em = ExperimentManager(confighandler=confighandler, VERBOSE=1)
        return em, confighandler
    
    def test_getLocalExperiments(store=True):
        em, ch = setup1()
        exps = em.getLocalExperiments(store=store)
        print "Experiments:"
        print "\n".join( "{exp.Localdir} : props={props}".format(exp=exp, props=exp.Props) for exp in exps )
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
        print "\n".join( "{} : {}".format(expid, exp.Props.get('exp_title_desc')) for expid, exp in sorted(expbyid.items()) )
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


    em = None
    em, exps = test_getLocalExperiments()
    report()
    em, expbyid = test_makeExperimentsByIdMap(em)
    report()
    test_getExperimentsIndices(em)
    report()
