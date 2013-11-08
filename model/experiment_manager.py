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

#import glob
import os
import re
import logging
from collections import OrderedDict
logger = logging.getLogger(__name__) # http://victorlin.me/posts/2012/08/good-logging-practice-in-python/
#from operator import attrgetter, itemgetter, methodcaller

# Model classes:
from experiment import Experiment
from confighandler import ExpConfigHandler
from server import ConfluenceXmlRpcServer

# Decorators:
from decorators.cache_decorator import cached_property

class ExperimentManager(object):
    """
    The _wikicache is used to avoid repeated server queries, e.g. for current experiments.
    The cache is structures as a dict where key designates the cache type
    and the value is a tuple of (timestamp, object)
     'current_wikipages' : (timestamp, object)
    However, see also:
    - https://wiki.python.org/moin/PythonDecoratorLibrary#Cached_Properties (with TTL setting)
    - https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize (infinite time-to-live)
    - https://pypi.python.org/pypi/GenericCache
    - https://bitbucket.org/zzzeek/dogpile.cache - dogpile, for more advanced caching.
    - http://dogpilecache.readthedocs.org/en/latest/usage.html
    - Do not use beaker, use dogpile: http://techspot.zzzeek.org/2012/04/19/using-beaker-for-caching-why-you-ll-want-to-switch-to-dogpile.cache/
    - http://seanblanchfield.com/python-memoize-with-expiry/ - based on Django's memorize
    """
    def __init__(self, confighandler, VERBOSE=0, autoinit=None, experimentsources=('local', 'wiki') ):
        self.VERBOSE = VERBOSE
        self.Confighandler = confighandler
        self._wikicache = dict()
        #self.Experiments = list()       # list of experiment objects;
        if autoinit is None:
            autoinit = self.Confighandler.get('exp_manager_autoinit')
        #self.ExperimentsById = OrderedDict()   # Is now a property. A dict of experiment instances, but keyed by expid
        self._experimentsbyid = None #
        self._autoinit = autoinit
        self._experimentsources = experimentsources
        if autoinit:
            logger.info("Auto-initiating experiments for ExperimentManager...")
            # Can be done by invoking the ExperimentsById property:
            exps = self.ExperimentsById
            logger.debug("self.ExperimentsById: %s", exps)
            #if 'localexps' in autoinit:
            #    self.ExperimentsById = self.makeExperimentByExpIdMap(self.getLocalExperiments())
            #if 'wikiexps' in autoinit:
            #    logger.info("wikiexps in autoinit not implemented...")
        #self.ExpSummariesById = dict()  # yaml-persisted brief info, from cache. Edit, this is now a property ExperimentPropsById
        # Discussion: Is it worth having a cached summary?
        # - Note: I still think basic info should be persisted on a per-experiment basis, not in a single large yaml file.
        # - Cons: It might be easier just to have the full info, perhaps as read-only (i.e. not the main...)
        # - Cons: It might also be better to just always make experiment objects. What is the overhead on making exp objects vs just generating a dict with info?
        # - Pro:

    @property
    def ExperimentsById(self):
        if self._experimentsbyid is None:
            #if 'local' in self._experimentsources:
            self._experimentsbyid = self.makeExperimentByExpIdMap(self.getLocalExperiments(), updateSelf=False)
        return self._experimentsbyid
    @ExperimentsById.setter
    def ExperimentsById(self, value):
        self._experimentsbyid = value

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
    @ExperimentPropsById.setter
    def ExperimentPropsById(self, value):
        # Do NOT override existing experiments_by_id if set, so using setdefault...
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
    def ActiveExperimentIds(self):
        "List of active experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_active_experiments', list())
    @property
    def RecentExperimentIds(self):
        "List of recently opened experiments, obtained from confighandler."
        return self.Confighandler.setdefault('app_recent_experiments', list())
    @property
    def ActiveExperiments(self):
        "List of active experiments, obtained from confighandler."
        expids = self.ActiveExperimentIds
        logger.debug("ActiveExperimentIds: %s", expids)
        return self.getExpsById(expids)
    @property
    def RecentExperiments(self):
        "List of recently opened experiments, obtained from confighandler."
        expids = self.RecentExperimentIds
        return self.getExpsById(expids)

    def archiveExperiment(self, exp):
        if not isinstance(exp, basestring):
            expid = exp.Props['expid'] # When you eventually implement file: and wiki: notations in addition to expid:, use try-except clause
        else:
            expid = exp
        try:
            self.ActiveExperimentIds.remove(expid)
            logger.debug("Removed expid '{}' from ActiveExperimentIds".format(expid))
        except ValueError:
            logger.warning("Expid '{}' not in ActiveExperimentIds.".format(expid))
        logger.debug("Appending expid '{}' to RecentExperimentIds".format(expid))
        self.RecentExperimentIds.append(expid)
        self.sortRecentExprimentIds()
        self.Confighandler.invokeEntryChangeCallback('app_active_experiments')
        self.Confighandler.invokeEntryChangeCallback('app_recent_experiments')
        self.Confighandler.saveConfigForEntry('app_recent_experiments')

    def addActiveExperiments(self, exps, removeFromRecent=True):
        for exp in exps:
            if not isinstance(exp, basestring):
                exp = exp.Props['expid']
            self.addActiveExperimentId(exp, removeFromRecent)
        self.sortActiveExprimentIds()
        self.sortRecentExprimentIds()
        self.Confighandler.invokeEntryChangeCallback() # the 'app_active_experiments' has been marked as chaned by self.addActiveExperimentId
        self.Confighandler.saveConfigForEntry('app_active_experiments')

    def addActiveExperimentId(self, expid, removeFromRecent=True):
        self.ActiveExperimentIds.append(expid)
        logger.debug("Appending expid '{}' to RecentExperimentIds".format(expid))
        # possibly do:
        self.Confighandler.ChangedEntriesForCallbacks.add('app_active_experiments') # it is a set.
        if removeFromRecent:
            logger.debug("Removing expid '{}' from RecentExperimentIds".format(expid))
            for i in range(self.RecentExperimentIds.count(expid)):
                self.RecentExperimentIds.remove(expid)
            self.Confighandler.ChangedEntriesForCallbacks.add('app_recent_experiments')

    def sortActiveExprimentIds(self):
        # Sort "in place", just in case there are direct references to the list in other places...:
        self.ActiveExperimentIds.sort()
        logger.debug("Sorted ActiveExperimentIds: ".format(self.ActiveExperimentIds))
    def sortRecentExprimentIds(self):
        self.RecentExperimentIds.sort()
        logger.debug("Sorted RecentExperimentIds: ".format(self.RecentExperimentIds))

    def initExpIds(self, expids):
        for expid in expids:
            if not expid:
                logger.warning("expid '%s' present in expids for initExpIds()", expid)
            elif expid not in self.ExperimentsById:
                logger.info( "expid '%s' not initialized, doing so manually...", expid)
                exp = self.ExperimentsById[expid] = Experiment(manager=self, confighandler=self.Confighandler,
                        props=dict(expid=expid, exp_titledesc='Untitled experiment'), VERBOSE=self.VERBOSE)
                logger.debug( "Experiment initialized: %s with props %s", exp, exp.Props)

    def getExpsById(self, expids):
        # Make sure all expids are initialized.
        # This is a lot faster if you have already initialized all experiments in the exp_local_subdir
        self.initExpIds(expids)
        return [ self.ExperimentsById[expid] for expid in expids ]



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
        """
        I currently try to use the same regex for both local experiment folders
        and wiki experiment pages.
        """
        return self.Confighandler.get('exp_series_regex')

    def getExpSubentryRegex(self):
        return self.Confighandler.get('exp_subentry_regex')


    def getRealLocalExpRootDir(self):
        #return os.path.join(self.Confighandler.getConfigDir('exp'), self.getLocalExpRootDir() )
        # edit: I have updated ExpConfigHandler to account for this:
        path = self.getLocalExpRootDir()
        # perhaps perform some kind of check...
        if not path:
            logger.warning("LocalExpRootDir is '%s'", path)
        return path

    def getRealLocalExpSubDir(self):
        #return os.path.join(self.Confighandler.getConfigDir('exp'), self.getLocalExpRootDir(), self.getLocalExpSubDir() )
        # edit: I have updated ExpConfigHandler to account for this:
        return self.getLocalExpSubDir()



    def getLocalExperiments(self, directory=None, store=False, ret='experiment-object'):
        """
        Parse the local experiment (sub)directory and create experiment objects from these.
        This should probably be a bit more advanced, or used from another method that processes the returned objects.
        Alternatively, make a more specialized version that interprets the regex match first
        and compares that with the experiments_by_id.

        ret argument specifies how/what you want returned:
        - 'experiment-object'  -> Returns instantiated experimentobject based on the directory listing
        - 'regex-match'         -> Returns the regex match objects from matching directory listings
        - 'properties'          -> Returns a dict with 'localdir' and match.groupdict
        - 'tuple'               -> Returns a tuple of ( expid, exp_titledesc, date )
        - 'expid'               -> Returns the expid only
        - 'display-tuple'       -> (<display>, <identifier>, <full object>) tuples. Well, currently not with the full object.
        """
        if directory is None:
            directory = self.getRealLocalExpSubDir()
        # Consider using glob.re
        if not directory:
            logger.warning("ExperimentManager.getLocalExperiments initiated with directory: %s, aborting...", directory)
            return False
        localdirs = sorted([dirname for dirname in os.listdir(directory) if os.path.isdir(os.path.abspath(os.path.join(directory, dirname) ) ) ]) #os.listdir(directory)
        logger.debug( "ExperimentManager.getLocalExperiments() :: searching in directory '%s'",directory )
        logger.debug( "ExperimentManager.getLocalExperiments() :: localdirs = %s", localdirs)
        regex_str = self.getExpSeriesRegex()
        logger.debug( "Regex and localdirs: %s, %s", regex_str, localdirs )
        if not regex_str:
            logger.warning( "ExperimentManager.getLocalExperiments() :: ERROR, no exp_series_regex entry found in config!" )
            return
        regex_prog = re.compile(regex_str)
        experiments = list()
        for localdir in localdirs:
            match = regex_prog.match(localdir)
            if self.VERBOSE > -1:
                logger.debug( "%s found when testing '%s' dirname against regex '%s'", "MATCH" if match else "No match", localdir, regex_str)
            if match:
                #props = dict(localdir=localdir)
                if ret == 'experiment-object':
                    experiments.append(Experiment(localdir=os.path.join(directory, localdir), regex_match=match, manager=self, confighandler=self.Confighandler, autoattachwikipage=False) )
                elif ret == 'regex-match':
                    experiments.append(match)
                elif ret in ('properties', 'groupdict'):
                    experiments.append(dict(foldername=localdir, **match.groupdict()))
                elif ret == 'tuple':
                    d = match.groupdict()
                    experiments.append(localdir, d['expid'], d.get('exp_titledesc'), d.get('date', d.get('date1', d.get('date2', None))), os.path.join(directory, localdir) )
                elif ret == 'expid':
                    experiments.append( match.groupdict().get('expid') )
                elif ret == 'display-tuple':
                    experiments.append( ( localdir, match.groupdict().get('expid'), None ) )
                else:
                    logger.warning("ret argument '%s' not recognized, will not return anything...", ret)
        if store and ret=='experiment-object':
            logger.debug("Persisting experiments list as self.Experiments")
            self.Experiments = experiments
        logger.debug("Number of local experiments (matching regex): %s", len(experiments))
        return experiments

    @cached_property(ttl=120) # 2 minutes cache...
    def getServerInfo(self):
        """ Remember, the cached_property makes a property, which must be nvoked without '()'!
        """
        return self.Server.getServerInfo()

    @cached_property(ttl=120) # 2 minutes cache...
    def CurrentWikiExperimentsPagestructsByExpid(self):
        """
        TTL-managed cached wrapper of getCurrentWikiExperiments(ret='pagestruct-by-expid')
        # Note: the cached_property only works for property-like methods, it is not for generic methods.
        # If you would like both argument-caching (like memorize) and TTL/expiration, you should try
        # the @region.cache_on_arguments() decorator provided by dogpile.
        """
        logger.debug("invoked cache-wrapped getCurrentWikiExperiments...")
        return self.getCurrentWikiExperiments(ret='pagestructs-by-expid', useCache=False, store=None)

    def getCurrentWikiExperiments(self, ret='pagestruct', useCache=True, store=None):
        """
        NOTICE: Implementation not final.
        Currently just returning child page(struct)s of the "Experiment Root Page".

        useCache :  If True, will try to find and update existing instances rather than always
                    instantiating new experiment objects.
        store    :  Not implemented.
        ret      :  what kind of objects to return in the list.
        'expriment-object'
        'pagestruct'
        'regex-match'
        'groupdict'
        'expid'
        'tuple'
        'display-tuple'     : (<display>, <identifier>, <full object>) tuples.
        'pagestruct-by-expid': Returns dict with {expid: page} entries.

        Todo: Implement a cache system, so that repeated calls to this method will not cause
        repeated server queries.
        """
        logger.debug("getCurrentWikiExperiments called with ret='%s', useCache=%s, store=%s", ret, useCache, store)
        if self.Server is None:
            logging.info("No server defined.")
            return
        if not self.Server:
            # There might have been a temporary issue with server, see if it is ressolved:
            logger.info("Server info: %s", self.getServerInfo) # This will handle cache etc and attempt to reconnect at most every two minutes.
        if not self.Server:
            logging.warning("Server not connected, aborting")
            return
        wiki_exp_root_pageid = self.getWikiExpRootPageId()
        if not wiki_exp_root_pageid:
            logger.warning("wiki_exp_root_pageid is boolean False ('%s'), aborting...", wiki_exp_root_pageid)
            return
        wiki_pages = self.Server.getChildren(wiki_exp_root_pageid)

        regex_str = self.getExpSeriesRegex()
        logger.debug( "Regex and wiki_pages: %s, %s", regex_str, ", ".join( u"{}: {}".format(p.get('id'), p.get('title')) for p in wiki_pages ) )
        if not regex_str:
            logger.warning( "ExperimentManager.getLocalExperiments() :: ERROR, no exp_series_regex entry found in config!" )
            return
        regex_prog = re.compile(regex_str)
        if ret == 'pagestruct-by-expid':
            experiments = OrderedDict()
        else:
            experiments = list()
        for page in wiki_pages:
            match = regex_prog.match(page['title'])
            logger.debug( "%s found when testing '%s' wiki page against regex '%s'", "MATCH" if match else "No match", page['title'], regex_str)
            if match:
                gd = d = match.groupdict()
                #props = dict(localdir=localdir)
                if ret == 'experiment-object':
                    # not sure how well experiment objects work without
                    # also, you should probably refer to the existing cache rather than always instantiating
                    # a new experiment object. If present in cache, simply update with properties in match.groupdict()
                    experiments.append(Experiment(regex_match=match, manager=self, confighandler=self.Confighandler, autoattachwikipage=False, wikipage=page) )
                elif ret == 'regex-match':
                    experiments.append(match)
                elif ret == 'pagestruct':
                    experiments.append( page )
                elif ret == 'groupdict':
                    experiments.append(dict(title=page['title'], **gd))
                elif ret == 'tuple':  # Note: this tuple is not the same as
                    experiments.append( (page['title'], gd['expid'], gd.get('exp_titledesc'),
                                       gd.get('date', gd.get('date1', gd.get('date2', None))) ) )
                elif ret == 'expid':
                    experiments.append( gd.get('expid') )
                elif ret == 'display-tuple':
                    experiments.append( ( page['title'], match.groupdict().get('expid'), None ) )
                elif ret == 'pagestruct-by-expid':
                    experiments[gd['expid']] = page
                else:
                    logger.warning("ret argument '%s' not recognized, will not return anything...", ret)
        if store and ret=='experiment-object':
            # You will need to implement a lot more complex logic to merge input from wikipages
            # with that from the local directory. Alternatively keep two separate experiment lists,
            # one for the local directory and another for the wiki?
            logger.warning("storing experiments from wiki pages is not implemented yet.")
            #self.Experiments = experiments
        return experiments



    def makeExperimentByExpIdMap(self, experiments=None, updateSelf=True, ret='experiment-object'):
        """
        This is a convenience method complementing the
        getLocalExperiments, getCurrentWikiExperiments, etc methods.
        The source methods can be called by this method, or it can
        be piped in as the "experiments" argument.
        """
        if experiments is None:
            experiments = self.Experiments
        elif experiments == 'local':
            experiments = self.getLocalExperiments()
        elif experiments in ('wiki-current', 'wiki'):
            experiments = self.getCurrentWikiExperiments()
        if not experiments:
            logger.warning("Experiments are boolean False, aborting: %s", experiments)
            return
        expByIdMap = self._experimentsbyid if updateSelf else OrderedDict()
        for experiment in experiments:
            expid = experiment.Props.get('expid')
            if not expid:
                logger.warning("Non-True expid '%s' provided; exp foldername is '%s'", expid, experiment.Foldername)
            # probably do some testing if there is already an exp with this expid !
            if expid in expByIdMap:
                if experiment == expByIdMap[expid]:
                    logger.info( "ExperimentManager, identical experiment during makeExperimentByExpIdMap(), %s", expid )
                else:
                     "ExperimentManager.makeExperimentByExpIdMap() :: WARNING: Duplicate expId '{}'".format(expid)
                    #expByIdMap[expId].update(experiment) # Not implemented; and should probably do some thorough checking before simply merging.
            else:
                expByIdMap[expid] = experiment
        return expByIdMap



    def getExperimentsIndices(self, expByIdMap=None):
        if expByIdMap is None:
            expByIdMap = self.ExperimentsById
        regex_str = self.getConfigEntry('expid_regex')
        if not regex_str:
            logger.info( "No expid regex in config, aborting." )
        logger.debug( "Regex: %s", regex_str )
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



    def getNewExpid(self):
        """
        Try to deliver an educated guess for what expid the user wants to use for the next experiment...:

        Todo: also implement checking the wiki first.
        """
        indices = self.getExperimentsIndices()
        m = max(indices)
        return m+1

    def addNewExperiment(self, makelocaldir=True, makewikipage='auto', **props):
        """
        arguments:
        props must have expid, exp_titledesc, and optionally date.
        Can be implemented in two ways:
        1) Make everything here
        2) Make a new experiment object and order that to create folder and wiki page.
        Since the JournalAssistant can already add a new wiki page when ordered so
        by its parent Experiment, I think it would be suited to do it further down the model chain.
        Todo: check whether expid already exists in cache. (and a lot of other checks)
        """
        logger.info("addNewExperiment invoked with arguments makelocaldir=%s, makewikipage=%s, props=%s",
                    makelocaldir, makewikipage, props)
        required_nonempty_keys = ('expid', 'exp_titledesc')
        for k in required_nonempty_keys:
            if not props.get(k):
                logger.warning("Required key '%s' is not boolean true: '%s'", k, props.get(k))
                return
        expid = props['expid']
        if expid in self.ExperimentsById:
            logger.warning("Add new experiment requested with already existing expid '%s', aborting", expid)
            return
        exp = Experiment(props=props, makelocaldir=makelocaldir, makewikipage=makewikipage,
                         manager=self, confighandler=self.Confighandler,
                         doparseLocaldirSubentries=False)
        logger.info("New experiment created: %s, with localdir: %s, and wikipage: ", exp, exp.Localdirpath, exp.PageId)
        logger.debug("Adding newly created experiment to list of active experiments...")
        self.ExperimentsById[expid] = exp
        self.addActiveExperimentId(expid)
        return exp




if __name__ == "__main__":

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
