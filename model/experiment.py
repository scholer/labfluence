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

import os
import yaml
import re
from datetime import datetime
from collections import OrderedDict
import xmlrpclib
import hashlib
import fnmatch

from confighandler import ExpConfigHandler
from server import ConfluenceXmlRpcServer
from page import WikiPage, WikiPageFactory
from journalassistant import JournalAssistant
from utils import *




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


    def __init__(self, localdir=None, props=None, server=None, manager=None, confighandler=None, wikipage=None, regex_match=None, VERBOSE=0,
                 doparseLocaldirSubentries=True, subentry_regex_prog=None, loadYmlFn='.labfluence.yml',
                 autoattachwikipage=True, doserversearch=False, savepropsonchange=True):
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

        self.VERBOSE = VERBOSE
        self._server = server
        self._manager = manager
        self.Confighandler = confighandler
        self.WikiPage = wikipage
        self.SavePropsOnChange = savepropsonchange
        self.PropsChanged = False # Flag,
        self.Subentries_regex_prog = subentry_regex_prog # Allows recycling of a single compiled regex for faster directory tree processing.
        self.ConfigFn = loadYmlFn
        self._attachments_cache = None # cached list of wiki attachment_structs. None = <not initialized>

        if localdir is None:
            if 'localdir' in props:
                localdir = props.get('localdir')
            else:
                print "\n\nExperiment.__init__() :: CRITICAL: No localdir provided; functionality of this object will be greatly reduced and may break at any time.\n\n"
                self.Localdirpath = None
                self.Foldername = None
                self.Parentdirpath = None
        else:
            # More logic may be required, e.g. if the dir is relative to e.g. the local_exp_rootDir.
            parentdirpath, foldername = os.path.split(localdir)
            if not parentdirpath:
                # The path provided was relative, e.g. "RS102 Strep-col11 TR annealed with biotin".
                # Assume that the experiment is based in the local_exp_subDir:
                parentdirpath = self.getConfigEntry('local_exp_subDir')
            self.Parentdirpath = parentdirpath
            if not foldername:
                print "Experiment.__init__() :: Warning, could not determine foldername...????"
            self.Foldername = foldername
            self.Localdirpath = os.path.join(self.Parentdirpath, self.Foldername)
            #self.Localdir = localdir # Currently not updating; this might be relative...


        """ Experiment properties/config related """
        """ Manual handling is deprecated; Props are now a property that deals soly with confighandler."""
        if self.VERBOSE:
            print "Experiment.__init__() :: Props already in HierarchicalConfig cfg: \n{}".format(self.Props)
        if props:
            self.Props.update(props)
            if self.VERBOSE:
                print "Experiment self.Props updated with props argument, is now {}".format(self.Props)
        if regex_match:
            gd = regex_match.groupdict()
            """ regex is often_like "(?P<expid>RS[0-9]{3}) (?P<exp_title_desc>.*)" """
            self.Props.update(gd)
        elif not 'expid' in self.Props:
            # self.Props is still too empty. Attempt to populate it using 1) the localdirpath and 2) the wikipage.
            exp_regex = self.getConfigEntry('exp_series_regex')
            exp_regex_prog = re.compile(exp_regex)
            regex_match = self.updatePropsByFoldername(exp_regex_prog)
            if not regex_match and wikipage: # equivalent to 'if wikipage and not regex_match', but better to check first:
                regex_match = self.updatePropsByWikipage(exp_regex_prog)

        """ Subentries related..."""
        # Subentries is currently an element in self.Props, makes it easier to save info...
        self.Subentries = self.Props.setdefault('exp_subentries', OrderedDict())
        if doparseLocaldirSubentries and self.Localdirpath:
            self.parseLocaldirSubentries()

        """
        I plan to allow for saving file histories, having a dict
        Fileshistory['RS123d subentry_titledesc/RS123d_c1-grid1_somedate.jpg'] -> list of {datetime:<datetime>, md5:<md5digest>} dicts.
        This will make it easy to detect simple file moves/renames and allow for new digest algorithms.
        """
        #self.loadFileshistory()
        if not self.WikiPage:
            wikipage = self.attachWikiPage(dosearch=doserversearch)
        if self.WikiPage and self.WikiPage.Struct:
            self.Props['wiki_pagetitle'] = self.WikiPage.Struct['title']
        self.JournalAssistant = JournalAssistant(self)
        if self.VERBOSE:
            print "Experiment.__init__() :: Props (at end of init): \n{}".format(self.Props)



    """ ATTRIBUTE PROPERTIES: """
    @property
    def Props(self):
        if getattr(self, 'Localdirpath', None):
            return self.Confighandler.getExpConfig(self.Localdirpath)
        props_cache = self.Confighandler.get('expprops_by_id_cache')
        if props_cache and getattr(self, '_expid', None):
            return props_cache.setdefault(self._expid, dict())
        else:
            print "Warning, no localdirpath provided for this experiment and no props_cache or no self._expid."
            if not hasattr(self, '_props'):
                self._props = dict()
            return self._props

    def getUrl(self, ):
        url = self.Props.get('url', None)
        if not url:
            if self.WikiPage and self.WikiPage.PageStruct:
                url = self.WikiPage.PageStruct.get('url', None)
        if not url:
            # perhaps use the pageId to generate a url (via the server and the wiki_url or perhaps wiki_url_bypageId_fmt).
            pass
        return url


    @property
    def Subentries(self):
        return self.Props.setdefault('exp_subentries', OrderedDict())
    @Subentries.setter
    def Subentries(self, subentries):
        self.Props['exp_subentries'] = subentries

    @property
    def Attachments(self):
        """
        Only update if a server is available...
        """
        if self.Server and self._attachments_cache is None:
            self.updateAttachmentsCache()
        return self._attachments_cache

    @property
    def Server(self, ):
        #print "self._server: {}".format(self._server)
        #print "self.Confighandler.Singletons: {}".format(self.Confighandler.Singletons)
        return self._server or self.Confighandler.Singletons.get('server')
    @property
    def Manager(self, ):
        return self._manager or self.Confighandler.Singletons.get('manager')


    def updateAttachmentsCache(self):
        structs = self.listAttachments()
        if not structs:
            print "Experiment.updateAttachmentsCache() :: listAttachments() returned '{}', aborting".format(structs)
        self._attachments_cache = structs


    """ Macro methods: """

    def saveAll(self):
        """
        Method for remembering to do all things that must be saved before closing experiment.
         - self.Props, dict in .labfluence.yml
         - self.Fileshistory, dict in .labfluence/files_history.yml
        What else is stored in <localdirpath>/.labfluence/ ??
         - what about journal assistant files?
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
            return self.Confighandler.get(cfgkey, default=default, path=self.Localdirpath)

    def setConfigEntry(self, cfgkey, value):
        if cfgkey in self.Props:
            self.Props[cfgkey] = value
        else:
            # does not currently check the hierarchical config, only the explicidly loaded 'system', 'user', 'exp', 'cache', etc.
            self.Confighandler.setkey(cfgkey, value)

    def getAbsPath(self):
        return os.path.abspath(self.Localdirpath)



    def saveIfChanged(self):
        if self.PropsChanged:
            self.saveProps()
            self.PropsChanged = False


    def saveProps(self, path=None):
        """
        Saves content of self.Props to file.
        If a confighandler is attached, allow it to do it; otherwise just persist as yaml to default location.
        """
        if self.VERBOSE:
            print "(Experiment.saveProps() triggered; confighandler: {}".format(self.Confighandler)
            if self.VERBOSE > 2:
                print "self.Props: {}".format(self.Props)
        if path is None:
            path = self.Localdirpath
        if self.Confighandler:
            if not os.path.isdir(path):
                path = os.path.dirname(path)
            if self.VERBOSE > 3:
                print "\nself.Confighandler.updateAndPersist(path, self.Props) ->"
                print path
                print self.Props
                print "\n"
            self.Confighandler.updateAndPersist(path, self.Props)
        else:
            print "Experiment.saveProps() :: No confighandler, saving manually..."
            if os.path.isdir(path):
                path = os.path.normpath(os.path.join(self.Localdirpath, self.ConfigFn))
            print "Experiment.saveProps() :: saving directly to file '{}' (not using confighandler)".format(path)
            yaml.dump(self.Props, open(path, 'wb'))
        if self.VERBOSE > 4:
            print "\nContent of exp config/properties file after save:"
            print open(os.path.join(path,self.ConfigFn)).read()



    def updatePropsByFoldername(self, regex_prog=None):
        if regex_prog is None:
            exp_regex = self.getConfigEntry('exp_series_regex')
            regex_prog = re.compile(exp_regex)
        regex_match = regex_prog.match(self.Foldername)
        if regex_match:
            self.Props.update(regex_match.groupdict())
            if self.SavePropsOnChange:
                self.saveProps()
        return regex_match

    def updatePropsByWikipage(self, regex_prog=None):
        if regex_prog is None:
            exp_regex = self.getConfigEntry('exp_series_regex')
            regex_prog = re.compile(exp_regex)
        wikipage=self.WikiPage
        if not wikipage.Struct:
            wikipage.reloadFromServer()
        regex_match = regex_prog.match(wikipage.Struct.get('title'))
        if regex_match:
            self.Props.update(regex_match.groupdict())
            if self.SavePropsOnChange:
                self.saveProps()
        return regex_match




    def makeFormattingParams(self, subentry_idx=None, props=None):
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



    """ STUFF RELATED TO SUBENTRIES """

    def sortSubentrires(self):
        #org_keyorder = self.Subentries.keys()
        if self.Subentries.keys() == sorted(self.Subentries.keys()):
            return
        self.Props['exp_subentries'] = self.Subentries = OrderedDict(sorted(self.Subentries.items()) )


    def addNewSubentry(self, subentry_titledesc, subentry_idx=None, subentry_date=None, extraprops=None, makefolder=False, makewikientry=False):
        if subentry_idx is None:
            subentry_idx = self.getNewSubentryIdx()
        if subentry_idx in self.Subentries:
            print "Experiment.addNewSubentry() :: ERROR, subentry_idx '{}' already listed in subentries, aborting...".format(subentry_idx)
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


    def makeSubentryFolder(self, subentry_idx):
        if subentry_idx not in self.Subentries:
            print "Experiment.makeSubentryFolder() :: ERROR, subentry_idx '{}' not listed in subentries, aborting...".format(subentry_idx)
            return
        subentry = self.getSubentry(subentry_idx)
        fmt_params = self.makeFormattingParams(subentry_idx=subentry_idx, props=subentry)
#        print "fmt_params: {}"
        subentry_foldername_fmt = self.getConfigEntry('exp_subentry_dir_fmt')
        subentry_foldername = subentry_foldername_fmt.format(**fmt_params)
        newfolderpath = os.path.join(self.Localdirpath, subentry_foldername)
        if os.path.exists(newfolderpath):
            print "\nExperiment.makeSubentryFolder() :: ERROR, newfolderpath already exists, aborting...\n--> '{}'".format(newfolderpath)
            return
        try:
            os.mkdir(newfolderpath)
        except OSError as e:
            print "\n{}\nExperiment.makeSubentryFolder() :: ERROR, making new folder:\n--> '{}'".format(e, newfolderpath)
            return False
        subentry['foldername'] = subentry_foldername
        if self.SavePropsOnChange:
            self.saveProps()
        return subentry_foldername


    def getSubentry(self, subentry_idx, default='getSubentry-not-set', ensureExisting=False):
        """
        I want to raise KeyError if default is not given (like dict does).
        However, how to set default to allow it to be optional, but allowing the
        user to set it to e.g. None. It is very likely that the user would want to get
        'None' returned instead of having a KeyError value raised.
        """
        if subentry_idx not in self.Subentries and ensureExisting:
            self.initSubentriesUpTo(subentry_idx)
        if default != 'getSubentry-not-set':
            return self.Subentries.get(subentry_idx, default)
        else:
            return self.Subentries[subentry_idx]

    def initSubentriesUpTo(self, subentry_idx):
        if not self.Subentries:
            self.Subentries = OrderedDict()
        for idx in idx_generator(subentry_idx):
            if idx not in self.Subentries:
                self.Subentries[idx] = dict()

    def getExpRepr(self, default=None):
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
        if subentry_idx:
            subentry = self.getSubentry(subentry_idx, default=None)
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
        if default=='exp':
            return self.getExpRepr()
        else:
            return default

    @property
    def Subentries_regex_prog(self):
        regex_prog = getattr(self, '_subentries_regex_prog', None)
        if regex_prog:
            return regex_prog
        else:
            regex_str = self.getConfigEntry('exp_subentry_regex') #getExpSubentryRegex()
            if not regex_str:
                print "Warning, no exp_subentry_regex entry found in config, reverting to hard-coded default."
                regex_str = "(?P<date1>[0-9]{8})?[_ ]*(?P<expid>RS[0-9]{3})-?(?P<subentry_idx>[^_ ])[_ ]+(?P<subentry_titledesc>.+?)\s*(\((?P<date2>[0-9]{8})\))?$"
            self._subentries_regex_prog = re.compile(regex_str)
            return self._subentries_regex_prog
    @Subentries_regex_prog.setter
    def Subentries_regex_prog(self, value):
        self._subentries_regex_prog = value



    def parseLocaldirSubentries(self, directory=None):
        """
        make self.Subentries by parsing local dirs like '20130106 RS102f PAGE of STV-col11 TR staps (20010203)'.

        """
        if directory is None:
            directory = self.Localdirpath
        if directory is None:
            print "Experiment.parseLocaldirSubentries() :: ERROR, no directory provided and no localdir in Props attribute."
            return
        # Consider using glob.re
        regex_prog = self.Subentries_regex_prog
        localdirs = sorted([dirname for dirname in os.listdir(directory) if os.path.isdir(os.path.abspath(os.path.join(directory, dirname) ) ) ])
        if self.VERBOSE:
            print "Experiment.parseLocaldirSubentries() :: self.Props:\n{}".format(self.Props)
        subentries = self.Props.setdefault('exp_subentries', OrderedDict())
        if self.VERBOSE:
            print "Experiment.parseLocaldirSubentries() :: searching in directory '{}'".format(directory)
            print "Experiment.parseLocaldirSubentries() :: regex = '{}'".format(regex_prog.pattern)
            print "Experiment.parseLocaldirSubentries() :: localdirs = {}".format(localdirs)
            print "Experiment.parseLocaldirSubentries() :: subentries (before read:) = \n{}\n".format(subentries)
        for foldername in localdirs:
            res = regex_prog.match(foldername)
            if self.VERBOSE:
                print "\n\n{} found when testing '{}' dirname against regex '{}'".format("MATCH" if res else "No match", foldername, regex_prog.pattern)
            if res:
                props = res.groupdict()
                # I allow for regex with multiple date entries, i.e. both first and last.
                datekeys = filter(lambda x: 'date' in x and len(x)>4, props.keys())
                for k in sorted(datekeys):
                    val = props.pop(k)
                    if val:
                        props['date']=val
                props['foldername'] = foldername
                #if 'subentry_idx' in props:
                current_idx = props['subentry_idx']
                # edit: how could subentry_idx possibly not be in res.groupdict? only if not included in regex?
                # anyways, if not present, simply making a new index could be dangerous; what if the directories are not sorted and the next index is not right?
                #else:
                #    current_idx =  self.getNewSubentryIdx() # self.subentry_index_increment(current_idx)
                subentries.setdefault(current_idx, dict()).update(props)


    def getNewSubentryIdx(self):
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
            print "No 'exp_subentry_dir_fmt' found in config; aborting"
            return
        for subentry in self.Subentries.values():
            # subentry is a dict
            newname = dir_fmt.format(subentry)
            newname_full = os.path.join(self.Localdirpath, newname)
            if 'dirname' in subentry:
                oldname_full = os.path.join(self.Localdirpath, subentry['dirname'])
                print "Renaming subentry folder: {} -> {}".format(oldname_full, newname_full)
                #os.rename(oldname_full, newname_full)
            elif createNonexisting:
                print "Making new subentry folder: {}".format(newname_full)
                #os.mkdir(newname_full)
            subentry['dirname'] = newname


    def renameFolderByFormat(self):
        """
        Renames the local directory folder to match the formatting dictated by exp_series_dir_fmt.
        Also takes care to update the confighandler.
        """
        dir_fmt = self.getConfigEntry('exp_series_dir_fmt')
        if not dir_fmt:
            print "No 'exp_series_dir_fmt' found in config; aborting"
            return
        newname = dir_fmt.format(self.Props)
        newname_full = os.path.join(self.Parentdirpath, newname)
        oldname = self.Foldername
        oldname_full = self.Localdirpath
        print "Renaming exp folder: {} -> {}".format(oldname_full, newname_full)
        #os.rename(oldname_full, newname_full)
        self.Localdirpath = newname_full
        self.Foldername = newname
        # Note: there is NO reason to have a key 'dirname' in self.Props;
        if self.Confighandler:
            self.Confighandler.renameConfigKey(oldname_full, newname_full)


    def hashFile(self, filepath, digesttypes=('md5', ), save_in_history=True):
        """
        Default is currently md5, although e.g. sha1 is not that much slower.
        The sha256 and sha512 are approx 2x slower than md5, and I dont think that is requried.

        Returns digestentry dict {datetime:datetime.now(), <digesttype>:digest }
        """
        print "Experiment.hashFile() :: Not tested yet - take care ;)"
        if not os.path.isabs(filepath):
            filepath = os.path.normpath(os.path.join(self.Localdirpath, filepath))
        relpath = os.path.relpath(filepath, self.Localdirpath)
        digestentry = dict(datetime=datetime.now())
        for digesttype in digesttypes:
            with open(filepath, 'rb') as f:
                m = hashlib.new(digesttype) # generic; can also be e.g. hashlib.md5()
                # md5 sum default is 128 = 2**7-bytes digest block. However, file read is faster for e.g. 8 kb blocks.
                # http://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
                for chunk in iter(lambda: f.read(128*m.block_size), b''):
                    m.update(chunk)
                hexdigest = m.hexdigest()
                digestentry[digesttype] = hexdigest
            if relpath in self.Fileshistory:
                if hexdigest not in [entry[digesttype] for entry in self.Fileshistory[relpath] if digesttype in entry]:
                    self.Fileshistory[relpath].append(d)
                # if hexdigest is present, then no need to add it...
            else:
                self.Fileshistory[relpath] = [d]
        return digestentry

    def saveFileshistory(self):
        savetofolder = os.path.join(self.Localdirpath, '.labfluence')
        if not os.path.isdir(savetofolder):
            try:
                os.mkdir(savetofolder)
            except OSError as e:
                print e
                return
        fn = os.path.join(savetofolder, 'files_history.yml')
        yaml.dump(self.Fileshistory, open(fn, 'wb'), default_flow_style=False)

    def loadFileshistory(self):
        if not getattr(self, 'Localdirpath', None):
            return
        savetofolder = os.path.join(self.Localdirpath, '.labfluence')
        fn = os.path.join(savetofolder, 'files_history.yml')
        try:
            self.Fileshistory = yaml.load(open(fn))
            return True
        except OSError as e:
            print e
        except IOError as e:
            print e
        except yaml.YAMLError as e:
            print e
        # If self.Fileshistory is already set, I dont think you should set to empty dict if read failed.
        if not getattr(self, 'Fileshistory', None):
            self.Fileshistory = dict()

    def getRelativeStartPath(self, relative):
        if relative is None or relative=='exp':
            relstart = self.Localdirpath
        elif relative == 'local_exp_subDir':
            relstart = self.Confighandler.get('local_exp_subDir')
        elif relative == 'local_exp_rootDir':
            relstart = self.Confighandler.get('local_exp_rootDir')
        else:
            relstart = relative
        return relstart

    def listLocalFiles(self, relative=None):
        if not self.Localdirpath:
            return list()
        relstart = self.getRelativeStartPath(relative)
        return [os.path.relpath(os.path.join(dirpath, filename),relstart) for dirpath,dirnames,filenames in os.walk(self.Localdirpath) for filename in filenames]



    def getLocalFilelist(self, fn_pattern=None, fn_is_regex=False, relative=None, subentries_only=True, subentry_idxs=list()):
        # oneliner for listing files with os.walk:
        #print "\n".join("{}:\n{}".format(dirpath,
        #        "\n".join(os.path.join(dirpath, filename) for filename in filenames))for dirpath,dirnames,filenames in os.walk('.') )
        ret = list()
        if not self.Localdirpath:
            return ret
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
            print "returning filelist using subentries..."
            if not self.Subentries:
                print "getLocalFilelist() :: subentries requested, but no subentries loaded, aborting."
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
            print "returning filelist by ignore pattern '{}'".format(ignore_pat)
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
                print "filtered dirnames: {}".format(dirnames)
                for filename in filenames:
                    if ignore_prog.search(filename) is None:
                        appendfile(dirpath, filename)
                    else:
                        print "filename {} matched ignore_pat {}, skipping.".format(filename, ignore_pat)
        else:
            print "Experiment.getLocalFilelist() - no ignore_pat, filtering from complete filelist..."
            #return [(path, os.path.relpath(path) for dirpath,dirnames,filenames in os.walk(self.Localdirpath) for filename in filenames for path in (appendfile(dirpath, filename), ) if path]
            for dirpath,dirnames,filenames in os.walk(self.Localdirpath):
                for filename in filenames:
                    appendfile(dirpath, filename)
        print "Experiment.getLocalFilelist() :: Returning list: {}".format(ret)
        return ret


    """
    STUFF RELATED TO WIKI PAGE HANDLING
    """

    def getWikiXhtml(self, ):
        if not self.WikiPage or not self.WikiPage.Struct:
            print "\nExperiment.getWikiSubentryXhtml() > WikiPage or WikiPage.Struct is None, aborting..."
            print "-- {} is {}\n".format('self.WikiPage.Struct' if self.WikiPage else self.WikiPage, self.WikiPage.Struct if self.WikiPage else self.WikiPage)
            return
        content = self.WikiPage.Struct['content']
        return content


    def getWikiSubentryXhtml(self, subentry=None):
        if subentry is None:
            subentry = getattr(self.JournalAssistant, 'Current_subentry_idx', None)
        if not subentry:
            print "\nExperiment.getWikiSubentryXhtml() > No subentry provided, aborting...\n"
            return None
        #xhtml = self.WikiPage.getWikiSubentryXhtml(subentry)
        regex_pat_fmt = self.Confighandler.get('wiki_subentry_parse_regex_fmt')
        fmt_params = self.makeFormattingParams(subentry_idx=subentry)
        regex_pat = regex_pat_fmt.format(**fmt_params)
        if not regex_pat:
            print "\nExperiment.getWikiSubentryXhtml() > No regex pattern found in config, aborting...\n"
            return
        if not self.WikiPage or not self.WikiPage.Struct:
            print "\nExperiment.getWikiSubentryXhtml() > WikiPage or WikiPage.Struct is None, aborting..."
            print "-- {} is {}\n".format('self.WikiPage.Struct' if self.WikiPage else self.WikiPage, self.WikiPage.Struct if self.WikiPage else self.WikiPage)
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
            print "\nWikiPage.getWikiSubentryXhtml() > No match found?"
            print "regex_pat_fmt: {}".format(regex_pat_fmt)
            #print "fmt_params: {}".format(fmt_params)
            print "regex_pat: {}".format(regex_pat)
            print "len(self.WikiPage.Struct['content']) is: {}".format(len(self.WikiPage.Struct['content']))
            return None


    def attachWikiPage(self, pageId=None, pagestruct=None, dosearch=False):
        if pageId is None:
            if pagestruct and 'id' in pagestruct:
                pageId = pagestruct['id']
            else:
                pageId = self.Props.get('wiki_pageId', None)
        if not pageId and self.Server and dosearch:
            print "Experiment.attachWikiPage() :: Searching on server..."
            pagestruct = self.searchForWikiPage()
            if pagestruct:
                self.Props['wiki_pageId'] = pageId = pagestruct['id']
                if self.SavePropsOnChange:
                    self.saveProps()
        print "Experiment.attachWikiPage() :: pageId: {}  server: {}   dosearch: {}   pagestruct: {}".format(pageId, self.Server, dosearch, pagestruct)
        if not pageId:
            print "Experiment.attachWikiPage() :: Notice - no pageId found for exp {} (dosearch={}, self.Server={})...\n".format(self.Props.get('expid'), dosearch, self.Server)
            return pagestruct
        self.WikiPage = WikiPage(pageId, self.Server, pagestruct, VERBOSE=self.VERBOSE)
        return self.WikiPage


    def searchForWikiPage(self, extended=0):
        """
        extended is used to control how much search you want to do.
        """
        print "Experiment.searchForWikiPage() :: Searching on server..."
        spaceKey = self.getConfigEntry('wiki_exp_root_spaceKey')
        pageTitle = self.Foldername # No reason to make this more complicated...
        user = self.getConfigEntry('wiki_username') or self.getConfigEntry('username')
        try:
            pagestruct = self.Server.getPage(spaceKey=spaceKey, pageTitle=pageTitle)
            pageId = pagestruct['id']
            print "\nExperiment.searchForWikiPage() :: Exact match in space '{}' found for page '{}'".format(spaceKey, pageTitle)
            return pagestruct
        except xmlrpclib.Fault:
            # perhaps do some searching...?
            print "\nExperiment.searchForWikiPage() :: No exact match found for '{}' in space '{}', searching by query...".format(pageTitle, spaceKey)
        if extended > 0:
            params = dict(spaceKey=spaceKey, contributor=user)
            params['type'] = 'page'
            expid = self.Props['expid']
            result = self.searchForWikiPageWithQuery(expid, parameters=params, intitle=expid)
            if result:
                return result
            elif result is 0 and extended > 1:
                # if this does not yield anything, try to search all spaces:
                params2 = params
                params2.pop('spaceKey')
                result = self.searchForWikiPageWithQuery(expid, parameters=params, intitle=expid)
                if result:
                    return result
                # and again, now excluding user as contributor (perhaps someone else wrote the entry...)
                params2 = params
                params2.pop('contributor')
                result = self.searchForWikiPageWithQuery(expid, parameters=params, intitle=expid)
                if result:
                    return result
            else:
                # Too many results? Perhaps two or something?
                print "Experiment.searchForWikiPage() :: Unable to find unique page result, aborting..."
                return None


    def searchForWikiPageWithQuery(self, query, parameters, intitle=None, title_regex=None, content_regex=None, singleMatchOnly=True):
        """
        Todo: allow for 'required' and 'optional' arguments.
        """
        results = self.Server.search(query, 10, parameters)
        if intitle:
            results = filter(lambda page: intitle in page['title'], results)
        if not singleMatchOnly:
            return results
        if len(results) > 1:
            print "\nExperiment.searchForWikiPageWithQuery() :: Many hits found, but only allowed to return a single match." # in space '{}', pageTitle '{}'".format(spaceKey, pagestruct['title'])
            print "\n".join( "{} ({})".format(page['title'], page['id']) for page in results )
            return False
        if len(results) < 1:
            return 0
        if len(results) == 1:
            pagestruct = results[0]
            print "\nExperiment.searchForWikiPageWithQuery() :: A single hit found in space '{}', pageTitle '{}'".format(spaceKey, pagestruct['title'])
            return pagestruct


    def makeWikiPage(self, dosave=True, pagefactory=None):
        if not (self.Server and self.Confighandler):
            print "Experiment.makeWikiPage() :: FATAL ERROR, no server and/or no confighandler."
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
        self.saveProps()
        return self.WikiPage


    def makeWikiSubentry(self, subentry_idx, subentry_titledesc=None, updateFromServer=True, persistToServer=True):
        """
        Edit: This has currently been delegated to self.JournalAssistant, which specializes in inserting
        content at the right location using regex'es.
        """
        if subentry_idx not in self.Subentries:
            print "Experiment.makeWikiSubentry() :: ERROR, subentry_idx '{}' not in self.Subentries; make sure to first add the subentry to the subentries list and _then_ add a corresponding subentry on the wikipage.".format(subentry_idx)
            return
        res = self.JournalAssistant.newExpSubentry(subentry_idx, subentry_titledesc=subentry_titledesc, updateFromServer=updateFromServer, persistToServer=persistToServer)
        # pagetoken = where to insert the new subentry on the page, typically before <h2>Results and discussion</h2>.
        #pagetoken = self.getConfigEntry('wiki_exp_new_subentry_token') # I am no longer using tokens, but relying on regular expressions to find the right insertion spot.
        self.saveIfChanged()
        return res


    def uploadAttachment(self, filepath, attachmentInfo=None, digesttype='md5'):
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
        print "Experiment.uploadAttachment() :: Not tested yet - take care ;)"
        if not getattr(self, 'WikiPage', None):
            print "Experiment.uploadAttachment() :: ERROR, no wikipage attached to this experiment object\n - {}".format(self)
            return None
        if attachmentInfo is None:
            attachmentInfo = dict()
        if not os.path.isabs(filepath):
            filepath = os.path.normpath(os.path.join(self.Localdirpath, filepath))
        # path relative to this experiment, e.g. 'RS123d subentry_titledesc/RS123d_c1-grid1_somedate.jpg'
        relpath = os.path.relpath(filepath, self.Localdirpath)
        mimetype = getmimetype(filepath)
        attachmentInfo['contentType'] = mimetype
        attachmentInfo.setdefault('comment', os.path.basename(filepath) )
        attachmentInfo.setdefault('fileName', os.path.basename(filepath) )
        attachmentInfo.setdefault('title', os.path.basename(relpath) )
        if digesttype:
            digestentry = self.hashFile(filepath, (digesttype, ))
            attachmentInfo.setdefault("{}-hexdigest: {}".format(digesttype, digestentry[digesttype]))
        with open(filepath, 'rb') as f:
            # Not sure exactly what format the file bytes should have.
#            attachmentData = f # Is a string/file-like object ok?
#            attachmentData = f.read() # Can I just load the bytes?
            # Should I do e.g. base64 encoding of the bytes?
            attachmentData = xmlrpclib.Binary(f.read())# as seen in https://confluence.atlassian.com/display/DISC/Upload+attachment+via+Python+XML-RPC
            attachment = self.WikiPage.addAttachment(attachmentInfo, attachmentData)



    def listAttachments(self):
        """
        Lists attachments on the wiki page.
        Returns a list of attachments (structs) if succeeded,
        False if failed and None if no attemt was made to upload due to a local Error.
        Use the Attachments property for a cached version.
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
            print "Experiment.uploadAttachment() :: ERROR, no wikipage attached to this experiment object\n - {}".format(self)
            return None
        print "Experiment.listAttachments() :: Not implemented yet - take care ;)"
        attachment_structs = self.WikiPage.getAttachments()


    def getAttachmentList(self, src=None, fn_pattern=None, fn_is_regex=False, **filterdict):
        """
        Similar to getLocalFileslist(), incorporates a filterdict.
        However, this uses self.
        - comment (string, required)
        - contentType (string, required)
        - created (date)
        - creator (string username)
        - fileName (string, required)
        - fileSize (string, number of bytes)
        - id (string, attachmentId)
        """
        if src is None:
            struct_list = self.Attachments
        else:
            if src == 'server':
                struct_list = self.updateAttachmentsCache()
            struct_list = self._attachments_cache
        # Returned tuple of (<display>, <identifier>, <complete struct>)
        # I think either filename or id would work as identifier.
        if fn_pattern:
            if not fn_is_regex:
                fn_pattern = fnmatch.translate(fn_pattern)
            regex_prog = re.compile(fn_pattern)
        else:
            regex_prog = None
        # attachment struct_list might be None or False, so must check before trying to iterate:
        if not struct_list:
            return list()
        return [ (struct['fileName'], struct['id'], struct) for struct in struct_list \
                    if regex_prog is None or regex_prog.match(struct['fileName']) ]








    """ Other stuff... """

    def __repr__(self):
        #return "Experiment in ('{}'), with Props:\n{}".format(self.Localdirpath, yaml.dump(self.Props))
        return "e>"+self.Confighandler.get('exp_series_dir_fmt').format(**self.Props)

    def update(self, other_exp):
        """
        Update this experiment with the content from other_exp.
        """
        raise NotImplementedError("Experiment.update is not implemented...")




