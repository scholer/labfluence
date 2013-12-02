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
# pylint: disable-msg=C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221,E1101,W0402,E0202,W0201,W0141
"""
experiment_manager module with ExperimentManager class,
handles logic related to managing experiment objects.
"""

#import glob
import os
import re
import logging
from collections import OrderedDict
from itertools import ifilter
logger = logging.getLogger(__name__) # http://victorlin.me/posts/2012/08/good-logging-practice-in-python/
#from operator import attrgetter, itemgetter, methodcaller

# Model classes:
from experiment import Experiment
#from confighandler import ExpConfigHandler
#from server import ConfluenceXmlRpcServer

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
        self._experimentsbyid = None
        self._autoinit = autoinit
        self._experimentsources = experimentsources
        self._experiments = list()
        if autoinit:
            logger.info("Auto-initiating experiments for ExperimentManager...")
            self.mergeLocalExperiments()
            if 'wikiexps' in autoinit:
                self.mergeCurrentWikiExperiments()
            logger.debug("self.ExperimentsById: %s", self.ExperimentsById)

    @property
    def Experiments(self):
        """property"""
        return self._experiments

    @property
    def ExperimentsById(self):
        """
        Returns a dictionary map, mapping [expid] -> expriment object.
        """
        if self._experimentsbyid is None:
            #if 'local' in self._experimentsources:
            #exps = self.Experiments or self.getLocalExperiments()
            #self._experimentsbyid = self.makeExperimentByExpIdMap(exps, updateSelf=False)
            self.mergeLocalExperiments()
        # Perhaps throw in a sort?
        return self._experimentsbyid
    @ExperimentsById.setter
    def ExperimentsById(self, value):
        """property setter"""
        self._experimentsbyid = value

    @property
    def Server(self):
        """
        Returns server registrered in confighandler's singleton registry.
        """
        return self.Confighandler.Singletons.get('server', None)
    @Server.setter
    def Server(self, value):
        """
        Set server in confighandler, if not already set.
        I do not allow overriding existing server if set, so using setdefault...
        """
        self.Confighandler.Singletons.setdefault('experimentmanager', value)

    @cached_property(ttl=60) # 1 minut cache...
    def ServerInfo(self):
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
        logger.debug("invoked cache-wrapped CurrentWikiExperimentsPagestructsByExpid...")
        pagestructs = list( self.getCurrentWikiExperiments(ret='pagestructs-by-expid') ) # Make sure you cache list and not generator.
        return pagestructs


    # Discussion: Is it worth having a cached summary?
    # - Note: I still think basic info should be persisted on a per-experiment basis, not in a single large yaml file.
    # - Cons: It might be easier just to have the full info, perhaps as read-only (i.e. not the main...)
    # - Cons: It might also be better to just always make experiment objects. What is the overhead on making exp objects vs just generating a dict with info?
    # - Pro:
    #@property
    #def ExperimentPropsById(self):
    #    return self.Confighandler.setdefault('experiments_by_id', dict())
    #@ExperimentPropsById.setter
    #def ExperimentPropsById(self, value):
    #    # Do NOT override existing experiments_by_id if set, so using setdefault...
    #    self.Confighandler.setdefault('experiments_by_id', value)


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

    def getCurrentExpid(self):
        """Returns current experiment id from app_current_expid"""
        return self.Confighandler.setdefault('app_current_expid', None)
    def setCurrentExpid(self, new_expid):
        """Sets current experiment id as app_current_expid"""
        old_expid = self.getCurrentExpid()
        if old_expid != new_expid:
            self.Confighandler.setkey('app_current_expid', new_expid)
            self.Confighandler.invokeEntryChangeCallback('app_current_expid', new_expid)
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
        """
        Marks an experiment as archived by removing it from the active experiments list,
        and adding it to the list of recent experiments instead.
        """
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
        """
        Adds an experiment to the list of active experiments.
        The active experiments list is only maintained as a list of expids,
        and not for actual experiment objects.
        """
        for exp in exps:
            if not isinstance(exp, basestring):
                # Assume Experiment-like object, or fail hard.
                exp = exp.Props['expid']
            self.addActiveExperimentId(exp, removeFromRecent)
        self.sortActiveExprimentIds()
        self.sortRecentExprimentIds()
        self.Confighandler.invokeEntryChangeCallback() # the 'app_active_experiments' has been marked as chaned by self.addActiveExperimentId
        self.Confighandler.saveConfigForEntry('app_active_experiments')

    def addActiveExperimentId(self, expid, removeFromRecent=True):
        """
        Adds an experiment ID to the list of active experiments (expids).
        """
        self.ActiveExperimentIds.append(expid)
        logger.debug("Appending expid '{}' to ActiveExperimentIds".format(expid))
        # possibly do:
        self.Confighandler.ChangedEntriesForCallbacks.add('app_active_experiments') # it is a set.
        if removeFromRecent:
            # Doing a bit specially to make sure to remove all entries, just in case:
            for _ in range(self.RecentExperimentIds.count(expid)):
                logger.debug("Removing expid '{}' from RecentExperimentIds".format(expid))
                self.RecentExperimentIds.remove(expid)
            self.Confighandler.ChangedEntriesForCallbacks.add('app_recent_experiments')

    def sortActiveExprimentIds(self):
        """
        Sort "in place", just in case there are direct references to the list in other places...:
        """
        self.ActiveExperimentIds.sort()
        logger.debug("Sorted ActiveExperimentIds: %s", self.ActiveExperimentIds)
    def sortRecentExprimentIds(self):
        """
        Sorts the list of recent experiment ids.
        """
        self.RecentExperimentIds.sort()
        logger.debug("Sorted RecentExperimentIds: %s", self.RecentExperimentIds)

    def initExpIds(self, expids):
        """
        Instantiate experiment objects for all experiment ids in expids.
        """
        for expid in expids:
            if not expid:
                logger.warning("expid '%s' present in expids for initExpIds()", expid)
            elif expid not in self.ExperimentsById:
                logger.info( "expid '%s' not initialized !...", expid)
                # Uhm... does it make sense to initialize experiments with no e.g. localdir? No.
                #exp = self.ExperimentsById[expid] = Experiment(manager=self, confighandler=self.Confighandler,
                #                                    props=dict(expid=expid))
                #logger.debug( "Experiment initialized: %s with props %s", exp, exp.Props)

    def getExpsById(self, expids):
        """
        Given a list of experiment ids, return a list of
        corresponding experiment objects.
        """
        # Make sure all expids are initialized.
        # This is a lot faster if you have already initialized all experiments in the exp_local_subdir
        self.initExpIds(expids)
        return [ self.ExperimentsById[expid] for expid in expids if expid in self.ExperimentsById ]



    ### CONFIG RELATED ###

    def getConfigEntry(self, key):
        """relays to confighandler"""
        return self.Confighandler.get(key)

    def getWikiExpRootSpaceKey(self):
        """relays to confighandler"""
        return self.Confighandler.get('wiki_exp_root_spaceKey')

    def getWikiExpRootPageId(self):
        """relays to confighandler"""
        return self.Confighandler.get('wiki_exp_root_pageId')

    def getLocalExpRootDir(self):
        """relays to confighandler"""
        return self.Confighandler.get('local_exp_rootDir') # e.g. the "_experiment_data/" dir

    def getLocalExpSubDir(self):
        """relays to confighandler"""
        return self.Confighandler.get('local_exp_subDir') # E.g. the "2013_Aarhus/" dir

    def getExpSeriesRegex(self, path=None):
        """
        I currently try to use the same regex for both local experiment folders
        and wiki experiment pages.
        """
        return self.Confighandler.get('exp_series_regex', path=path)

    def getExpSubentryRegex(self, path=None):
        """relays to confighandler"""
        return self.Confighandler.get('exp_subentry_regex', path=path)


    #def getRealLocalExpRootDir(self):
    #    #return os.path.join(self.Confighandler.getConfigDir('exp'), self.getLocalExpRootDir() )
    #    # edit: I have updated ExpConfigHandler to account for this:
    #    path = self.getLocalExpRootDir()
    #    # perhaps perform some kind of check...
    #    if not path:
    #        logger.warning("LocalExpRootDir is '%s'", path)
    #    return path
    #
    #def getRealLocalExpSubDir(self):
    #    #return os.path.join(self.Confighandler.getConfigDir('exp'), self.getLocalExpRootDir(), self.getLocalExpSubDir() )
    #    # edit: I have updated ExpConfigHandler to account for this:
    #    return self.getLocalExpSubDir()



    ########################################
    ### Loading/parsing wiki experiments ###
    ########################################

    def getLocalExperimentFolderpaths(self, directory=None):
        """
        Returns a generator of local experiment foldernames
        """
        if directory is None:
            directory = self.getLocalExpSubDir()
        # Consider using glob.re
        if not directory:
            logger.warning(" Search directory is '%s', aborting...", directory)
            return False
        # Note: sorted returns a list, not an iterator...
        localdirs = sorted( dirname for dirname in os.listdir(directory) if os.path.isdir(os.path.abspath(os.path.join(directory, dirname) ) ) ) #os.listdir(directory)
        logger.debug("localdirs in directory %s: %s", directory, localdirs)
        folderpaths = ( os.path.join(directory, dirname) for dirname in localdirs )
        return folderpaths

    def getLocalExpsDirMatchTuples(self, basedir=None):
        """
        Returns a generator with
          (localdirpath, regex_match) for local experiment folders
        """
        exp_paths = self.getLocalExperimentFolderpaths(basedir)
        if not exp_paths:
            logger.warning("exp_paths is %s, aborting...", exp_paths)
            return
        regex_str = self.getExpSeriesRegex(basedir) # using basedir should enable per-directory regex definitions.
        if not regex_str:
            logger.warning( "ERROR, no exp_series_regex entry found in config (%s), aborting...", regex_str )
            return
        logger.debug( "Parsing local folders with regex: %s", regex_str )
        regex_prog = re.compile(regex_str)
        pathmatchtuples = (tup for tup in ( (path, regex_prog.match(os.path.basename(path))) for path in exp_paths) if tup[1])
        return pathmatchtuples

    def getLocalExpsDirGroupdictTuples(self, basedir=None):
        """
        Returns a generator with (path, match.groupdict() ) tuples,
        for local experiment folders.
        """
        pathgds = ( (path, match.groupdict()) for path, match in self.getLocalExpsDirMatchTuples(basedir) )
        return ((path, dict(date=next(ifilter(None, [gd.pop('date', None), gd.pop('date1', None), gd.pop('date2', None)]), None),
                            **gd))
                    for path, gd in pathgds)


    def getLocalExperiments(self, ret='experiment-object', basedir=None):
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
        if ret == 'experiment-object':
            exps = ( Experiment(localdir=exppath, regex_match=match, manager=self, confighandler=self.Confighandler)
                    for exppath, match in self.getLocalExpsDirMatchTuples(basedir) )
        elif ret == 'regex-match':
            exps = (tup[1] for tup in self.getLocalExpsDirMatchTuples(basedir))
        elif ret in ('properties', 'groupdict'):
            exps = (tup[0] for tup in self.getLocalExpsDirMatchTuples(basedir))
        elif ret in ('properties', 'groupdict'):
            exps = (tup[1] for tup in self.getLocalExpsDirGroupdictTuples(basedir))
        elif ret == 'tuple':
            exps = (    (os.path.basename(exppath),
                        gd['expid'], gd.get('exp_titledesc'), gd.get('date', gd.get('date1', gd.get('date2', None))),
                        exppath ) for exppath, gd in self.getLocalExpsDirGroupdictTuples(basedir) )
        elif ret == 'expid':
            exps = (tup[1].get('expid') for tup in self.getLocalExpsDirGroupdictTuples(basedir))
        elif ret == 'display-tuple':
            exps = ( (os.path.basename(exppath), gd.get('expid'), None ) for exppath, gd in self.getLocalExpsDirGroupdictTuples(basedir) )
        else:
            logger.warning("ret argument '%s' not recognized, will not return anything...", ret)
            return
        return exps


    def mergeLocalExperiments(self, basedir=None, addtoactive=False):#, sync_exptitledesc=None):
        """
        Merges the current wiki experiments with the experiments from the local directory.
        sync_exptitledesc can be either of: (not implemented)
        - None = Do not change anyting.
        - 'foldername' = Change wikipage to match the local foldername
        - 'wikipage' = Change local folder to match the wiki
        """
        logger.debug("mergeLocalExperiments called with basedir='%s'", basedir)
        newexpids = list()
        if self._experimentsbyid is None:
            self._experimentsbyid = OrderedDict()
        for path, gd in self.getLocalExpsDirGroupdictTuples(basedir):
            logger.debug("Processing path: %s", path)
            expid = gd['expid']
            if expid in self._experimentsbyid: # do NOT use self.ExperimentsById as this property calls this method (cyclic reference!)
                exp = self._experimentsbyid[expid]
                if exp.Localdirpath != path:
                    logger.info("Exp %s : exp.Localdirpath != path ( %s != %s)", exp, exp.Localdirpath, path)
            else:
                exp = Experiment(props=gd, localdir=path,
                                 manager=self, confighandler=self.Confighandler,
                                 doparseLocaldirSubentries=True)
                logger.info("New experiment created: %s, with localdir: %s", exp, exp.Localdirpath)
                self._experimentsbyid[expid] = exp
                newexpids.append(expid)
        if addtoactive and newexpids:
            logger.debug("Adding new expids to active experiments: %s", newexpids)
            self.addActiveExperiments( newexpids ) # This will take care of invoking registrered callbacks in confighandler.
        return newexpids



    ########################################
    ### Loading/parsing wiki experiments ###
    ########################################


    def getExpRootWikiPages(self):
        """
        Returns a list of wiki pages directly below the page defined by config entry 'wiki_exp_root_pageId'.
        (as a list of PageSummary structs)
        PageSummary structs has keys: id, space, parentId, title, url, permissions.
        """
        if not self.Server:
            if self.Server is None:
                logging.info("No server defined, aborting.")
                return
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
        if not wiki_pages:
            logger.info("No wiki pages found for wiki_exp_root_pageid %s, server returned: %s", wiki_exp_root_pageid, wiki_pages)
        return wiki_pages


    def getCurrentWikiExpsPageMatchTuples(self):
        """
        old name: getExpRootWikiPageMatchTuples
        Returns a generator with
         (page, title regex match) tuples
        for sub-pages to the wiki_exp_root page,
        with page title matching exp_series_regex.
        """
        wiki_pages = self.getExpRootWikiPages()
        if not wiki_pages:
            logger.debug("No wiki pages, aborting...")
            return
        regex_str = self.getExpSeriesRegex()
        logger.debug( "Regex and wiki_pages: %s, %s", regex_str, ", ".join( u"{}: {}".format(p.get('id'), p.get('title')) for p in wiki_pages ) )
        if not regex_str:
            logger.warning( " ERROR, no exp_series_regex entry found in config, aborting!" )
            return
        regex_prog = re.compile(regex_str)
        pagematchtuples = (tup for tup in ( (page, regex_prog.match(page['title'])) for page in wiki_pages) if tup[1])
        return pagematchtuples

    def getCurrentWikiExpsPageGroupdictTuples(self, ):
        """
        old name: getExpRootWikiPageGroupdictTuples
        Returns a generator with (page, match.groupdict() ) tuples.
        """
        pagegds = ( (page, match.groupdict()) for page, match in self.getCurrentWikiExpsPageMatchTuples())
        return (    (page, dict(title=page['title'], expid=gd['expid'], exp_titledesc=gd['exp_titledesc'],
                                date=gd.get('date', gd.get('date1', gd.get('date2', None)))))
                    for page, gd in pagegds)


    def getCurrentWikiExperiments(self, ret='pagestruct'):
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
        repeated server queries. Possibly by routing through cached properties...
        """
        logger.debug("getCurrentWikiExperiments called with ret='%s'", ret)

        if ret == 'regex-match':
            exps =  (tup[1] for tup in self.getCurrentWikiExpsPageMatchTuples())
        elif ret in ('pagestruct', 'pagestructs'):
            exps =  (tup[0] for tup in self.getCurrentWikiExpsPageMatchTuples())
        elif ret in ('pagestruct-by-expid', 'pagestructs-by-expid'): # the plural 's' is common mistake...
            exps =  dict( (match.groupdict().get('expid'), page) for page, match in self.getCurrentWikiExpsPageMatchTuples() )
        elif ret in ('groupdict', 'groupdicts'):
            # Returns a generator with dicts, containing keys: title, expid, exp_titledesc, date or date1 or date2
            exps =  ( tup[1] for tup in self.getCurrentWikiExpsPageGroupdictTuples() )
        elif ret in ('tuple', 'tuples'):
            # Note: this tuple is NOT the same as the display tuple used for lists!
            # This is a memory efficient (pagetitle, expid, exp_titledesc, date) tuple
            exps =  ( ( gd['title'], gd['expid'], gd.get('exp_titledesc'), gd['date'] )
                        for page, gd in self.getCurrentWikiExpsPageGroupdictTuples() )
        elif ret in ('expid', 'expids'):
            exps =  ( gd.get('expid') for page, gd in self.getCurrentWikiExpsPageGroupdictTuples() )
        elif ret in ('display-tuple', 'display-tuples'):
            exps =  ( ( page['title'], match.groupdict().get('expid'), None ) for page, match in self.getCurrentWikiExpsPageMatchTuples() )
        elif ret in ('experiment-object', 'experiment-objects'):
            exps =  ( Experiment(regex_match=match, manager=self, confighandler=self.Confighandler, wikipage=page)
                        for page, match in self.getCurrentWikiExpsPageMatchTuples() )
        else:
            logger.warning("ret argument '%s' not recognized, will not return anything...", ret)
            return
        return exps


    def mergeCurrentWikiExperiments(self, autocreatelocaldirs=None):#, sync_exptitledesc=None):
        """
        Merges the current wiki experiments with the experiments from the local directory.
        sync_exptitledesc can be either of: (not implemented)
        - None = Do not change anyting.
        - 'foldername' = Change wikipage to match the local foldername
        - 'wikipage' = Change local folder to match the wiki
        """
        logger.debug("mergeCurrentWikiExperiments called with autocreatelocaldirs='%s'", autocreatelocaldirs)
        if autocreatelocaldirs is None:
            autocreatelocaldirs = self.Confighandler.get('app_autocreatelocalexpdirsfromwikiexps', False)
        newexpids = list()
        if self._experimentsbyid is None:
            self._experimentsbyid = OrderedDict()
        for page, gd in self.getCurrentWikiExpsPageGroupdictTuples():
            expid = gd['expid']
            if expid in self.ExperimentsById:
                exp = self.ExperimentsById[expid]
                if not exp.PageId:
                    logger.info("Experiment %s : Connecting to page with id %s and title: %s", exp, page['id'], page['title'])
                    exp.PageId = page['id']
            else:
                exp = Experiment(props=gd, makelocaldir=autocreatelocaldirs,
                                 manager=self, confighandler=self.Confighandler,
                                 doparseLocaldirSubentries=False, wikipage=page)
                logger.info("New experiment created: %s, with localdir: %s, and wikipage: %s", exp, exp.Localdirpath, exp.PageId)
                logger.debug("Adding newly created experiment to list of active experiments...")
                self.ExperimentsById[expid] = exp
                newexpids.append(expid)
        if newexpids:
            logger.debug("Adding new expids to active experiments: %s", newexpids)
            self.addActiveExperiments( newexpids ) # This will take care of invoking registrered callbacks in confighandler.
        return newexpids



    def makeExperimentByExpIdMap(self, experiments=None, updateSelf=True):
        """
        This is a convenience method complementing the
        getLocalExperiments, getCurrentWikiExperiments, etc methods.
        The source methods can be called by this method, or it can
        be piped in as the "experiments" argument.
        """
        if experiments is None:
            experiments = self.Experiments
        elif 'local' == experiments or 'local' in experiments:
            experiments = self.getLocalExperiments()
        elif experiments in ('wiki-current', 'wiki'):
            experiments = self.getCurrentWikiExperiments()
        if not experiments:
            logger.warning("Experiments are boolean False (%s), aborting...", experiments)
            return
        expByIdMap = self._experimentsbyid if updateSelf else OrderedDict()
        for experiment in experiments:
            expid = experiment.Props.get('expid')
            if not expid:
                logger.warning("Non-True expid '%s' provided; exp foldername is '%s', exp.Props is: %s", expid, experiment.Foldername, experiment.Props)
            # probably do some testing if there is already an exp with this expid !
            if expid in expByIdMap:
                if experiment == expByIdMap[expid]:
                    logger.info( "ExperimentManager, identical experiment during makeExperimentByExpIdMap(), %s", expid )
                else:
                    logger.info( "ExperimentManager.makeExperimentByExpIdMap() :: WARNING: Duplicate expId '%s'", expid)
                    #expByIdMap[expId].update(experiment) # Not implemented; and should probably do some thorough checking before simply merging.
            else:
                expByIdMap[expid] = experiment
        return expByIdMap



    def getExperimentsIndices(self, expByIdMap=None):
        """
        Returns a list of experiment indices, i.e. for expids list:
            ['RS102','RS104','RS105']
        return [102, 104, 105]
        """
        if expByIdMap is None:
            expByIdMap = self.ExperimentsById
        regex_str = self.getConfigEntry('expid_regex')
        if not regex_str:
            logger.info( "No expid regex in config, aborting." )
        logger.debug( "Regex: %s", regex_str )
        regex_prog = re.compile(regex_str)
        #def matchgroupdummy(*args):
        #    """ Used to avoid calling .group() method of None object: """
        #    return None
        #def intConv(str_number):
        #    """convert string to number or return None (instead of raising ValueErroor)"""
        #    try:
        #        return int(str_number)
        #    except ValueError:
        #        return None
        #f = itemgetter('expid'), g = itemgetter('Props') # allows using f(g(exp)) to get exp id, but does not deal well with KeyError exceptions
        #f = methodcaller(1) # does not work, f(a) will call a.1(), not a(1)
        #return [ intConv(getattr(regex_prog(getattr(exp, 'Props', dict()).get('expid', "")), 'group', matchgroupdummy)(1)) for exp in self.Experiments ]
        #return [ getattr(regex_prog.match(expid), 'group', matchgroupdummy)(1) for expid in self.ExperimentsById.keys() ]
        #return sorted(filter(lambda x: x is not None, [ intConv(getattr(regex_prog.match(expid), 'group', matchgroupdummy)(1) ) for expid in sorted(expByIdMap.keys()) ] ))

        return sorted( (x for x in  (int(match.group(1)) for match in (regex_prog.match(expid) for expid in expByIdMap.keys() ) )
                        if x is not None) )

#        return sorted(filter(lambda x: x is not None, [ intConv(getattr(regex_prog.match(expid), 'group', matchgroupdummy)(1) ) for expid in sorted(expByIdMap.keys()) ] ))



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
        logger.info("New experiment created: %s, with localdir: %s, and wikipage with pageId %s", exp, exp.Localdirpath, exp.PageId)
        logger.debug("Adding newly created experiment to list of active experiments...")
        self.ExperimentsById[expid] = exp
        self.addActiveExperiments( (expid, ) ) # This will take care of invoking registrered callbacks in confighandler.
        return exp




if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
