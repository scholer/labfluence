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
# messages:
#   C0301: Line too long (max 80), R0902: Too many instance attributes (includes dict())
#   C0302: too many lines in module; R0201: Method could be a function; W0142: Used * or ** magic
#   R0904: Too many public methods (20 max); R0913: Too many arguments;
#   W0221: Arguments differ from overridden method,
#   W0402: Use of deprechated module (e.g. string)
#   E1101: Instance of <object> has no <dynamically obtained attribute> member.
#   R0921: Abstract class not referenced. Pylint thinks any class that raises a NotImplementedError somewhere is abstract.
#   E0102: method already defined in line <...> (pylint doesn't understand properties well...)
#   E0202: An attribute affected in <...> hide this method (pylint doesn't understand properties well...)
#   C0303: Trailing whitespace (happens if you have windows-style \r\n newlines)
#   C0111: Missing method docstring (pylint insists on docstrings, even for one-liner inline functions and properties)
#   W0201: Attribute "_underscore_first_marks_insternal" defined outside __init__ -- yes, I use it in my properties.
# Regarding pylint failure of python properties: should be fixed in newer versions of pylint.
"""
Experiment module and its primary Experiment class
is the center for all "Experiment" related functionality.
It ties together two important helper objects:
* WikiPage
* JournalAssistant
"""



import os
import yaml
import re
from datetime import datetime
from collections import OrderedDict
import xmlrpclib
import hashlib
import fnmatch
import logging
logger = logging.getLogger(__name__)

# Labfluence modules and classes:
from page import WikiPage, WikiPageFactory
from journalassistant import JournalAssistant
from utils import getmimetype, increment_idx, idx_generator, filehexdigest
from decorators.cache_decorator import cached_property
from decorators.deprecated_decorator import deprecated