if __name__ == '__main__':
    import glob
    def setup1(useserver=True):
        confighandler = ExpConfigHandler( pathscheme='default1', VERBOSE=1 )
        print "----"
        rootdir = confighandler.get("local_exp_subDir")
        print "rootdir: {}".format(rootdir)
        print "glob res: {}".format(glob.glob(os.path.join(rootdir, r'RS102*')) )
        ldir = os.path.join(rootdir, glob.glob(os.path.join(rootdir, r'RS102*'))[0] )
        print "ldir: {}".format(ldir)
        ldir2 = os.path.join(rootdir, glob.glob(os.path.join(rootdir, "RS105*"))[0] )
        print "ldir2: {}".format(ldir2)
        #ldir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
#                '/home/scholer/Documents/labfluence_data_testsetup/.labfluence
        #ldir2 = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS105 TR STV-col11 Origami v3":
        server = ConfluenceXmlRpcServer(confighandler=confighandler, VERBOSE=4, prompt='auto', autologin=True) if useserver else None
        e = Experiment(confighandler=confighandler, server=server, localdir=ldir, VERBOSE=10)
        return e

    def test_1(e=None):
        if not e:
            e = setup1()
        print e
        return e

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

    def test_attachWikiPage(e=None):
        if not e:
            e = setup1()
        if e.WikiPage:
            print "\nPage already attached: {}".format(e.WikiPage)
        else:
            e.attachWikiPage(dosearch=True)
            print "\nPage attached: {}".format(e.WikiPage)
        return e

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

    def test_addNewSubentry(e=None, subentry_idx=None):
        if not e:
            e = setup1()
        if not subentry_idx:
            subentry_idx = e.getNewSubentryIdx()
        e.addNewSubentry(subentry_titledesc="AFM of RS102e TR")
        return e

    def test_addNewSubentry2(e=None, subentry_idx=None):
        if not e:
            e = setup1()
        if not subentry_idx:
            subentry_idx = e.getNewSubentryIdx()
        e.addNewSubentry(subentry_titledesc="Strep NHS-N3 activation", subentry_idx='a', subentry_date="20130103")
        return e

    def test_addNewSubentry3(e=None, subentry_idx=None):
        if not e:
            e = setup1()
        if not subentry_idx:
            subentry_idx = e.getNewSubentryIdx()
        e.addNewSubentry(subentry_titledesc="Strep-N3 DBCO-dUTP conj", subentry_idx='b', subentry_date="20130103", makefolder=True, makewikientry=True)
        return e

    def test_addNewSubentry4(e=None, subentry_idx=None):
        if not e:
            e = setup1()
        if not subentry_idx:
            subentry_idx = e.getNewSubentryIdx()
        e.addNewSubentry(subentry_titledesc="Amicon pur and UV quant of Strep-ddUTP", subentry_idx='c', subentry_date="20130104", makefolder=True, makewikientry=True)
        return e

    def test_makeSubentryFolder(e=None, subentry_idx=None):
        if not e:
            e = setup1()
        if not subentry_idx:
            subentry_idx = e.getNewSubentryIdx()
        e.makeSubentryFolder(subentry_idx='a')
        return e

    def test_makeNewWikiSubentry(e=None, subentry_idx=None):
        if not e:
            e = setup1()
        if not subentry_idx:
            subentry_idx = e.getNewSubentryIdx()
        res = e.makeWikiSubentry(subentry_idx)
        print "\nResult of makeWikiSubentry() :\n{}".format(res)
        return e


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



    def test_getWikiSubentryXhtml(e=None):
        print "\n>>>>>>>>>>>>>> test_getWikiSubentryXhtml() started >>>>>>>>>>>>>"
        if not e:
            e = setup1(useserver=True)
            e.attachWikiPage()
        print "\n\n"
        print e.Server
        for s in ('a',):#'b','c','e'):
            print "\nFor subentry '{}':".format(s)
            e.getWikiSubentryXhtml(s)
        #print "\nInvoked without subentry:"
        #e.getWikiSubentryXhtml()



        print "<<<<<<<<<<<<<< test_getWikiSubentryXhtml() finished <<<<<<<<<<<<"


    print "\n\n---------------- STARTING EXPERIMENT.PY MAIN TESTS --------------\n\n"
    #e=test_1()
    print "\n------------finished test_1() ----------------------\n"

    #e=test_saveProps(e)
    #print "\n------------finished test_saveProps() ----------------------\n"

    #e=test_attachWikiPage(e)
    print "\n------------finished test_attachWikiPage() ----------------------\n"

    #e=test_makeNewWikiPage(e)
    #print "\n------------finished test_makeNewWikiPage() ----------------------\n"


#    e=test_addNewSubentry(e)
#    e=test_addNewSubentry2(e)
#    e=test_addNewSubentry3(e)
    #e=test_addNewSubentry4(e)
    print "\n------------finished test_addNewSubentry() ----------------------\n"


#    e=test_makeSubentryFolder(e, 'a')
#    print "\n------------finished test_makeSubentryFolder() ----------------------\n"


#    e=test_makeNewWikiSubentry(e, 'c')
#    print "\n------------finished test_makeNewWikiSubentry() ----------------------\n"

    #e = None
    #e = test_getRepr()
    e = test_getWikiSubentryXhtml()
    print "\n\n"
    print e

"""

Cut out parts, here as trash-bin:

# hashing... don't think I will ever need this anyways...
                # My own implementation using python's fast hash function...
                if digesttype == 'python-hash':
                    # 16k byte block sizes:
                    lasthash = hash('')
                    for chunk in iter(lambda: f.read(128*128), b''):
                        lasthash = lasthash + hash(chunk)
                    digestentry[digesttype] = lasthash
                    hexdigest = lasthash # well, not actually hex, perhaps do some base64 encoding?
                else:
                    # assume the digesttype is available in hashlib:


"""
