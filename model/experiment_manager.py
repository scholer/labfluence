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
        if server:
            self.Server = server
        self.Experiments = list()       # list of experiment objects;
        self.ExperimentsById = dict()   # also objects, but keyed as 'RS123'
        #self.ExpSummariesById = dict()  # yaml-persisted brief info, from cache. Edit, this is now a property ExperimentPropsById
        # Discussion: Is it worth having a cached summary?
        # - Note: I still think basic info should be persisted on a per-experiment basis, not in a single large yaml file.
        # - Cons: It might be easier just to have the full info, perhaps as read-only (i.e. not the main...)
        # - Cons: It might also be better to just always make experiment objects. What is the overhead on making exp objects vs just generating a dict with info?
        # - Pro:  


    """ Properties: """
    @property
    def Server(self):
        return self.Confighandler.Singletons.get('server', None)
    @Server.setter
    def Server(self, value):
        # Do NOT override existing server if set, so using setdefault...
        self.Confighandler.Singletons.setdefault('experimentmanager', value)


    @property
    def ExperimentPropsById(self):
        return self.Confighandler.setdefault('experiments_by_id', dict())
    @ExperimentsById.setter
    def ExperimentPropsById(self, value):
        # Do NOT override existing server if set, so using setdefault...
        self.Confighandler.setdefault('experiments_by_id', value)


    """
    I am not really sure how to persist my active- and recent experiments.
    - I can hardly do it as the experiment objects...
    - I could just save the expids
    - I could save the localdirpath... but that is not very portable... and does not work for exps that are only on the wiki...
    - I could save expid and foldername - and use local_exp_subDir to determine path.
    - I could save dicts or tuples with info such as expid, foldername, etc...
    - I could persist the complete Experiment Props dict... 
    
    For now, the easiest thing is probably to just persist the expid. However, that requries that
    it is easy to obtain the other info, either as exp-objects or props-dicts. Which perhaps itsn't
    that bad, it just requires this ExperimentManager to load objects upon init.
    Or, at least have all experiments cached in some form...
    
    """

    @property
    def ActiveExperimentsIds(self):
        "List of active experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_active_experiments', list())

    @property
    def ActiveExperimentsIds(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_recent_experiments', list())

    @property
    def ActiveExperiments(self):
        "List of active experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_active_experiments', list())

    @property
    def RecentExperiments(self):
        "List of recently opened experiments, obtained from confighandler."
        exps = [Experiment(manager=self, confighandler=self.Confighandler) for 
        exps = list()
        for expid in self.RecentExperimentsSavedList:
            if 
            exps.append(
        return self.Confighandler.setdefault('app_recent_experiments', list())



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




    def getCurrentWikiExperiments(self, ret='page-structs'):
        if not self.Server:
            print "No server defined."
            logging.info("No server defined.")
            return
        wiki_pages = self.Server.getChildren(self.getWikiExpRootPageId())
        if self.VERBOSE:
            print "wiki_pages:"
            print wiki_pages
        return wiki_pages


    def getLocalExperiments(self, directory=None, store=False, ret='experiment-objects'):
        """
        Parse the local experiment (sub)directory and create experiment objects from these.
        This should probably be a bit more advanced, or used from another method that processes the returned objects.
        Alternatively, make a more specialized version that interprets the regex match first 
        and compares that with the experiments_by_id.
        """
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
            match = regex_prog.match(localdir)
            if self.VERBOSE > 2:
                print "{} found when testing '{}' dirname against regex '{}'".format("MATCH" if match else "No match", localdir, regex_str)
            if match:
                #props = dict(localdir=localdir)
                if ret == 'experiment-objects':
                    experiments.append(Experiment(localdir=os.path.join(directory, localdir), regex_match=match, manager=self, confighandler=self.Confighandler, autoattachwikipage=False) )
                elif ret == 'regex-match':
                    experiments.append(match)
                elif ret == 'properties':
                    experiments.append(dict(foldername=localdir, **match.groupdict()))
                elif ret == 'tuple':
                    d = match.groupdict()
                    experiments.append(localdir, d['expid'], d.get('exp_titledesc'), d.get('date', d.get('date1', d.get('date2', None))), os.path.join(directory, localdir) )
        if store:
            self.Experiments = experiments
        return experiments


    def makeExperimentByExpIdMap(self, experiments=None, updateSelf=True, ret='experiment-objects'):
        if experiments is None:
            experiments = self.Experiments
        elif experiments == 'local':
            experiments = self.getLocalExperiments()
        elif experiments in ('wiki-current', 'wiki'):
            experiments = self.getCurrentWikiExperiments()
        expByIdMap = self.ExperimentsById if updateSelf else dict()
        for experiment in experiments:
            expid = experiment.Props.get('expid')
            # probably do some testing if there is already an exp with this expid !
            if expid in expByIdMap:
                if experiment == expByIdMap[expid]:
                    print "ExperimentManager.makeExperimentByExpIdMap() :: Identical experiment, {}".format(expid)
                else:
                    print "ExperimentManager.makeExperimentByExpIdMap() :: WARNING: Duplicate expId '{}'".format(expid)
                    #expByIdMap[expId].update(experiment) # Not implemented; and should probably do some thorough checking before simply merging.
            else:
                expByIdMap[expid] = experiment
                #print experiment
        return expByIdMap



    def getExperimentsIndices(self, expByIdMap=None):
        if expByIdMap is None:
            expByIdMap = self.ExperimentsById
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
        return sorted(filter(lambda x: x is not None, [ intConv(getattr(regex_prog.match(expid), 'group', matchgroupdummy)(1) ) for expid in sorted(expByIdMap.keys()) ] ))
        # The above is basically just a list comprehension of the following:




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


    em = None
    em, exps = test_getLocalExperiments()
    report()
    em, expbyid = test_makeExperimentsByIdMap(em)
    report()
    test_getExperimentsIndices(em)
    report()