class Experiment(object):
    """
    This class is the main model for a somewhat abstract "Experiment".
    It mostly models the local directory in which the experiment (data) is saved.
    However, it is also the main node onto which other model parts of an experiment is attached, e.g.
     - A WikiPage object, representing the wiki page on the server. This object should be capable of
       performing most server-related inqueries, particularly including wiki-page updates/appends.
       Experiment objects can also refer directly to the server object. However, this is mostly as
       a convenience and is mostly used before a WikiPage object is attached; in particular the
       server object is used to search for existing/matching wiki pages.
       Most other logic should be done by the ExperimentManager rather than individual experiments.


    The Prop attribute is a dict which include the following info (is persisted as a .labfluence.yml file)
     - localdir, relative to local_exp_rootDir
     - expid, generated expid string e.g. 'RS123'
     - exp_index
     - exp_title_desc
     - exp_series_longdesc, not used
     - wiki_pageId
     - wiki_pageTitle (cached)

     Regarding "experiment entry" vs "experiment item" vs "-subitem":
      - 'subitem' returns 2e6 google hits, has entry at merriam-webster and wikitionary.
      - 'subentry' returns 4e5 google hits, but also has
      - 'item' returns 4e9 hits.
      - 'entry' returns 1.6e9 hits.
      --> I think I will go with entry, as that also relates to "entry in a journal/log".

     Subentries attribute is a list of dicts, keyed alphabetically ('a','b',...) which each include:
     - subentry_id, generated string e.g. 'RS123a'
     - subentry_idx, index e.g. 'a'.
     - subentry_titledesc,
     - dirname, directory relative to the main experiment
     - dirname should match expitem_title_desc
     Note: The properties are related via config items exp_subentry_dir_fmt and exp_subentry_regex.
           The dir can be generated using exp_subentry_dir_fmt.format(...),
           while reversedly the items can be generated from the dirname using exp_subentry_regex,
           in much the same way as is done with the experiment (series).

     Changes:
      - Trying to eliminate all the 'series' annotations and other excess;
        - exp_series_index --> exp_index
        - exp_series_shortdesc --> exp_title_desc
        - expid_str --> expid
      - Settled on term 'subentry' to designate 'RS123a'-like items.

      Considerations:
      - I recently implemented HierarchicalConfigHandler, which loads all '.labfluence.yml' files in the experiment tree.
        It seems counter-productive to also implement loading/saving of yaml files here
    """


    def __init__(self, localdir=None, props=None, server=None, manager=None, confighandler=None, wikipage=None, regex_match=None,
                 doparseLocaldirSubentries=True, subentry_regex_prog=None, autoattachwikipage=True, savepropsonchange=True, makelocaldir=False, makewikipage=False):
        """
        Arguments:
        - localdir: path string
        - props: dict with properties
        - server: Server object
        - manager: parent manager object
        - confighandler: ExpConfigHandler object; this will be used to retrieve and save local .labfluence.yml properties
        - regex_match: A re.Match object, provided by reading e.g. the folder name or wiki pagetitle.
        - VERBOSE: The verbose level of the object, e.g. for debugging. (In addition to logging levels)
        - doparseLocaldirSubentries: Search the current directory for experiment subentries.
        - subentry_regex_prog: compiled regex pattern; saved for reuse.
          If not provided, will call confighandler.getEntry() to retrieve a regex.
        - loadYmlFn: filename to use when loading and persisting experiment props; only used if confighandler is not provided.
        """
        self.VERBOSE = 0
        self.Confighandler = confighandler
        self._server = server
        self._manager = manager
        if isinstance(wikipage, WikiPage) or wikipage is None:
            self._wikipage = wikipage
        else:
            # Assume page struct:
            self._wikipage = WikiPage(wikipage.get('id', wikipage.get('pageId', None)), self.Server, pagestruct=wikipage)
        # Attaching of wiki pages is done lazily on first call. _autoattachwikipage is not really used.
        self._autoattachwikipage = autoattachwikipage
        # NOTICE: Attaching wiki pages is done lazily using a property (unless makewikipage is not False)
        self.SavePropsOnChange = savepropsonchange
        self.PropsChanged = False # Flag,
        self.Subentries_regex_prog = subentry_regex_prog # Allows recycling of a single compiled regex for faster directory tree processing.
        self.ConfigFn = '.labfluence.yml',
        self._attachments_cache = None # cached list of wiki attachment_structs. None = <not initialized>
        self._fileshistory = dict()
        self._props = dict()
        self._expid = None
        self._allowmanualpropssavetofile = False # Set to true if you want to let this experiment handle Props file persisting without a confighandler.
        self._doserversearch = False
        if localdir is None:
            localdir = props.get('localdir')
        if makelocaldir:
            logger.debug("makelocaldir is boolean True, invoking self.makeLocaldir(props=%s, localdir=%s)", props, localdir)
            localdir = self.makeLocaldir(props, localdir, wikipage) # only props currently supported...
            logger.debug("localdir after makeLocaldir: %s", localdir)
        if localdir:
            # We have a localdir. Local dirs may be of many formats, e.g.:
            #   /some/abosolute/unix/folder
            #   C:\some\absolute\windows\folder
            #   relative/unix/folder
            #   relative\windows\folder
            # More logic may be required, e.g. if the dir is relative to e.g. the local_exp_rootDir.
            self.setLocaldirpathAndFoldername(localdir)
        else:
            logger.debug("localdir is: %s (and makelocaldir was: %s), setting Localdirpath, Foldername and Parentdirpath to None.", localdir, makelocaldir)
            self.Localdirpath = None
            self.Foldername = None
            self.Parentdirpath = None

        ### Experiment properties/config related
        ### Manual handling is deprecated; Props are now a property that deals soly with confighandler."""
        if self.VERBOSE:
            logger.debug( "Experiment.__init__() :: Props already in HierarchicalConfig cfg: \n{}".format(self.Props) )
        if props:
            self.Props.update(props)
            logger.debug("Experiment %s updated with props argument, is now %s", self, self.Props)
        if regex_match:
            gd = regex_match.groupdict()
            # In case the groupdict has multiple date fields, find out which one to use and discart the other keys:
            date = next( ( date for date in [gd.pop(k, None) for k in ('date1', 'date2', 'date')] if date ), None )
            gd['date'] = date
            ## regex is often_like "(?P<expid>RS[0-9]{3}) (?P<exp_title_desc>.*)"
            self.Props.update(gd)
        elif not 'expid' in self.Props:
            logger.debug("self.Props is still too empty (no expid field). Attempting to populate it using 1) the localdirpath and 2) the wikipage.")
            exp_regex = self.getConfigEntry('exp_series_regex')
            exp_regex_prog = re.compile(exp_regex)
            regex_match = None
            if self.Foldername:
                regex_match = self.updatePropsByFoldername(exp_regex_prog)
            if not regex_match and wikipage: # equivalent to 'if wikipage and not regex_match', but better to check first:
                regex_match = self.updatePropsByWikipage(exp_regex_prog)

        if not localdir:
            logger.info( "NOTICE: No localdir provided for expid '%s'; \
functionality of this object will be greatly reduced and may break at any time.", self.Expid)

        ### Subentries related...###
        # Subentries is currently an element in self.Props, makes it easier to save info...
        self.Subentries = self.Props.setdefault('exp_subentries', OrderedDict())
        if doparseLocaldirSubentries and self.Localdirpath:
            self.parseLocaldirSubentries()

        ###I plan to allow for saving file histories, having a dict
        ###Fileshistory['RS123d subentry_titledesc/RS123d_c1-grid1_somedate.jpg'] -> list of {datetime:<datetime>, md5:<md5digest>} dicts.
        ###This will make it easy to detect simple file moves/renames and allow for new digest algorithms.

        #self.loadFileshistory()
        #if not self.WikiPage:
        #    wikipage = self.attachWikiPage(dosearch=doserversearch)
        #if self.WikiPage and self.WikiPage.Struct:
        #    self.Props['wiki_pagetitle'] = self.WikiPage.Struct['title']
        if makewikipage:
            # page attaching should only be done if you are semi-sure that a page does not already exist.
            # trying to attach a wiki page will see if a page already exist.
            page_test = self.WikiPage # will do auto-attaching.
            if not page_test:
                self.makeWikiPage()

        self.JournalAssistant = JournalAssistant(self)
        if self.VERBOSE:
            logger.debug("Experiment.__init__() :: Props (at end of init): \n{}".format(self.Props))



    ### ATTRIBUTE PROPERTIES: ###
    @property
    def Props(self):
        """
        If localdirpath is provided, use that to get props from the confighandler.
        """
        if getattr(self, 'Localdirpath', None):
            props = self.Confighandler.getExpConfig(self.Localdirpath)
        else:
            props_cache = self.Confighandler.get('expprops_by_id_cache')
            _expid = getattr(self, '_expid', None)
            if props_cache and _expid:
                props = props_cache.setdefault(_expid, dict())
            else:
                if not hasattr(self, '_props'):
                    logger.debug("Setting self._props = dict()")
                    self._props = dict()
                props = self._props
                logger.debug("(test mode?) self.Localdirpath is '%s', props_cache type: %s, self._expid is: %s, returning props: %s",
                               getattr(self, 'Localdirpath', '<not set>'), type(props_cache), _expid, props)
                #logger.debug("Returning self._props, which is: %s", props)
        try:
            wikipage = self._wikipage # Do NOT try to use self.WikiPage. self.WikiPage calls self.attachWikiPage which calls self.Props -- circular loop.
            if not props.get('wiki_pagetitle') and wikipage and wikipage.Struct \
                        and props.get('wiki_pagetitle') != wikipage.Struct['title']:
                logger.info("Updating experiment props['wiki_pagetitle'] to '{}'".format(wikipage.Struct['title']))
                props['wiki_pagetitle'] = wikipage.Struct['title']
        except AttributeError as e:
            logger.debug("AttributeError: %s", e)
        return props
    @property
    def Subentries(self):
        """Should always be located one place and one place only: self.Props."""
        return self.Props.setdefault('exp_subentries', OrderedDict())
    @Subentries.setter
    def Subentries(self, subentries):
        """property setter"""
        self.Props['exp_subentries'] = subentries
    @property
    def Expid(self):
        """Should always be located one place and one place only: self.Props."""
        return self.Props.get('expid')
    @Expid.setter
    def Expid(self, expid):
        """property setter"""
        if expid == self.Expid:
            logger.info("Trying to set new expid '{0}', but that is the same as the existing self.Expid '{1}', localpath='{2}'".format(expid, self.Expid, self.Localdirpath))
            return
        elif self.Expid:
            logger.info("Overriding old self.Expid '{1}' with new expid '{0}', localpath='{2}'".format(expid, self.Expid, self.Localdirpath))
        self.Props['expid'] = expid
    @property
    def Wiki_pagetitle(self):
        """Should always be located one place and one place only: self.Props."""
        return self.Props.get('wiki_pagetitle')
    @property
    def PageId(self, ):
        """
        Should be located only as a property of self.WikiPage
        Uhm... should calling self.PageId trigger attachment of wiki page, with all
        of what that includes?
        No. Thus, using self._wikipage and not self.WikiPage.
        """
        if self._wikipage and self._wikipage.PageId:
            self.Props.setdefault('wiki_pageId', self._wikipage.PageId)
            return self._wikipage.PageId
        elif self.Props.get('wiki_pageId'):
            pageid = self.Props.get('wiki_pageId')
            if self._wikipage:
                # we have a wikipage instance attached, but it does not have a pageid??
                self._wikipage.PageId = pageid
            return pageid
    @PageId.setter
    def PageId(self, pageid):
        """
        Will update self.Props['wiki_pageId'], and make sure that self.WikiPage
        reflects the update.
        Uhm... should calling self.PageId trigger attachment of wiki page, with all
        of what that includes?
        """
        if self._wikipage:
            if self._wikipage.PageId != pageid:
                self._wikipage.PageId = pageid
                self._wikipage.reloadFromServer()
        self.Props['wiki_pageId'] = pageid


    @cached_property(ttl=300)
    def Attachments(self):
        """
        Returns list of attachment structs with metadata on attachments on the wiki page.
        Note that the list should be treated strictly as a read-only object:
        * It is not possible to set the Attachments list.
        * Any changes made to the list will be lost when the cache is expired.
        The property invokes the cached method listAttachments.
        To reset the cache and get an updated list, use getUpdatedAttachmentsList().
        """
        return self.listAttachments()

    @property
    def Server(self):
        """
        Server evaluates to False if it is not connected, so check specifically against None.
        """
        if self._server is not None:
            return self._server
        else:
            return self.Confighandler.Singletons.get('server')
    @property
    def Manager(self):
        """
        Retrieve manager from confighandler singleton registry if not specified manually.
        """
        return self._manager or self.Confighandler.Singletons.get('manager')
    @property
    def WikiPage(self):
        """
        Attempts to lazily attach a wikipage if none is attached.
        """
        if not self._wikipage:
            self.attachWikiPage()
            if self._wikipage:
                logger.info("%s - Having just attached the wikipage (pageid=%s), I will now parse wikipage subentries and merge them...",
                            self, self._wikipage.PageId)
                self.mergeWikiSubentries(self._wikipage)
        return self._wikipage
    @WikiPage.setter
    def WikiPage(self, newwikipage):
        """property setter"""
        self._wikipage = newwikipage
    @property
    def Fileshistory(self):
        """
        Invokes loadFilesHistory() lazily if self._fileshistory has not been loaded.
        """
        if not self._fileshistory:
            self.loadFileshistory() # Make sure self.loadFileshistory does NOT refer to self.Fileshistory (cyclic reference)
        return self._fileshistory
    @property
    def Subentries_regex_prog(self):
        """
        Returns self._subentries_regex_prog if defined and not None, otherwise obtain from confighandler.
        """
        regex_prog = getattr(self, '_subentries_regex_prog', None)
        if regex_prog:
            return regex_prog
        else:
            regex_str = self.getConfigEntry('exp_subentry_regex') #getExpSubentryRegex()
            if not regex_str:
                logger.warning("Warning, no exp_subentry_regex entry found in config, reverting to hard-coded default.")
                regex_str = r"(?P<date1>[0-9]{8})?[_ ]*(?P<expid>RS[0-9]{3})-?(?P<subentry_idx>[^_ ])[_ ]+(?P<subentry_titledesc>.+?)\s*(\((?P<date2>[0-9]{8})\))?$"
            self._subentries_regex_prog = re.compile(regex_str)
            return self._subentries_regex_prog
    @Subentries_regex_prog.setter
    def Subentries_regex_prog(self, value):
        """property setter"""
        self._subentries_regex_prog = value
    @property
    def Status(self):
        """
        Returns whether experiment is 'active' or 'recent'.
        Returns None if neither.
        """
        manager = self.Manager
        if not manager:
            return None
        if self.Expid in manager.ActiveExperimentIds:
            return 'active'
        elif self.Expid in manager.RecentExperimentIds:
            return 'recent'
    def isactive(self):
        """Returns whether experiment is listed in the active experiments list."""
        return self.Status == 'active'
    def isrecent(self):
        """Returns whether experiment is listed in the recent experiments list."""
        return self.Status == 'recent'

    ## Non-property getters:
    def getUrl(self):
        """get wikipage url"""
        url = self.Props.get('url', None)
        if not url:
            # Note: self.WikiPage will trigger attachWikipage including possible server search for wiki page.
            # Using self._wikipage will not do this.
            if self.WikiPage:
                url = self.WikiPage.getViewPageUrl()
        return url


    ########################
    ### MANAGER methods: ###
    ########################

    def archive(self):
        """
        archive this experiment, relays through self.Manager.
        """
        mgr = self.Manager
        if not mgr:
            logger.debug("archive() invoked, but no ExperimentManager associated, aborting...")
            return
        self.Manager.archiveExperiment(self)


    ######################
    ### Macro methods: ###
    ######################

    def saveAll(self):
        """
        Method for remembering to do all things that must be saved before closing experiment.
         - self.Props, dict in .labfluence.yml
         - self.Fileshistory, dict in .labfluence/files_history.yml
        What else is stored in <localdirpath>/.labfluence/ ??
         - what about journal assistant files?

        Consider returning True if all saves suceeded and False otherwise...
        e.g.
            return self.saveProps() and self.saveFileshistory()
        """
        self.saveProps()
        self.saveFileshistory()


    """
    STUFF RELATED TO PROPERTY HANDLING/PERSISTING AND LOCAL DIR PARSING
    """

    def getConfigEntry(self, cfgkey, default=None):
        """
        self.Props is linked to Confighandler, so
            self.Confighandler.get(cfgkey, path=self.Localdirpath)
        should return exactly the same as
            self.Props.get(cfgkey)
        if cfgkey is in self.Props.
        However, probing self.Props.get(cfgkey) directly should be somewhat faster.
        """
        if cfgkey in self.Props:
            return self.Props.get(cfgkey)
        else:
            p = getattr(self, 'Localdirpath', None)
            return self.Confighandler.get(cfgkey, default=default, path=p)

    def setConfigEntry(self, cfgkey, value):
        """
        Sets config entry. If cfgkey is listed in self.Props, then set/update that,
        otherwise relay through to self.Confighandler.
        Notice: does not currently check the hierarchical config,
        only the explicidly loaded 'system', 'user', 'exp', 'cache', etc.
        """
        if cfgkey in self.Props:
            self.Props[cfgkey] = value
        else:
            self.Confighandler.setkey(cfgkey, value)

    def getAbsPath(self):
        """
        Returns the absolute path of self.Localdirpath. Not sure this is required?
        """
        return os.path.abspath(self.Localdirpath)

    def saveIfChanged(self):
        """
        Saves props if the self.PropsChanged flag has been switched to True.
        Can be invoked as frequently as you'd like.
        """
        if self.PropsChanged:
            self.saveProps()
            self.PropsChanged = False

    def saveProps(self, path=None):
        """
        Saves content of self.Props to file.
        If a confighandler is attached, allow it to do it; otherwise just persist as yaml to default location.
        """
        logger.debug("(Experiment.saveProps() triggered; confighandler: {}".format(self.Confighandler))
        if self.VERBOSE > 2:
            logger.debug("self.Props: {}".format(self.Props))
        if path is None:
            path = self.Localdirpath
            if not path:
                logger.debug("No path provided to saveProps and Experiment.Localdirpath is also '%s'", path)
                return False
        if self.Confighandler:
            if not os.path.isdir(path):
                path = os.path.dirname(path)
            logger.debug("Invoking self.Confighandler.updateAndPersist(path=%s, self.Props=%s)", path, self.Props)
            self.Confighandler.updateAndPersist(path, self.Props)
        elif self._allowmanualpropssavetofile:
            logger.debug("Experiment.saveProps() :: No confighandler, saving manually...")
            if os.path.isdir(path):
                path = os.path.normpath(os.path.join(self.Localdirpath, self.ConfigFn))
            logger.debug("Experiment.saveProps() :: saving directly to file '%s' (not using confighandler)", path)
            yaml.dump(self.Props, open(path, 'wb'))
        else:
            return False
        if self.VERBOSE > 4:
            logger.debug("\nContent of exp config/properties file after save:")
            logger.debug(open(os.path.join(path, self.ConfigFn)).read())
        return True


    def updatePropsByFoldername(self, regex_prog=None):
        """
        Update self.Props to match the meta info provided by the folder name, e.g. expid, titledesc and date.
        """
        if regex_prog is None:
            exp_regex = self.getConfigEntry('exp_series_regex')
            regex_prog = re.compile(exp_regex)
        regex_match = regex_prog.match(self.Foldername)
        if regex_match:
            self.Props.update(regex_match.groupdict())
            logger.debug("Props updated using foldername %s and regex, returning groupdict %s", self.Foldername, regex_match.groupdict())
            if self.SavePropsOnChange:
                self.saveProps()
        return regex_match

    def updatePropsByWikipage(self, regex_prog=None):
        """
        Update self.Props to match the meta info provided by the wiki page (page title),
        e.g. expid, titledesc and date.
        """
        if regex_prog is None:
            exp_regex = self.getConfigEntry('exp_series_regex')
            regex_prog = re.compile(exp_regex)
        wikipage = self.WikiPage
        if not wikipage.Struct:
            wikipage.reloadFromServer()
        regex_match = regex_prog.match(wikipage.Struct.get('title'))
        if regex_match:
            self.Props.update(regex_match.groupdict())
            logger.debug("Props updated using wikipage.Struct['title'] %s and regex, returning groupdict %s", regex_match.string, regex_match.groupdict())
            if self.SavePropsOnChange:
                self.saveProps()
        return regex_match



    def makeFormattingParams(self, subentry_idx=None, props=None):
        """
        Returns a dict containing all keys required for many string formatting interpolations,
        e.g. makes a dict that includes both expid and subentry props.
        """
        fmt_params = dict(datetime=datetime.now())
        # datetime always refer to datetime.datetime objects; 'date' may refer either to da date string or a datetime.date object.
        # edit: 'date' must always be a string date, formatted using 'journal_date_format'.
        fmt_params.update(self.Props) # do like this to ensure copy and not override, just to make sure...
        if subentry_idx:
            fmt_params['subentry_idx'] = subentry_idx
            fmt_params['next_subentry_idx'] = increment_idx(subentry_idx)
            if self.Subentries and subentry_idx in self.Subentries:
                fmt_params.update(self.Subentries[subentry_idx])
        if props:
            fmt_params.update(props) # doing this after to ensure no override.
        fmt_params['date'] = fmt_params['datetime'].strftime(self.Confighandler.get('journal_date_format', '%Y%m%d'))
        return fmt_params


    def setLocaldirpathAndFoldername(self, localdir):
        """
        Takes a localdir, either absolute or relative (to local_exp_subDir),
        and use this to set self.Foldername, self.Parentdirpath and self.Localdirpath.
        """
        foldername, parentdirpath, localdirpath = self._getFoldernameAndParentdirpath(localdir)
        logger.debug("self._getFoldernameAndParentdirpath(%s) returned: %s, %s, %s", localdir, foldername, parentdirpath, localdirpath)
        self.Parentdirpath = parentdirpath
        if not foldername:
            logger.warning( "Experiment.__init__() :: Warning, could not determine foldername...????" )
        self.Foldername = foldername
        self.Localdirpath = localdirpath
        logger.debug("self.Parentdirpath=%s, self.Foldername=%s, self.Localdirpath=%s", self.Parentdirpath, self.Foldername, self.Localdirpath)

    def _getFoldernameAndParentdirpath(self, localdir):
        """
        Takes a localdir, either absolute or relative (to local_exp_subDir),
        and returns the foldername and parentdirpath of the localdir.
        """
        localdir = os.path.expanduser(localdir)
        if not os.path.isabs(localdir):
            # The path provided was relative, e.g.:
            # "RS102 Strep-col11 TR annealed with biotin",
            # or "2012_Aarhus/RS065 something".
            local_exp_root = self.getConfigEntry('local_exp_rootDir')
            local_exp_subdir = self.getConfigEntry('local_exp_subDir')
            if os.path.isdir(os.path.join(local_exp_root, localdir)):
                localdir = os.path.join(local_exp_root, localdir)
            elif os.path.isdir(os.path.join(local_exp_subdir, localdir)):
                localdir = os.path.join(local_exp_subdir, localdir)
            else:
                if getattr(self, 'Parentdirpath', None):
                    logger.info("localdir %s does not exist, but self.Parentdirpath is set, so using self.Parentdirpath %s as base.", localdir, self.Parentdirpath)
                    localdir = os.path.join(self.Parentdirpath, localdir)
                else:
                    logger.info("localdir %s does not exist, using local_exp_subDir (%s) as base.", localdir, local_exp_subdir)
                    common = os.path.commonprefix([local_exp_subdir, localdir])
                    if common:
                        # localdir might be a long relative dir, that shares most in comon with local_exp_subDir.
                        org = localdir
                        localdir = os.path.abspath(os.path.join(local_exp_subdir, os.path.relpath(localdir, local_exp_subdir)))
                        logger.info("EXPERIMENTAL: localdir set using os.path.abspath(os.path.join(local_exp_subdir, os.path.relpath(localdir, local_exp_subdir))):\
\n-localdir: %s\n-local_exp_subDir: %s\n-localdir: %s", org, local_exp_subdir, localdir)
                    else:
                        localdir = os.path.join(local_exp_subdir, localdir)
                        logger.info("Setting localdir by joining local_exp_subdir and localdir, result is: %s", localdir)
        parentdirpath, foldername = os.path.split(localdir)
        return foldername, parentdirpath, localdir


    def makeLocaldir(self, props, localdir=None, wikipage=None):
        """
        Alternatively, 'makeExperimentFolder' ?
        props:      Dict with props required to generate folder name.
        localdir:   Not supported yet.
        wikipage:   Not supported yet.
        """
        # Note: If this is called as part of __init__, it is called as one of the first things,
        # before setting self.Props, and before pretty much anything.
        logger.debug("Experiment makeLocaldir invoked with props=%s, localdir=%s", props, localdir)
        try:
            foldername = self.getFoldernameFromFmtAndProps(props)
            localexpsubdir = self.getConfigEntry('local_exp_subDir')
            localdirpath = os.path.join(localexpsubdir, foldername)
            os.mkdir(localdirpath)
            #logger.info("Created new localdir: %s", localdirpath)
        except KeyError as e:
            logger.warning("KeyError making new folder: %s", e)
        except TypeError as e:
            logger.warning("TypeError making new folder: %s", e)
        except OSError as e:
            logger.warning("OSError making new folder: %s", e)
        except IOError as e:
            logger.warning("IOError making new folder: %s", e)
        logger.info("Created new localdir for experiment: %s", localdirpath)
        return localdirpath


    def getFoldernameFromFmtAndProps(self, props=None, foldername_fmt=None):
        """
        Generates a foldername formatted using props and the format string in
        confighandler's exp_series_dir_fmt config entry.
        """
        if props is None:
            props = self.Props
        if foldername_fmt is None:
            foldername_fmt = self.getConfigEntry('exp_series_dir_fmt')
        foldername = foldername_fmt.format(**props)
        return foldername



    def changeLocaldir(self, newfolder):
        """
        Renames the folder of the experiment's local folder.
        Will also rename path-based exp key in confighandler.
        newfolder can be either an absolute path, or relative compared to either of:
        - local_exp_rootDir
        - local_exp_subDir
        - self.Parentdirpath (in case the experiment was previously initialized).
        """
        oldlocaldirpath = self.Localdirpath
        _, newfoldername, newlocaldirpath = self._getFoldernameAndParentdirpath(newfolder)
        try:
            os.rename(oldlocaldirpath, newlocaldirpath)
        except OSError as e:
            logger.warning("OSError renaming old folder %s to new folder %s: %s", oldlocaldirpath, newlocaldirpath, e)
        except IOError as e:
            logger.warning("IOError renaming old folder %s to new folder %s: %s", oldlocaldirpath, newlocaldirpath, e)
        self.Confighandler.renameConfigKey(oldlocaldirpath, newlocaldirpath)
        logger.info("Renamed old folder %s to new folder %s", oldlocaldirpath, newlocaldirpath)
        return newlocaldirpath



    ### STUFF RELATED TO SUBENTRIES ###

    def sortSubentrires(self):
        """
        Make sure the subentries are properly sorted. They might not be, e.g. if subentry f was created locally
        while subentry e was created on the wiki page and only read in later.
        """
        #org_keyorder = self.Subentries.keys()
        if self.Subentries.keys() == sorted(self.Subentries.keys()):
            return
        self.Props['exp_subentries'] = self.Subentries = OrderedDict(sorted(self.Subentries.items()) )


    def addNewSubentry(self, subentry_titledesc, subentry_idx=None, subentry_date=None, extraprops=None, makefolder=False, makewikientry=False):
        """
        Adds a new subentry and add it to the self.Props['subentries'][<subentry_idx>].
        Optionally also creates a local subentry folder and adds a new subentry section to the wiki page,
        by relaying to self.makeSubentryFolder() and self.makeWikiSubentry()
        """
        if subentry_idx is None:
            subentry_idx = self.getNewSubentryIdx()
        if subentry_idx in self.Subentries:
            logger.error("Experiment.addNewSubentry() :: ERROR, subentry_idx '{}' already listed in subentries, aborting...".format(subentry_idx))
            return
        if subentry_date is None:
            subentry_datetime = datetime.now()
            subentry_date = "{:%Y%m%d}".format(subentry_datetime)
        elif isinstance(subentry_date, datetime):
            subentry_datetime = subentry_date
            subentry_date = "{:%Y%m%d}".format(subentry_datetime)
        elif isinstance(subentry_date, basestring):
            date_format = self.getConfigEntry('journal_date_format')
            subentry_datetime = datetime.strptime(subentry_date, date_format)
        subentry = dict(subentry_idx=subentry_idx, subentry_titledesc=subentry_titledesc, date=subentry_date, datetime=subentry_datetime)
        if extraprops:
            subentry.update(extraprops)
        self.Subentries[subentry_idx] = subentry
        if makefolder:
            self.makeSubentryFolder(subentry_idx)
        if makewikientry:
            self.makeWikiSubentry(subentry_idx)
        self.saveIfChanged()
        return subentry


    def getSubentryFoldername(self, subentry_idx):
        """
        Returns the foldername for a particular subentry, relative to the experiment directory.
        Returns None in case of e.g. KeyError.
        Returns False if foldername is an existing path, but not a directory.
         -- Edit: This is currently not implemented; I will cross that bridge if it ever becomes an issue.
        """
        try:
            subentry = self.Subentries[subentry_idx]
        except KeyError:
            logger.debug("subentry_idx not in self.Subentries, returning None")
            return
        if 'foldername' in subentry:
            foldername = subentry['foldername']
            if os.path.isdir(os.path.join(self.Localdirpath, foldername)):
                return foldername
            else:
                logger.warning("Subentry '%s' exists in self.Props and has a 'foldername' key with \
                               value '%s', but this is not a foldername!", subentry_idx, foldername)
        # No existing folder specified; make one from the format provided in configentry:
        fmt_params = self.makeFormattingParams(subentry_idx=subentry_idx, props=subentry)
        subentry_foldername_fmt = self.getConfigEntry('exp_subentry_dir_fmt')
        subentry_foldername = subentry_foldername_fmt.format(**fmt_params)
        return subentry_foldername


    def existingSubentryFolder(self, subentry_idx, returntuple=False):
        """
        Serves two purposes:
        1) To tell whether a particular subentry exists,
        2) If returntuple is True, will return a tuple consisting of:
            (boolean whether subentry folder exist,
             subentry_folder_path, subentry_foldername)
        """
        subentry_foldername = self.getSubentryFoldername(subentry_idx)
        folderpath = os.path.realpath(os.path.join(self.Localdirpath, subentry_foldername))
        if os.path.isdir(folderpath):
            if returntuple:
                return (True, folderpath, subentry_foldername)
            return True
        elif os.path.exists(folderpath):
            logger.warning("The folder specified by subentry '%s' exists, but is not a directory: %s ", subentry_idx, folderpath)
        if returntuple:
            return (False, folderpath, subentry_foldername)
        return False

    def registerCallback(self, callbackkey):
        """
        It would be nice to be able to register various kinds of callbacks,
        e.g. have a wikipage reload (fetch new struct from server)
        trigger e.g. a new subentry merge, and have a new subentry init
        invoking a UI widget reload.
        """
        pass


    def makeSubentryFolder(self, subentry_idx):
        """
        Creates a new subentry subfolder in the local experiment directory,
        with a foldername matching the format dictated in the config
        as config key 'exp_subentry_dir_fmt'.
        """
        try:
            subentry = self.Subentries[subentry_idx]
        except KeyError:
            logger.warning("Experiment.makeSubentryFolder() :: ERROR, subentry_idx '{}' not listed in subentries, aborting...".format(subentry_idx) )
            return

        folder_exists, newfolderpath, subentry_foldername = self.existingSubentryFolder(subentry_idx, returntuple=True)
        if folder_exists:
            logger.error("\nExperiment.makeSubentryFolder() :: ERROR, newfolderpath already exists, aborting...\n--> '{}'".format(newfolderpath))
            return
        try:
            os.mkdir(newfolderpath)
        except OSError as e:
            logger.error("\n%s\nExperiment.makeSubentryFolder() :: ERROR, making new folder: '%s'".format(e, newfolderpath))
            return False
        subentry['foldername'] = subentry_foldername
        if self.SavePropsOnChange:
            self.saveProps()
        return subentry_foldername

    @deprecated
    def getSubentry_(self, subentry_idx, default='getSubentry-not-set', ensureExisting=False):
        """
        I want to raise KeyError if default is not given (like dict does).
        However, how to set default to allow it to be optional, but allowing the
        user to set it to e.g. None. It is very likely that the user would want to get
        'None' returned instead of having a KeyError value raised.
        Note: Unless you want to use the 'default' parameter or make convenient use of
        the 'ensureExisting' option, it is generally more code efficient to simply do:
            try:
                subentry = self.Subentries[subentry_idx]
            except KeyError:
                <something>
        or just use:
            self.Subentries.get(subentry_idx, None)
        Actually, I think this is a bad method to have, the only advantage is that if you
        decide to refactor and e.g. have Subentries as something else, you would just have to
        change this method. However, since self.Subentries is a property, I can always just change that.
        So, I hereby decide to deprechate this method.
        And actually, the dict does NOT raise a KeyError, ever. But, in that case, just use
        self.Subentries.get(subentry_idx) instead of bloating this class with yet another method.
        """
        if subentry_idx not in self.Subentries and ensureExisting:
            self.initSubentriesUpTo(subentry_idx)
        if default != 'getSubentry-not-set':
            return self.Subentries.get(subentry_idx, default)
        else:
            return self.Subentries[subentry_idx]


    def initSubentriesUpTo(self, subentry_idx):
        """
        Make sure all subentries are initiated up to subentry <subentry_idx>.
        """
        if not self.Subentries:
            self.Subentries = OrderedDict()
        for idx in idx_generator(subentry_idx):
            if idx not in self.Subentries:
                self.Subentries[idx] = dict()

    def getExpRepr(self, default=None):
        """
        Returns a string representation of this exp object.
        Used by self.__repr__()
        """
        if 'foldername' in self.Props:
            return self.Props['foldername']
        else:
            fmt = self.Confighandler.get('exp_series_dir_fmt')
            fmt_params = self.makeFormattingParams()
            try:
                return fmt.format(**fmt_params)
            except KeyError:
                if default:
                    return default
                else:
                    return "{} {}".format(self.Props.get('expid', None), self.Props.get('exp_titledesc', None))

    def getSubentryRepr(self, subentry_idx=None, default=None):
        """
        Returns a string representation for a particular subentry,
        formatted according to config entry 'exp_subentry_dir_fmt'
        Is used to create new subentry folders, and display subentries in e.g. lists, etc.
        """
        if subentry_idx:
            subentry = self.Subentries.get(subentry_idx, None)
            if subentry:
                if 'foldername' in subentry:
                    return subentry['foldername']
                else:
                    fmt = self.Confighandler.get('exp_subentry_dir_fmt')
                    fmt_params = self.makeFormattingParams(subentry_idx=subentry_idx)
                    try:
                        return fmt.format(**fmt_params)
                    except KeyError:
                        if default:
                            return default
                        else:
                            return "{}{} {}".format(self.Props.get('expid', None), subentry.get('subentry_idx', None), self.Props.get('subentry_titledesc', None))
        if default == 'exp':
            return self.getExpRepr()
        else:
            return default



    def parseLocaldirSubentries(self, directory=None):
        """
        make self.Subentries by parsing local dirs like '20130106 RS102f PAGE of STV-col11 TR staps (20010203)'.

        """
        if directory is None:
            directory = self.Localdirpath
            logger.debug("No directory provided, using self.Localdirpath '%s'", directory)
        if directory is None:
            logger.error("Experiment.parseLocaldirSubentries() :: ERROR, no directory provided and no localdir in Props attribute.")
            return
        # Consider using glob.re
        regex_prog = self.Subentries_regex_prog
        logger.debug("parsing subentries for directory %s ", directory)
        localdirs = sorted([dirname for dirname in os.listdir(directory) if os.path.isdir(os.path.abspath(os.path.join(directory, dirname) ) ) ])
        if self.VERBOSE:
            logger.debug("Experiment.parseLocaldirSubentries() :: self.Props:\n{}".format(self.Props))
        subentries = self.Props.setdefault('exp_subentries', OrderedDict())
        if self.VERBOSE:
            logger.debug("Experiment.parseLocaldirSubentries() :: searching in directory '{}'".format(directory))
            logger.debug("Experiment.parseLocaldirSubentries() :: regex = '{}'".format(regex_prog.pattern))
            logger.debug("Experiment.parseLocaldirSubentries() :: localdirs = {}".format(localdirs))
            logger.debug("Experiment.parseLocaldirSubentries() :: subentries (before read:) = \n{}\n".format(subentries))
        for foldername in localdirs:
            res = regex_prog.match(foldername)
            if self.VERBOSE:
                logger.info("\n\n{} found when testing '{}' dirname against regex '{}'".format("MATCH" if res else "No match", foldername, regex_prog.pattern))
            if res:
                props = res.groupdict()
                # I allow for regex with multiple date entries, i.e. both at the start end end of filename.
                datekeys = sorted( key for key in props.items() if 'date' in key and len(key)>4 )
                # Having found the relevant datekeys, remove them all from the parsed props dict.
                # If there is one that is not None, set it as the 'real' date field for the subentry:
                for k in datekeys:
                    val = props.pop(k)
                    if val:
                        props['date'] = val
                props['foldername'] = foldername
                #if 'subentry_idx' in props: - it must be
                current_idx = props['subentry_idx']
                # edit: how could subentry_idx possibly not be in res.groupdict? only if not included in regex?
                # anyways, if not present, simply making a new index could be dangerous; what if the directories are not sorted and the next index is not right?
                #else:
                #    current_idx =  self.getNewSubentryIdx() # self.subentry_index_increment(current_idx)
                subentries.setdefault(current_idx, dict()).update(props)
        return subentries

    def parseSubentriesFromWikipage(self, wikipage=None, xhtml=None, return_subentry_xhtml=False):
        """
        Note: wikipage is a WikiPage object, not a page struct.
        Not sure what the return_subentry_xhtml argument was intended for...?
        """
        ### Uh, it would seem that the wiki_experiment_section config entry has gone missing,
        ### returning none until it is back up.
        return dict()
        if isinstance(wikipage, WikiPage):
            logger.debug("wikipage is instance of WikiPage, ok.")
        else:
            logger.warning("wikipage is not instance of WikiPage! This has not been implemented (but should be easy to do)")
        if xhtml is None:
            if wikipage is None:
                wikipage = self.WikiPage
            #xhtml = wikipage['content']
            xhtml = wikipage.Content
        expsection_regex = self.getConfigEntry('wiki_experiment_section')
        logger.debug("expsection_regex = %s", expsection_regex)
        expsection_regex_prog = re.compile(expsection_regex, flags=re.DOTALL+re.MULTILINE)
        logger.debug("wiki_experiment_section is:\n%s", expsection_regex_prog.pattern)

        subentry_regex_fmt = self.getConfigEntry('wiki_subentry_regex_fmt')
        logger.debug("wiki_subentry_regex_fmt is\n%s", subentry_regex_fmt)
        subentry_regex = subentry_regex_fmt.format(expid=self.Expid, subentry_idx=r"(?P<subentry_idx>[_-]{0,3}[^\s]+)" ) # alternatively, throw in **self.Props
        logger.debug("Subentry regex after format substitution:\n%s", subentry_regex)
        subentry_regex_prog = re.compile(subentry_regex, flags=re.DOTALL+re.MULTILINE)

        expsection_match = expsection_regex_prog.match(xhtml) # consider using search instead of match?
        if not expsection_match:
            logger.warning("NO MATCH ('%s') for expsubsection_regex '%s' in xhtml of length %s, aborting",
                           expsection_match, expsection_regex_prog.pattern, len(xhtml))
            logger.debug("xhtml is:\n%s", xhtml)
            return
        exp_xhtml = expsection_match.groupdict().get('exp_section_body')
        if not exp_xhtml:
            logger.warning("Aborting, exp_section_body is empty: %s", exp_xhtml)
            return
        wiki_subentries = OrderedDict()
        for match in subentry_regex_prog.finditer(exp_xhtml):
            gd = match.groupdict()
            logger.debug("Match groupdict: %s", gd)
            datestring = gd.pop('subentry_date_string')
            if not return_subentry_xhtml:
                subentry_xhtml = gd.pop('subentry_xhtml')
            if datestring:
                gd['date'] = datetime.strptime(datestring, "%Y%m%d")
            if gd['subentry_idx'] in wiki_subentries:
                logger.warning("Duplicate subentry_idx '%s' encountered while parsing xhtml", gd['subentry_idx'])
            wiki_subentries[gd['subentry_idx']] = gd
        return wiki_subentries


    def mergeWikiSubentries(self, wikipage=None):
        """
        Used to parse existing subentries (in self.Props) with subentries
        obtained by parsing the wiki page.
        """
        if wikipage is None:
            wikipage = self.WikiPage
        wiki_subentries = self.parseSubentriesFromWikipage(wikipage)
        # OrderedDict returned
        subentries = self.Subentries
        for subentry_idx, subentry_props in wiki_subentries.items():
            if subentry_idx in subentries:
                logger.debug("Subentry '%s' from wikipage already in Subentries", subentry_idx)
            else:
                subentries[subentry_idx] = subentry_props
                logger.debug("Subentry '%s' from wikipage added to Subentries, props are: %s",
                             subentry_idx, subentry_props)





    def getNewSubentryIdx(self):
        """
        Returns the next subentry idx, e.g.:
        if 'a', 'b', 'd' are existing subentries --> return 'e'
        """
        if not self.Subentries:
            return 'a'
        return increment_idx(sorted(self.Subentries.keys())[-1])




    """ -------------------------------------------
    --- STUFF related to local file management ----
    ------------------------------------------- """


    def renameSubentriesFoldersByFormat(self, createNonexisting=False):
        """
        Renames all subentries folders to match
        """
        dir_fmt = self.getConfigEntry('exp_subentry_dir_fmt')
        if not dir_fmt:
            logger.warning("No 'exp_subentry_dir_fmt' found in config; aborting")
            return
        for subentry in self.Subentries.values():
            # subentry is a dict
            newname = dir_fmt.format(subentry)
            newname_full = os.path.join(self.Localdirpath, newname)
            if 'dirname' in subentry:
                oldname_full = os.path.join(self.Localdirpath, subentry['dirname'])
                logger.info("Renaming subentry folder: {} -> {}".format(oldname_full, newname_full))
                #os.rename(oldname_full, newname_full)
            elif createNonexisting:
                logger.info("Making new subentry folder: {}".format(newname_full))
                #os.mkdir(newname_full)
            subentry['dirname'] = newname


    def renameFolderByFormat(self):
        """
        Renames the local directory folder to match the formatting dictated by exp_series_dir_fmt.
        Also takes care to update the confighandler.
        """
        dir_fmt = self.getConfigEntry('exp_series_dir_fmt')
        if not dir_fmt:
            logger.warning("No 'exp_series_dir_fmt' found in config; aborting")
            return
        newname = dir_fmt.format(self.Props)
        newpath = os.path.join(self.Parentdirpath, newname)
        oldpath = self.Localdirpath
        logger.info("Renaming exp folder: {} -> {}".format(oldpath, newpath))
        #os.rename(oldname_full, newname_full)
        self.Localdirpath = newpath
        self.Foldername = newname
        # Note: there is NO reason to have a key 'dirname' in self.Props;
        if self.Confighandler:
            self.Confighandler.renameConfigKey(oldpath, newpath)


    def hashFile(self, filepath, digesttypes=('md5', )):
        """
        Default is currently md5, although e.g. sha1 is not that much slower.
        The sha256 and sha512 are approx 2x slower than md5, and I dont think that is requried.

        Returns digestentry dict {datetime:datetime.now(), <digesttype>:digest }
        """
        logger.info("Experiment.hashFile() :: Not tested yet - take care ;)")
        if not os.path.isabs(filepath):
            filepath = os.path.normpath(os.path.join(self.Localdirpath, filepath))
        relpath = os.path.relpath(filepath, self.Localdirpath)
        fileshistory = self.Fileshistory
        digestentry = dict( (digesttype, filehexdigest(filepath, digesttype)) for digesttype in digesttypes)
        digestentry['datetime'] = datetime=datetime.now()
        if relpath in fileshistory:
            # if hexdigest is present, then no need to add it...? Well, now that you have hashed it, just add it anyways.
            #if hexdigest not in [entry[digesttype] for entry in fileshistory[relpath] if digesttype in entry]:
            fileshistory[relpath].append(digestentry)
        else:
            fileshistory[relpath] = [digestentry]
        return digestentry

    def saveFileshistory(self):
        """
        Persists fileshistory to file.
        """
        fileshistory = self.Fileshistory # This is ok; if _fileshistory is empty, it will try to reload to make sure not to override.
        if not fileshistory:
            logger.info("No fileshistory ('{}')for experiment '{}', aborting saveFileshistory".format(fileshistory, self))
            return
        savetofolder = os.path.join(self.Localdirpath, '.labfluence')
        if not os.path.isdir(savetofolder):
            try:
                os.mkdir(savetofolder)
            except OSError as e:
                logger.warning(e)
                return
        fn = os.path.join(savetofolder, 'files_history.yml')
        yaml.dump(fileshistory, open(fn, 'wb'), default_flow_style=False)

    def loadFileshistory(self):
        """
        Loads the fileshistory from file.
        """
        if not getattr(self, 'Localdirpath', None):
            logger.warning("loadFileshistory was invoked, but experiment has no localfiledirpath. ({})".format(self))
            return
        savetofolder = os.path.join(self.Localdirpath, '.labfluence')
        fn = os.path.join(savetofolder, 'files_history.yml')
        try:
            if self._fileshistory is None:
                self._fileshistory = dict()
            self._fileshistory.update(yaml.load(open(fn)))
            return True
        except OSError as e:
            logger.warning("loadFileshistory error: {}".format(e))
        except IOError as e:
            logger.info("loadFileshistory error: {}".format(e))
        except yaml.YAMLError as e:
            logger.info("loadFileshistory error: {}".format(e))

    def getRelativeStartPath(self, relative):
        """
        Returns the relative path for various elements, e.g.
        - 'exp'  (default)      -> returns self.Localdirpath
        - 'local_exp_subDir'
        - 'local_exp_rootDir'
        """
        if relative is None or relative == 'exp':
            relstart = self.Localdirpath
        elif relative == 'local_exp_subDir':
            relstart = self.Confighandler.get('local_exp_subDir')
        elif relative == 'local_exp_rootDir':
            relstart = self.Confighandler.get('local_exp_rootDir')
        else:
            relstart = relative
        return relstart

    def listLocalFiles(self, relative=None):
        """
        Lists all local files, essentially a lite version of getLocalFilelist
        that makes it clear that the task can be accomplished as a one-liner :-)
        """
        if not self.Localdirpath:
            return list()
        relstart = self.getRelativeStartPath(relative)
        return [os.path.relpath(os.path.join(dirpath, filename),relstart) for dirpath,dirnames,filenames in os.walk(self.Localdirpath) for filename in filenames]



    def getLocalFilelist(self, fn_pattern=None, fn_is_regex=False, relative=None, subentries_only=True, subentry_idxs=None):
        """
        Returns a filtered list of local files in the experiment directory and sub-folders,
        filtering by:
        - fn_pattern
        - fn_is_regex   -> if True, will enterpret fn_pattern as a regular expression.
        - relative       -> relative to what ('exp', 'local_exp_subDir', 'local_exp_rootDir')
        - subentries_only -> only return files from subentry folders and not other files.
        - subentries_idxs -> only return files from from subentries with these subentry indices (sequence)
        """
        # oneliner for listing files with os.walk:
        #print "\n".join("{}:\n{}".format(dirpath,
        #        "\n".join(os.path.join(dirpath, filename) for filename in filenames))for dirpath,dirnames,filenames in os.walk('.') )
        ret = list()
        if not self.Localdirpath:
            return ret
        if subentry_idxs is None:
            subentry_idxs = list()
        relstart = self.getRelativeStartPath(relative)
        # I am not actually sure what is fastest, repeatedly checking "if include_prog and include_prog.match()
        if relative == 'filename-only':
            def file_repr(path, filename, relstart):
                return filename
            def make_tuple(path, filename):
                return ( filename, path, dict(fileName=filename, filepath=path) )
        else:
            def file_repr(dirpath, filename, relstart):
                path = os.path.join(dirpath, filename)
                return os.path.join(os.path.relpath(path, relstart))
            def make_tuple(dirpath, filename):
                path = os.path.join(dirpath, filename)
                return ( os.path.join(os.path.relpath(path, relstart)), path, dict(fileName=filename, filepath=path) )
        if fn_pattern:
            if not fn_is_regex:
                # fnmatch translates into equivalent regex, offers the methods fnmatch, fnmatchcase, filter, re and translate
                fn_pattern = fnmatch.translate(fn_pattern)
            include_prog = re.compile(fn_pattern)
            def appendfile(dirpath, filename):
                # tuple format is (<list_repr>, <identifier>, <metadata>)
                if include_prog.match(filename):
                    ret.append( make_tuple(dirpath, filename ) )
        else:
            # alternative, just do if include_prog is None or include_prog.match(...)
            def appendfile(dirpath, filename):
                ret.append( make_tuple(dirpath, filename ) )

        if subentry_idxs or subentries_only:
            logger.debug("returning filelist using subentries...")
            if not self.Subentries:
                logger.warning("getLocalFilelist() :: subentries requested, but no subentries loaded, aborting.")
                return ret
            for idx,subentry in self.Subentries.items():
                if (subentries_only or idx in subentry_idxs) and 'foldername' in subentry:
                    # perhaps in a try-except clause...
                    for dirpath,dirnames,filenames in os.walk(os.path.join(self.Localdirpath,subentry['foldername'])):
                        for filename in filenames:
                            appendfile(dirpath, filename)
            #print "Experiment.getLocalFilelist() :: Returning list: {}".format(ret)
            return ret
        ignore_pat = self.Confighandler.get('local_exp_ignore_pattern')
        if ignore_pat:
            logger.debug("returning filelist by ignore pattern '{}'".format(ignore_pat))
            ignore_prog = re.compile(ignore_pat)
            for dirpath,dirnames,filenames in os.walk(self.Localdirpath):
                # http://stackoverflow.com/questions/18418/elegant-way-to-remove-items-from-sequence-in-python
                # remember to modify dirnames list in-place:
                #dirnames = filter(lambda d: ignore_prog.search(d) is None, dirnames) # does not work
                #dirnames[:] = filter(lambda d: ignore_prog.search(d) is None, dirnames) # works
                dirnames[:] = ( d for d in dirnames if ignore_prog.search(d) is None ) # works, using generator
                # alternatively, use list.remove() in a for-loop, but remember to iterate backwards.
                # or perhaps even better, iterate over a copy of the list, and remove items with list.remove().
                # if you can control the datatype, you can also use e.g. collections.deque instead of a list.
                logger.debug("filtered dirnames: {}".format(dirnames))
                for filename in filenames:
                    if ignore_prog.search(filename) is None:
                        appendfile(dirpath, filename)
                    else:
                        logger.debug("filename {} matched ignore_pat {}, skipping.".format(filename, ignore_pat))
        else:
            logger.debug("Experiment.getLocalFilelist() - no ignore_pat, filtering from complete filelist...")
            #return [(path, os.path.relpath(path) for dirpath,dirnames,filenames in os.walk(self.Localdirpath) for filename in filenames for path in (appendfile(dirpath, filename), ) if path]
            for dirpath, dirnames, filenames in os.walk(self.Localdirpath):
                for filename in filenames:
                    appendfile(dirpath, filename)
        logger.debug("Experiment.getLocalFilelist() :: Returning list: {}".format(ret))
        return ret


    ###
    ### CODE RELATED TO WIKI PAGE HANDLING
    ###

    def reloadWikipage(self):
        """
        Reload the attached wiki page from server.
        """
        self.WikiPage.reloadFromServer()


    def getWikiXhtml(self, ):
        """
        Get xhtml for wikipage.
        """
        if not self.WikiPage or not self.WikiPage.Struct:
            logger.warning("\nExperiment.getWikiSubentryXhtml() > WikiPage or WikiPage.Struct is None, aborting...")
            logger.warning("-- {} is {}\n".format('self.WikiPage.Struct' if self.WikiPage else self.WikiPage, self.WikiPage.Struct if self.WikiPage else self.WikiPage))
            return
        content = self.WikiPage.Struct['content']
        return content


    def getWikiSubentryXhtml(self, subentry=None):
        """
        Get xhtml (journal) for a particular subentry on the wiki page.
        subentry defaults to self.JournalAssistant.Current_subentry_idx.
        """
        if subentry is None:
            subentry = getattr(self.JournalAssistant, 'Current_subentry_idx', None)
        if not subentry:
            logger.info("No subentry set/selected/available, aborting...")
            return None
        #xhtml = self.WikiPage.getWikiSubentryXhtml(subentry)
        regex_pat_fmt = self.Confighandler.get('wiki_subentry_parse_regex_fmt')
        fmt_params = self.makeFormattingParams(subentry_idx=subentry)
        regex_pat = regex_pat_fmt.format(**fmt_params)
        if not regex_pat:
            logger.warning("No regex pattern found in config, aborting...\n")
            return
        if not self.WikiPage or not self.WikiPage.Struct:
            logger.info("WikiPage or WikiPage.Struct is None, aborting...")
            logger.info("-- {} is {}\n".format('self.WikiPage.Struct' if self.WikiPage else self.WikiPage, self.WikiPage.Struct if self.WikiPage else self.WikiPage))
            return
        content = self.WikiPage.Struct['content']
        regex_prog = re.compile(regex_pat, flags=re.DOTALL)
        match = regex_prog.search(content)
        if match:
            gd = match.groupdict()
            #print "matchgroups:"
            #for k in ('subentry_header', 'subentry_xhtml'):
            #    print "-'{}': {}".format(k, gd[k])
            return "\n".join( gd[k] for k in ('subentry_header', 'subentry_xhtml') )
        else:
            logger.debug("No subentry xhtml found matching regex_pat '%s', derived from regex_pat_fmt '%s'. len(self.WikiPage.Struct['content']) is: %s",
                         regex_pat, regex_pat_fmt, len(self.WikiPage.Struct['content']) )
            return None


    def attachWikiPage(self, pageId=None, pagestruct=None, dosearch=1):
        """
        Searches the server for a wiki page using the experiment's metadata,
        if pageid is already stored in the Props, then using that, otherwise
        searching the servier using e.g. expid, title, etc.
        A WikiPage is only attached (and returned) if a page was found on the server
        (yielding a correct pageid).
        """
        if pageId is None:
            if pagestruct and 'id' in pagestruct:
                pageId = pagestruct['id']
            else:
                pageId = self.Props.get('wiki_pageId', None)
        if (pageId is None and self._wikipage) or (self._wikipage and self._wikipage.PageId == pageId):
            logger.warning("attachWikiPage invoked, but no (new) pageId was provided, and existing wikipage already attached, aborting. If a wrong pageId is registrered, you need to remove it manually.")
            return
        if not pageId and self.Server and dosearch:
            logger.info("(exp with expid=%s), pageId is boolean false, invoking self.searchForWikiPage(%s)...", self.Expid, dosearch)
            pagestruct = self.searchForWikiPage(dosearch)
            if pagestruct:
                logger.debug("searchForWikiPage returned a pagestruct with id: %s", pagestruct['id'])
                self.Props['wiki_pageId'] = pageId = pagestruct['id']
                if self.SavePropsOnChange:
                    self.saveProps()
        logger.debug("Params are: pageId: %s  server: %s   dosearch: %s   pagestruct: %s", pageId, self.Server, dosearch, pagestruct)
        # Does it make sense to create a wikiPage without pageId? No. This check should take care of that:
        if not pageId:
            logger.info("Notice - no pageId found for expid %s (dosearch=%s, self.Server=%s)...", self.Props.get('expid'), dosearch, self.Server)
            return pagestruct
        self.WikiPage = wikipage = WikiPage(pageId, self.Server, pagestruct)
        # Update self.Props for offline access to the title of the wiki page:
        if wikipage.Struct:
            self.Props['wiki_pagetitle'] = self.WikiPage.Struct['title']
        return wikipage


    def searchForWikiPage(self, extended=0):
        """
        extended is used to control how much search you want to do.
        Search strategy:
        1) Find page on wiki in space with pageTitle matching self.Foldername.
        2) Query manager for CURRENT wiki experiment pages and see if there is one that has matching expid.
        3) Query exp manager for ALL wiki experiment pages and see if there is one that has matching expid.
        3) Find pages in space with user as contributor and expid in title.
           # If multiple results are returned, filter pages by parentId matching wiki_exp_root_pageId? No, would be found by #2.
        4) Find pages in all spaces with user as contributor and ...?
        5) Find pages in user's space without user as contributor and expid in title?
        Hmm... being able to define list with multiple spaceKeys and wiki_exp_root_pageId
        would make it a lot easier for users with wikipages scattered in several spaces...?
        Also, for finding e.g. archived wikipages...
        """
        callinfo = logger.findCaller()
        method_repr = "{}.{}".format(self.__class__.__name__, callinfo[2])
        logger.info("%s :: Searching on server...", method_repr)
        spaceKey = self.getConfigEntry('wiki_exp_root_spaceKey')
        pageTitle = self.Foldername or self.getFoldernameFromFmtAndProps() # No reason to make this more complicated...
        user = self.getConfigEntry('wiki_username') or self.getConfigEntry('username')
        try:
            # First try to find a wiki page with an exactly matching pageTitle.
            pagestruct = self.Server.getPage(spaceKey=spaceKey, pageTitle=pageTitle)
            logger.debug("%s :: self.Server.getPage returned pagestruct of type '%s'", method_repr, type(pagestruct))
            if pagestruct:
                logger.info("%s :: Exact match in space '%s' found for page '%s'", method_repr, spaceKey, pageTitle)
                return pagestruct
            else:
                logger.debug("%s :: pagestruct is empty: '%s'", method_repr, pagestruct)
        except xmlrpclib.Fault:
            # perhaps do some searching...?
            # Edit, server.execute might catch xmlrpclib.Fault exceptions;
            logger.info("%s :: xmlrpclib.Fault raised, indicating that no exact match found for '%s' in space '%s', searching by query...", method_repr, pageTitle, spaceKey)
        # Query manager for current wiki pages:
        expid = self.Expid  # uses self.Props
        if self.Manager:
            currentwikipagesbyexpid = self.Manager.CurrentWikiExperimentsPagestructsByExpid # cached_property
            if currentwikipagesbyexpid and expid in currentwikipagesbyexpid:
                return currentwikipagesbyexpid[expid]
        else:
            logger.warning("Experiment %s has no ExperimentManager.", expid)
        # Perform various searches on the wiki:
        if extended > 0:
            params = dict(spaceKey=spaceKey, contributor=user)
            params['type'] = 'page'
            logger.info("%s :: performing slightly more extended search with intitle='%s' and params: %s", method_repr, expid, params)
            result = self.searchForWikiPageWithQuery(expid, parameters=params, intitle=expid)
            if result:
                return result
            elif result is 0 and extended > 1:
                # searchForWikiPageWithQuery found zero matching pages, try to search all spaces:
                params2 = params
                params2.pop('spaceKey')
                logger.debug("%s :: performing even more extended search with intitle='%s' and params: %s", method_repr, expid, params)
                result = self.searchForWikiPageWithQuery(expid, parameters=params, intitle=expid)
                if result:
                    logger.debug("%s :: a single hit found of type '%s'", method_repr, result)
                    return result
                # and again, now excluding user as contributor (perhaps someone else wrote the entry...)
                params2 = params
                params2.pop('contributor')
                logger.debug("%s :: performing next extended search with intitle='%s' and params: %s", method_repr, expid, params)
                result = self.searchForWikiPageWithQuery(expid, parameters=params, intitle=expid)
                if result:
                    logger.debug("%s :: a single hit found of type '%s'", method_repr, result)
                    return result
            else:
                # Too many results? Perhaps two or something?
                logger.debug("Experiment.searchForWikiPage() :: Unable to find unique page result, aborting...")
                return None
        logger.debug("%s :: Unable to locate wiki page. Returning None...", method_repr)


    def searchForWikiPageWithQuery(self, query, parameters, intitle=None, title_regex=None, content_regex=None, singleMatchOnly=True):
        """
        Unless singleMatchOnly is set to False, this method will return
        no more than a single wikiPage, or fail with one of the following:
        - 0 = Zero results found.
        - False = More than one result found.

        ## Todo: allow for 'required' and 'optional' arguments.
        ## TODO: Enable title_regex search (must be done on client side)
        ## TODO: Enable content regex search (must also be done on client side)
        """
        server = self.Server
        if not server:
            # Server might be None or a server instance with attribute _connectionok value of either
            # of 'None' (not tested) or False (last connection failed) or True (last connection succeeded).
            logger.info("searchForWikiPageWithQuery() > Server is None or not connected, aborting.")
            return
        results = server.search(query, 10, parameters)
        # Unfortunately, server results only contains: title, url, excerpt, type, id.
        if intitle:
            results = filter(lambda page: intitle in page['title'], results)
        #if len(results) > 1:
        #    logger.debug("Results before filtering by parentId: %s", len(results))
        #    results = filter(lambda page: page['parentId']==preferparentid, results)
        #    logger.debug("Results after filtering by parentId: %s", len(results))
        if not singleMatchOnly:
            return results
        if len(results) > 1:
            logger.info("Experiment.searchForWikiPageWithQuery() :: Many hits found, but only allowed to return a single match:\n%s",
            "\n".join( "{} ({})".format(page['title'], page['id']) for page in results ) ) # in space '{}', pageTitle '{}'".format(spaceKey, pagestruct['title'])
            #logger.info("\n".join( "{} ({})".format(page['title'], page['id']) for page in results ))
            return False
        if len(results) < 1:
            return 0
        if len(results) == 1:
            pagestruct = results[0]
            logger.info("pagestruct keys: %s", pagestruct.keys() )
            # pagestruct keys returned for a server search is: 'id', 'title', 'type', 'url', 'excerpt'
            logger.info("Experiment.searchForWikiPageWithQuery() :: A single hit found : '%s: %s: %s'",
                          pagestruct['space'], pagestruct['id'], pagestruct['title'] )
            return pagestruct


    def makeWikiPage(self, pagefactory=None):
        """
        Unlike attachWikiPage which attempts to attach an existing wiki page,
        this method creates a new wiki page and persists it to the server.
        Changes:
        - Removed , dosave=True argument
            Props should always be saved/persisted after making a wiki page,
            otherwise the pageId might be lost.
        """
        if not (self.Server and self.Confighandler):
            logger.error("Experiment.makeWikiPage() :: FATAL ERROR, no server and/or no confighandler.")
            return
        if pagefactory is None:
            pagefactory = WikiPageFactory(self.Server, self.Confighandler)
        current_datetime = datetime.now()
        fmt_params = dict(datetime=current_datetime,
                          date=current_datetime)
        fmt_params.update(self.Props)
        self.WikiPage = pagefactory.new('exp_page', fmt_params=fmt_params)
        self.Props['wiki_pageId'] = self.WikiPage.Struct['id']
        #if dosave or self.SavePropsOnChange:
        # edit: always save/persist props after making a wiki page, otherwise the pageId might be lost.
        self.saveProps()
        return self.WikiPage


    def makeWikiSubentry(self, subentry_idx, subentry_titledesc=None, updateFromServer=True, persistToServer=True):
        """
        Edit: This has currently been delegated to self.JournalAssistant, which specializes in inserting
        content at the right location using regex'es.
        """
        if subentry_idx not in self.Subentries:
            logger.info("Experiment.makeWikiSubentry() :: ERROR, subentry_idx '{}' not in self.Subentries; make sure to first add the subentry to the subentries list and _then_ add a corresponding subentry on the wikipage.".format(subentry_idx))
            return
        res = self.JournalAssistant.newExpSubentry(subentry_idx, subentry_titledesc=subentry_titledesc, updateFromServer=updateFromServer, persistToServer=persistToServer)
        # pagetoken = where to insert the new subentry on the page, typically before <h2>Results and discussion</h2>.
        #pagetoken = self.getConfigEntry('wiki_exp_new_subentry_token') # I am no longer using tokens, but relying on regular expressions to find the right insertion spot.
        self.saveIfChanged()
        return res


    def uploadAttachment(self, filepath, att_info=None, digesttype='md5'):
        """
        Upload attachment to wiki page.
        Returns True if succeeded, False if failed and None if no attemt was made to upload due to a local Error.
        Fields for attachmentInfo are:
            Key         Type    Value
            id          long    numeric id of the attachment
            pageId      String  page ID of the attachment
            title       String  title of the attachment
            fileName    String  file name of the attachment (Required)
            fileSize    String  numeric file size of the attachment in bytes
            contentType String  mime content type of the attachment (Required)
            created     Date    creation date of the attachment
            creator     String  creator of the attachment
            url         String  url to download the attachment online
            comment     String  comment for the attachment (Required)
        """
        logger.warning("Experiment.uploadAttachment() :: Not tested yet - take care ;)")
        if not getattr(self, 'WikiPage', None):
            logger.error("Experiment.uploadAttachment() :: ERROR, no wikipage attached to this experiment object\n - {}".format(self))
            return None
        if not os.path.isabs(filepath):
            filepath = os.path.normpath(os.path.join(self.Localdirpath, filepath))
        # path relative to this experiment, e.g. 'RS123d subentry_titledesc/RS123d_c1-grid1_somedate.jpg'
        from model.utils import attachmentTupFromFilepath
        attachmentInfo, attachmentData = attachmentTupFromFilepath(fp)
        # NOTE: CONF-31169 and CONF-30024.
        # - attachment title ignored when adding attachment
        # - RemoteAttachment.java does not have a comment setter.
        relpath = os.path.relpath(filepath, self.Localdirpath)
        mimetype = getmimetype(filepath)
        #attachmentInfo['contentType'] = mimetype
        #attachmentInfo.setdefault('comment', os.path.basename(filepath) )
        #attachmentInfo.setdefault('fileName', os.path.basename(filepath) )
        #attachmentInfo.setdefault('title', os.path.basename(relpath) )
        attachmentInfo.update(att_info)
        if digesttype:
            digestentry = self.hashFile(filepath, (digesttype, ))
            attachmentInfo['comment'] = attachmentInfo.get('comment', '') \
                + "; {}-hexdigest: {}".format(digesttype, digestentry[digesttype])
        with open(filepath, 'rb') as f:
            # Not sure exactly what format the file bytes should have.
#            attachmentData = f # Is a string/file-like object ok?
#            attachmentData = f.read() # Can I just load the bytes?
            # Should I do e.g. base64 encoding of the bytes?
            attachmentData = xmlrpclib.Binary(f.read())# as seen in https://confluence.atlassian.com/display/DISC/Upload+attachment+via+Python+XML-RPC
            attachment = self.WikiPage.addAttachment(attachmentInfo, attachmentData)
        return attachment


    def getUpdatedAttachmentsList(self):
        """
        Updates the attachments cache by resetting the listAttachements cache
        and then returning self.Attachments.
        Returns updated list of attachments (or empty list if server query failed).
        """
        # Reset the cache:
        del self._cache['Attachments']
        structs = self.Attachments
        if not structs:
            logger.info( "Experiment.updateAttachmentsCache() :: listAttachments() returned '%s'", structs )
        return structs


    #@cached_property(ttl=300)
    # edit: cached_property makes the method a property and can no longer be used as a method.
    # I have moved the caching to the Attachments property instead...
    def listAttachments(self):
        """
        Lists attachments on the wiki page.
        Returns a list of attachments (structs) if succeeded, and empty list if failed.
        https://developer.atlassian.com/display/CONFDEV/Remote+Confluence+Data+Objects#RemoteConfluenceDataObjects-attachmentAttachment
        attachment-struct has:
        - comment (string, required)
        - contentType (string, required)
        - created (date)
        - creator (string username)
        - fileName (string, required)
        - fileSize (string, number of bytes)
        - id (string, attachmentId)
        - pageId (string)
        - title (string)
        - url (string)
        """
        if not getattr(self, 'WikiPage', None):
            logger.info("Experiment.uploadAttachment() :: ERROR, no wikipage attached to this experiment object\n - {}".format(self))
            return list()
        #logger.warning("Experiment.listAttachments() :: Not implemented yet - take care ;)")
        attachment_structs = self.WikiPage.getAttachments()
        if attachment_structs is None:
            logger.debug("exp.WikiPage.getAttachments() returned None, likely because the server it not connected.")
            return list()
        return attachment_structs



    def getAttachmentList(self, fn_pattern=None, fn_is_regex=False, **filterdict):
        """
        The wiki-attachments equivalent to getLocalFileslist(),
        Returns a tuple list of (<display>, <identifier>, <complete struct>) elements.
        Like getLocalFileslist, the returned list can be filtered based on
        filename pattern (glob; or regex if fn_is_regex is True).
        The filterdict kwargs are currently not used.
        However, when needed, this could be used to filter the returned list based on
        attachment metadata, which includes:
        - comment (string)
        - contentType (string)
        - created (date)
        - creator (string username)
        - fileName (string, required)
        - fileSize (string, number of bytes)
        - id (string, attachmentId)
        """
        struct_list = self.Attachments
        if not struct_list:
            return list()
        # Returned tuple of (<display>, <identifier>, <complete struct>)
        # I think either filename or id would work as identifier.
        if fn_pattern:
            if not fn_is_regex:
                fn_pattern = fnmatch.translate(fn_pattern)
            regex_prog = re.compile(fn_pattern)
        else:
            regex_prog = None
        # attachment struct_list might be None or False, so must check before trying to iterate:
        return [ (struct['fileName'], struct['id'], struct) for struct in struct_list \
                    if regex_prog is None or regex_prog.match(struct['fileName']) ]


    ### Other stuff...###

    def __repr__(self):
        #return "Experiment in ('{}'), with Props:\n{}".format(self.Localdirpath, yaml.dump(self.Props))
        try:
            return "e>"+self.Confighandler.get('exp_series_dir_fmt').format(**self.Props)
        except KeyError:
            logger.debug("KeyError for 'return e>+self.Confighandler.get('exp_series_dir_fmt').format(**self.Props)'")
            return "e>"+str(getattr(self, 'Foldername', '<no-foldername>'))+str(self.Props)

    def update(self, other_exp):
        """
        Update this experiment with the content from other_exp.
        """
        #raise NotImplementedError("Experiment.update is not implemented...")
        logger.warning( "update not implemented..." )



if __name__ == '__main__':
    import glob


    logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():\n%(message)s\n"
    logging.basicConfig(level=logging.INFO, format=logfmt)
    logging.getLogger("__main__").setLevel(logging.DEBUG)
    #logging.getLogger("server").setLevel(logging.DEBUG)
