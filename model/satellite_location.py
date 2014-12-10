#!/usr/bin/env python3
# -*- coding: utf-8 -*-
##    Copyright 2013-2014 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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
# pylint: disable-msg=C0103,C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221,E1101,W0402,E0202,W0201,E0102
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
Code for dealing with satellite locations.
Consider using virtualfs python module to normalize external locations,
rather than implementing ftp, etc...

Object graph:
                        Experiment
                       /          \
            Filemanager             WikiPage
           /
SatelliteMgr
           \
            SatelliteLocation


In general, I imagine this being used in two ways:

1)  Location-centric: You ask a satellite location if something has changed (possibly as part
    of a loop over all locations). If something has changed, it figures out which experiment(s)
    the change(s) is (are) related to and syncs to the local directory tree.

2)  Experiment-centric: You (or an experiment object) ask the satellite location to identify folders related to a specific
    experiment and then syncs just those folders to the experiment's folders.
    (Note: Probably cache the local directory tree in memory for maybe 1 min so you can
    rapidly sync multiple experiments...)

What about the use case where I simply want to do a one-way sync, pulling new files from a
satellite location to the local experiment data directory?
  - This should not be handled here; A satellite location knows nothing about the local
    experiment data file structure.
    Two questions: WHERE should this be handled/implemented and HOW?

HOW to implement "one-way sync to pull new files from sat loc to local exp data file structure":
 a) ExpManager parses local experiment directory tree, getting a list of expids.
    SatLoc parses remote tree, getting a list of expids.
    For each local experiment, sync all remote subentry folders into the experiment's local directory.
    This could be handled by the (already large) experimentmanager module, or it could be
    delegated to a separate module, syncmanager.py

    All other ways I've found is either where the local experiment folder is specified
    (effectively the same as the "experiment centric" implementation/usage above)
    or where an experiment ID is provided, effectively just applying the above for
    a single expid instead of all expids.

As default, sync should be one-way only: from satellite location to local data tree.
Only exception might be to update foldernames on the satellite location to match the
foldernames in the data tree.


TODO:
    # TODO: Consolidate all file structure parsing to a single module.

== Other design considerations: ==

    It is a design target that the subentry folder on the satellite location DOES NOT have
    to match the name of the subentry folder in the main data tree exactly, but can be
    inferred from the name by regex parsing, so that the subentry folder "RS190c PAGE analysis of b"
    will be interpreted correctly as Experiment=RS190, subentry=c.
    The experiment/subentry folder can then optionally be renamed to match the name in the main
    data tree, if the program has read permissions. (Possibly extending this to files...)


== Discussion: Monitoring filesystem changes: ==

    Consideration: Which approach is better if I want to be able to check if something has changed?
        a)  Keep a full directory list structure in memory and check against this?
        b)  Create a simple checksum of the directory structure. Re-calculate this when checking for changes.
            But then, say you discover that something has changed. Then you need to figure out
            *what* has changed. This argument would prefer strategy (a).

    There must be a library for checking for updates to file trees...
    Indeed: Watchdog is one (cross-platform). pyinotify is another (linux only). Watcher is a third (windows only).

    Attention: A lot of these 'smart' solutions use system signals to watch for changes. However, since
    the satellite location is most likely on a remote system, I'm not sure any signal will be emitted
    which the code can catch.
    Watchdog specifically states not to use the dirsnapshot module for virtual filesystems mapped to a network share.

    The general approach seems to be to store all filepaths in a dict.
    When checking for changes, generate a new dict and compare with old.
    This can be optimized by e.g. using folder's mtime (on UNIX) to assume it has not been changed.

    Watchdog library:
    - https://pythonhosted.org/watchdog/
    - http://blog.philippklaus.de/2011/08/use-the-python-module-watchdog-to-monitor-directories-for-changes/
    For Windows:
    - http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
    On UNIX:
    - http://code.activestate.com/recipes/215418-watching-a-directory-tree-on-unix/
    - http://code.activestate.com/recipes/217829-watching-a-directory-tree-under-linux/
    - http://pyinotify.sourceforge.net/  (relies on inotify in linux kernel)
    With PyQt:
    - http://stackoverflow.com/questions/182197/how-do-i-watch-a-file-for-changes-using-python (also links other solutions)


"""
from __future__ import print_function
from six import string_types

import os
import re
import shutil
import time
# FTP not yet implemented...
#from ftplib import FTP
import logging
logger = logging.getLogger(__name__)

from decorators.cache_decorator import cached_property

class SatelliteLocation(object):
    """
    Base class for satellite locations, treats the location as if it is a locally available file system.

    Initialize with a locationparams dict and an optional satellite manager.
    Locationparams is generally specified in a yaml/json configuration file.
    Location params dict can include the following:
        name:       The display name of the satellite location.
        description: Description of the satellite location.
        protocol:   The protocol to use. Currently, only file protocol is supported.
        uri:        The location of the satellite directory, e.g. Z:\.
        rootdir:    The folder on the satellite location, e.g. Microscopy\Rasmus.
        folderscheme: String specifying how the folders are organized, e.g. {year}/{experiment}/{subentry}. Defaults to {subentry}.
        regexs:     A dict with regular expressions specifying how to parse each element in the folderscheme.
                    The key must correspond to the name in the folderscheme, e.g. 'experiment': r'(?P<expid>RS[0-9]{3})[_ ]+(?P<exp_titledesc>.+)'
        ignoredirs: A list of directories to ignore when parsing the satellite location for experiments/subentries.
        mountcommand: Specifies how to mount the satellite location as a local, virtual filesystem.

    The rationale for keeping uri and rootdir separate is that the uri can be mounted, e.g. if it is an FTP server,
    followed by a 'cd' to the root dir.

    Notes:
    Protocol is used to determine how to access the file. This is generally handled by subclassing with the location_factory module function,
        which e.g. returns a SatelliteFileLocation subclass for 'file' protocol locations.
    URI, rootdir, and folderscheme is used to access the files.
    - URI is the "mount point", FTP server, or NFS share or similar,
        e.g. /mnt/typhoon_ftp/
        (Currently, only local file protocol is supported...)
    - Rootdir is the directory on the URI where your files are located, e.g.
        /scholer/   or  /typhoon_data/jk/Rasmus/
    - Folderscheme is used to figure out how to handle/sync files from the satellite location
        into the main experiment data tree. Examples of Folderschemes:
        ./subentry/     -> Means that data is stored in folders named after the subentry related to that data.
                        e.g. /mnt/typhoon_ftp/scholer/RS190c PAGE analysis of b/RS190c_PAGE_sybr_600V.gel
        ./              -> data is just stored in a big bunch within the root folder.
                        Use filenames to interpret what experiments/subentries they belong to, e.g.:
                            /mnt/typhoon_ftp/scholer/RS190c_PAGE_sybr_600V.gel
        ./year/experiment/subentry/  -> data is stored, e.g.
                        /mnt/typhoon_ftp/scholer/2014/RS190 Test experiment/RS190c PAGE analysis of b/RS190c_PAGE_sybr_600V.gel

    QUESTION: If the subentryId (expid+subentry_idx) does not match the experiment id, which takes preference?
    E.g. for folder:    <rootdir>/RS190 Test experiment/RS191c PAGE analysis of b/
    which takes preference?

    == Methods and Usage: ==
    This class contains a lot of code intended for a persistent/long-lived satellite location object.
    This includes code to parse a full directory tree to produce a central data structure consisting of
        dict[expid][subentry_idx] = filepath
    e.g.
        ds['RS123']['a'] = "2014/RS123 Some experiment/RS123a Relevant subentry"
    The primary file tree parsing methods are:
        genPathmatchTupsByPathscheme
        getSubentryfoldersByExpidSubidx

    Many of the methods are used to either extract info from this datastructure,
    or update this data structure:
        update_expsubfolders : Updates the two catalogs _expidsubidxbyfolder, _subentryfolderset
            and returns a three-tuple specifying what has been updated since it was last invoked.

    A few methods are intended to update the satellite location's file structure (keeping the database updated in the process).
        renameexpfolder
        renamesubentryfolder
        ensuresubentryfoldername

    Subclasses provides med-level methods for one-way syncing:
        syncToLocalDir      Syncs a satellite directory to a local directory.
        syncFileToLocalDir  Syncs a satellite file to a local path.

    Each subclass additionally provides some low-level "file system" methods, e.g. rename, copy, etc.
        rename
        listdir, isdir, join,

    Additionally, there are a few rarely-used methods:
        getFilepathsByExpIdSubIdx: Like getSubentryfoldersByExpidSubidx, but returns a list of files within the folder.


    """
    def __init__(self, locationparams, manager=None):
        self._locationparams = locationparams
        self._manager = manager
        self._fulldirectoryset = set()
        self._regexpats = None
        # self._subentryfoldersbyexpidsubidx = None # Is now a cached property; the cache value should only be located in one place and that is not here.
        self._subentryfolderset = set()
        self._expidsubidxbyfolder = None
        self._cache = dict()

    def __repr__(self):
        return "sl> {}".format(self.Name or self.Description or self.URI)

    #########################
    ### Properties ##########
    #########################

    @property
    def LocationManager(self):
        """ The locationsmanager used to manage the locations (if any). """
        return self._manager
    @property
    def Confighandler(self):
        """ The universal confighandler. """
        if self._manager:
            return self._manager.Confighandler
    @property
    def LocationParams(self):
        """ Location parameters for this satellite location. """
        return self._locationparams
    @property
    def Protocol(self):
        """ Protocol """
        return self.LocationParams.get('protocol', 'file')
    @property
    def URI(self):
        """ URI """
        return self.LocationParams.get('uri')
    @property
    def Rootdir(self):
        """ Rootdir """
        return self.LocationParams.get('rootdir', '.')
    @property
    def IgnoreDirs(self):
        """
        List of directories to ignore. Consider implementing glob-based syntax...
        Excluding directories from e.g. previous years can help speed up lookups and location hashing.
        """
        return self.LocationParams.get('IgnoreDirs', list())
    @property
    def Folderscheme(self):
        """ Folderscheme """
        return self.LocationParams.get('folderscheme', './subentry/')
    @property
    def Mountcommand(self):
        """ Mountcommand """
        return self.LocationParams.get('mountcommand')
    @property
    def Name(self):
        """ Description """
        return self.LocationParams.get('name')
    @property
    def Description(self):
        """ Description """
        return self.LocationParams.get('description')
    @property
    def Regexs(self):
        """
        Returns regex to use to parse foldernames.
        If regex is defined in locationparams, this is returned.
        Otherwise, try to find a default regex in the confighandler.
        If that doesn't work, ... ?
        """
        if not self._regexpats:
            ch = self.Confighandler
            if 'regexs' in self.LocationParams:
                regexs = self.LocationParams['regexs']
            elif ch:
                regexs = ch.get('satellite_regexs') or ch.get('exp_folder_regexs')
            else:
                logger.warning("Could not obtain any regex !")
                return
            self._regexpats = {regex : re.compile(regex) for regex in regexs}
        return self._regexpats
    @Regexs.setter
    def Regexs(self, regexs):
        """
        Set regexs. Format must be a dict where key corresponds to a pathscheme element (e.g. 'experiment')
        and the values must be either regex patterns or strings (which will then be compiled...)
        """
        self._regexpats = {key : re.compile(regex) if isinstance(regex, string_types) else regex for key, regex in regexs.items()}
        logger.debug("self._regexpats set to {}".format(self._regexpats))

    ##################################
    ## Not-used/diabled properties ###
    ##################################

    # Some of these should probably be implemented differently, they are just here for the concept.

    #@property
    #def FoldersByExpSub(self):
    #    """
    #    Return a dict-dict datastructure:
    #    [<expid>][<subentry_idx>] = folderpath.
    #    With this, it is easy to find a satellite folderpath for a particular experiment subentry.
    #    """
    #    return self.getSubentryfoldersByExpidSubidx()
    #
    #@property
    #def FolderStructureStat(self):
    #    """
    #    Returns a dict datastructure:
    #    [folderpath] = stat
    #    I'm not sure how much it costs to stat() a file/folder on a network share vs just listing the contents.
    #    """
    #    pass
    #
    #@property
    #def Fulldirectoryset(self):
    #    """
    #    Returns a set of all files in the datastructure.
    #    This would be very easy to compare for new files and folders:
    #    """
    #    return self._fulldirectoryset


    #####################################
    #- Properties for subentryfolders  -#
    #####################################

    @cached_property(ttl=60)
    def SubentryfoldersByExpidSubidx(self):
        """
        Returns a dict-dict with subentry folders as:
            ds[expid][subidx] = <filepath>

        Implementation discussion:
        I guess this should really be the other way around.
        But currently, update_expsubfolders() takes care of resetting the cache items.
        self.update_expsubfolders() will calculate:
        self._expidsubidxbyfolder = expidsubidxbyfolder
        self._subentryfolderset = subentryfoldersset
        """
        logger.debug("Getting foldersbyexpidsubidx with self.getSubentryfoldersByExpidSubidx(), [%s]", time.time())
        foldersbyexpidsubidx = self.getSubentryfoldersByExpidSubidx()
        logger.debug("-- foldersbyexpidsubidx obtained with %s items, [%s]", foldersbyexpidsubidx if foldersbyexpidsubidx is None else len(foldersbyexpidsubidx), time.time())
        logger.debug("Invoking self.update_expsubfolders(foldersbyexpidsubidx=foldersbyexpidsubidx) [%s]", time.time())
        self.update_expsubfolders(foldersbyexpidsubidx=foldersbyexpidsubidx)
        return foldersbyexpidsubidx
    @property
    def ExpidSubidxByFolder(self):
        """
        ExpidSubidxByFolder[<folderpath] --> (expid, subidx)
        """
        if not self._subentryfolderset:
            logger.debug("Invoking self.update_expsubfolders(), %s", time.time())
            self.update_expsubfolders()
        return self._expidsubidxbyfolder
    @property
    def Subentryfoldersset(self):
        """
        set(<list of subentry folders>)
        """
        if not self._subentryfolderset:
            logger.debug("Invoking self.update_expsubfolders(), %s", time.time())
            self.update_expsubfolders()
        return self._subentryfolderset

    #def subentryfoldersupdated(self):
    #    """
    #    Call this to invalidate the stored cache:
    #    Probably not the best thing to do.
    #    """
    #    self._expidsubidxbyfolder = None
    #    self._subentryfolderset = None



    def getConfigEntry(self, cfgkey, default=None):
        """
        Returns a config key from the confighandler, if possible.
        """
        ch = self.Confighandler
        if ch:
            return ch.get(cfgkey, default)


    #def findSubentries(self, regexpat, basepath='.', folderscheme=None):
    #    """
    #    First primitive attempt. Finds subentry folders matching regexpat.
    #    Returns a list of the subentry folders.
    #    """
    #    if folderscheme is None:
    #        folderscheme = self.Folderscheme
    #    if isinstance(regexpat, basestring):
    #        regexpat = re.compile(regexpat)
    #    basepath = self.getRealPath(basepath)
    #    if folderscheme == './experiment/subentry/':
    #        subentryfolders = ((subentry, self.join(basepath, experiment, subentry))
    #                 for experiment in self.listdir(basepath) if self.isdir(self.join(basepath, experiment))
    #                    for subentry in self.join(basepath, experiment) if self.isdir(self.join(basepath, experiment, subentry)))
    #    else: # e.g. if self.FolderScheme == './subentry/':
    #        subentryfolders = ((subentry, self.join(basepath, subentry)) for subentry in self.listdir(basepath))
    #    dirs = [path for foldername, path in subentryfolders if regexpat.match(foldername)]
    #    return dirs

    #def genSubentryFolderMatches(self, regexs=None, basedir=None, folderscheme=None):
    #    """
    #    Generate a sequence of tuples:
    #        (filepath, subentry_regex_match, exp_regex_match)
    #    This could probably be made considerably better by splitting folderscheme to a sequence:
    #        './experiment/subentry/'  ->  ( 'experiment', 'subentry' )
    #    and then looping over this from the start / popping.
    #    You could even combine with os.walk, stepping up and down in the items in folderscheme as you
    #    walk up and down the directory tree.
    #    This could yield corresponding directory matches:
    #        [<experiment-match>][subentry-match] = <list of filename(-matche)s>
    #    Alternatively, it could be a sequence of tuples:
    #        (<experiment-match>, <subentry-match>, <filename-match>, filepath)
    #    or a sequence of dicts ?
    #        {'experiment': <exp-match>, 'subentry': <subentry-match>, 'filename' : <fn-match>, 'filepath' : <full filepath>}
    #    """
    #    return self.genPathmatchTupsByPathscheme(regexs, basedir, folderscheme)
    #    ### All of the below is replaced by the line above:
    #    #regexs = regexs or self.Regexs
    #    #basedir = basedir or self.Rootdir
    #    #basepath = self.getRealPath(basedir)
    #    #folderscheme = folderscheme or self.Folderscheme
    #    #
    #    ## First: tuple-generator, where
    #    ## first item  = folder path relative to basedir.
    #    ## second item = regex match for subentry folder.
    #    ## third item  = regex match for experiment folder (might be None).
    #    #if folderscheme == './experiment/subentry/':
    #    #    expfolders = self.listdir(basepath)
    #    #    expregexpat = regexs['experiment']
    #    #    if expregexpat:
    #    #        expfolders = ((self.join(basedir, folder), match) for folder, match in
    #    #                        ((folder, expregexpat.match(folder)) for folder in expfolders)
    #    #                        if match)
    #    #else:
    #    #    expfolders = iter((basedir, None))
    #    #
    #    #if folderscheme.endswith('/subentry/'):
    #    #    subentryregexpat = regexs['subentry']
    #    #    def subentrymatch_gen():
    #    #        """ is this a generator closure? """
    #    #        for expfolder, expmatch in expfolders:
    #    #            for folder in self.listdir(expfolder):
    #    #                subentrymatch = subentryregexpat.match(folder)
    #    #                if subentrymatch:
    #    #                    yield (self.join(expfolder, folder), subentrymatch.groupdict(), expmatch.groupdict() if expmatch else None)
    #    #return subentrymatch_gen()


    def genPathmatchTupsByPathscheme(self, regexs=None, basedir=None, folderscheme=None, includefiles=False):
        """
        Returns a sequnce/generator of two-item 'matchtuples':
            (folderpath, match-items-dict)
        where each match-items-dict has keys matching each scheme item in folderscheme
        and each value is a regex match found during traversal at that scheme level.
        For a very deep pathscheme of 'year/experiment/subentry/filename'
            {'year': <year match>, 'experiment': <exp-match>, 'subentry': <subentry-match>, 'filename' : <fn-match>}
        (Usually, you do not want to include <filename> in the folderscheme, but perhaps
        parse that separately if required...)
        Question: Do you save for all levels, or only for the final part? Only the last part.

        """
        regexs = regexs or self.Regexs
        basedir = basedir or self.Rootdir
        basedir = os.path.normpath(basedir)
        basepath = self.getRealPath(basedir)
        folderscheme = folderscheme or self.Folderscheme
        schemekeys = [key for key in folderscheme.split('/') if key and key != '.']
        logger.debug("genPathmatchTupsByPathscheme invoked running with, regexs=%s, basedir=%r, folderscheme=%r, includefiles=%s",
                     regexs, basedir, folderscheme, includefiles)


        logger.debug("Making pathmatchtuples from pathscheme %s with regexs: %s", folderscheme, regexs)
        def genitems(schemekeys, basefolder, basematch=None):
            """
            schemekeys are the remaining items in the pathscheme, starting
            from basefolder. basematch is a dict with matches for the basefolder.
            If pathscheme is ./year/experiment/subentry and we are at ./2013/RS160.../
            then basematch will be a dict : {'year': <year match>, 'experiment': <exp match>}
            Since we are using a generator, creating dicts should not be a big memory issue.
            And, since the pathscheme should only go two maybe three steps deep,
            recursing shouldn't be an issue either.
            Returns a sequnce/generator of two-item 'matchtuples':
                (folderpath, match-items-dict)
            """
            # slicing does not raise indexerrors:
            schemekey, remainingschemekeys = schemekeys[0], schemekeys[1:]
            regexpat = regexs[schemekey]
            # logging disabled: produces A LOT of output
            #logger.debug("Running genitems for schemekey '%s', remaining items is: %s", schemekey, remainingschemekeys)
            #logger.debug("basefolder is '%s', regex '%s', matching against directory elements: %s", basefolder, regexpat.pattern, self.listdir(basefolder))
            # if schemekey is 'experiment' and remaining items is ['subentry'],
            # then basefolder should be e.g. ./2014/.
            # Produce list of folders (or files, if includefiles=True):
            foldernames = (foldername for foldername in self.listdir(basefolder)
                            if foldername not in self.IgnoreDirs and (includefiles or self.isdir(self.join(basefolder, foldername))))
            # Make tuples with folder path and regex match
            pathmatchtup = ((self.join(basefolder, foldername), regexpat.match(foldername))
                                    for foldername in foldernames)
            #logger.debug("Number of folders matched:  %s", len(pathmatchtup))#, pathmatchtup)
            # Filter out tuples where regex match is None (= no match)
            foldertups = ((self.path.normpath(folderpath), dict(basematch, **{schemekey: match})) # alternatively basematch.copy().update({schemekey: match})
                            for folderpath, match in pathmatchtup if match)
            #logger.debug("Number of matching matched: %s", len(foldertups))
            if remainingschemekeys:
                matchitems = (subfoldertup
                              for folderpath, matchdict in foldertups
                                for subfoldertup in genitems(remainingschemekeys, folderpath, matchdict))
                #logger.debug("Received matching items from remainingschemekeys: %s", len(matchitems))
            else:
                #logger.debug("No remaining items, returning foldertups at this level.")
                matchitems = foldertups
            return matchitems

        foldermatchtups = genitems(schemekeys, basepath, basematch=dict())
        return foldermatchtups



    def getSubentryfoldersByExpidSubidx(self, regexs=None, basedir=None, folderscheme=None):
        """
        Return datastructure:
            [expid][subentry_idx] = <filepath relative to basedir/rootdir>
        Usage:
            ds = getSubentryfoldersByExpidSubidx(...)
            subentry_fpath = ds['RS123']['a'] # returns e.g. "2014/RS123 Some experiment/RS123a Relevant subentry"
        """
        # logger.debug("getSubentryfoldersByExpidSubidx(regexs=%s, basedir='%s', folderscheme='%s')", regexs, basedir, folderscheme)
        subentryfoldermatchtuples = self.genPathmatchTupsByPathscheme(regexs, basedir, folderscheme, includefiles=False)
        foldersbyexpidsubidx = dict()
        self.Matchpriorities = {'expid' : ('experiment', 'subentry'), #'filename'), # folderscheme looks for subentries, so there will not be a file.
                                'subentry_idx' : ('subentry', )# 'filename') # Remember the fucking comma.
                                }
        # This runs the generator. You may want to grab as much as possible now that you have it.
        for folderpath, matchdict in subentryfoldermatchtuples:
            expid = next(expid for expid in
                            (matchdict[k].groupdict().get('expid') for k in
                                (elem for elem in self.Matchpriorities['expid'] if elem in matchdict)
                            ) if expid)
            # DEBUGGING:
            #logger.debug("self.Matchpriorities['subentry_idx'] = %s, matchdict = %s",
            #             self.Matchpriorities['subentry_idx'], matchdict)
            ## For the schemekeys specified for subentry_idx in self.Matchpriorities, find those that are in the matchdict.
            #schemekeys_in_matchdict = [elem for elem in self.Matchpriorities['subentry_idx'] if elem in matchdict.keys()]
            #logger.debug("Relevant relevant_schemekeys: %s", schemekeys_in_matchdict)
            #groupdict_subentryidx = [matchdict[k].groupdict().get('subentry_idx') for k in schemekeys_in_matchdict]
            #logger.debug("Match groupdict subentry_idx: %s", groupdict_subentryidx)
            subentry_idx = next(subentry_idx for subentry_idx in
                            (matchdict[k].groupdict().get('subentry_idx') for k in
                                (elem for elem in self.Matchpriorities['subentry_idx'] if elem in matchdict)
                            ) if subentry_idx)
            foldersbyexpidsubidx.setdefault(expid, dict())[subentry_idx] = folderpath
        logger.debug("expsubfolders expids: %s", foldersbyexpidsubidx.keys())
        return foldersbyexpidsubidx



    def update_expsubfolders(self, clearcache=False, foldersbyexpidsubidx=None):
        """
        Updates the catalog of experiment subentry folders and the complementing
        _subentryfolderset and _expidsubidxbyfolder.

        Returns a tuple of
            (newexpsubidx, newsubentryfolders, removedsubentryfolders)
        listing folder changes since last update, where:
        - newexpsubidx = set with tuples of (expid, subidx) of newly changed folder.
          (Same as _expidsubidxbyfolder[folder] for a newly changed folders)
        - newsubentryfolders = set of added subentry foldernames since last update.
        - removedsubentryfolders = set of removed subentry foldernames since last update.

        NOTICE: Can NOT be used to check for updates to files within a folder; only
                for changes to subentry foldernames / paths.
        """
        logger.debug("update_expsubfolders(clearcache=%s, foldersbyexpidsubidx='%s')",
                     clearcache, foldersbyexpidsubidx)
        # Avoid premature optimizations:
        # self.getSubentryfoldersByExpidSubidx() is the only calculation expected to be slow,
        # so only make a cached_property for this.
        if clearcache:
            logger.debug("Clearing cache for self.SubentryfoldersByExpidSubidx")
            # Note: This will delete most references to the SubentryfoldersByExpidSubidx. Maybe clear it rather than delete/reassign?
            # How is the property's del defined?
            del self.SubentryfoldersByExpidSubidx
        if foldersbyexpidsubidx is None:
            logger.debug("Obtaining foldersbyexpidsubidx = self.SubentryfoldersByExpidSubidx")
            foldersbyexpidsubidx = self.SubentryfoldersByExpidSubidx
            logger.debug("foldersbyexpidsubidx obtained")

        # Perform calculations
        expidsubidxbyfolder = {subentryfolder : (expid, subidx)
                                    for expid, expdict in foldersbyexpidsubidx.items()
                                        for subidx, subentryfolder in expdict.items()}
        subentryfoldersset = set(expidsubidxbyfolder.keys())
        newsubentryfolders = subentryfoldersset - self._subentryfolderset
        removedsubentryfolders = self._subentryfolderset - subentryfoldersset
        newexpsubidx = {expidsubidxbyfolder[folder] for folder in newsubentryfolders}

        #self._subentryfoldersbyexpidsubidx = foldersbyexpidsubidx
        self._expidsubidxbyfolder = expidsubidxbyfolder
        self._subentryfolderset = subentryfoldersset
        #self._newexpsubidxsincelastupdate = newexpsubidx
        #self._newsubentryfolderssincelastupdate = newsubentryfolders
        #self._removedsubentryfolderssincelastupdate = removedsubentryfolders

        ## Update the cache:
        ## Edit: Not required;
        #now = time.time()
        #toupdate = (('SubentryfoldersByExpidSubidx', foldersbyexpidsubidx),
        #            ('Subentryfoldersset', subentryfoldersset),
        #            ('ExpidSubidxByFolder', expidsubidxbyfolder))
        #for cachename, value in toupdate:
        #    self._cache['cachename'] = (value, now)

        return (newexpsubidx, newsubentryfolders, removedsubentryfolders)



    def getFilepathsByExpIdSubIdx(self, regexs=None, basedir=None, pathscheme=None):
        """
        Equivalent to getSubentryfolderssByExpIdSubIdx, but for files rather than
        subentryfolders. Probably not as useful, but implemented because I got the idea.
        Returns datastructure:
            [expid][subentry_idx] = list of filenames/filepaths for subentry relative to basedir/rootdir.

        Question: How to you handle sub-folders in subentries, e.g.
            ./2014/RS190 Something/RS190c Else/good_images/<files>   ?
        """
        regexs = regexs or self.Regexs
        basedir = basedir or self.Rootdir
        pathscheme = pathscheme or self.Folderscheme
        pathscheme = pathscheme.strip().rstrip('/')
        if not pathscheme.endswith('filename'):
            pathscheme = "/".join((pathscheme, 'filename'))
        if 'filename' not in regexs:
            regexs['filename'] = re.compile('.*')

        pathmatchtuples = self.genPathmatchTupsByPathscheme(regexs, basedir, pathscheme, includefiles=True)
        pathsbyexpidsubidx = dict()
        self.Matchpriorities = {'expid' : ('experiment', 'subentry', 'filename'),
                                'subentry_idx' : ('subentry', 'filename')
                                }
        # This runs the generator. You may want to grab as much as possible now that you have it.
        for path, matchdict in pathmatchtuples:
            # Find expid and subentry idx based on the matches in matchdict.
            expid = next(expid for expid in
                            (matchdict[k].groupdict().get('expid') for k in
                                (elem for elem in self.Matchpriorities['expid'] if elem in matchdict)
                            ) if expid)
            subentry_idx = next(subentry_idx for subentry_idx in
                            (matchdict[k].groupdict().get('subentry_idx') for k in
                                (elem for elem in self.Matchpriorities['subentry_idx'] if elem in matchdict)
                            ) if subentry_idx)
            pathsbyexpidsubidx.setdefault(expid, dict()).setdefault(subentry_idx, list()).append(path)
        logger.debug("pathsbyexpidsubidx: %s", pathsbyexpidsubidx)
        return pathsbyexpidsubidx


    def renameexpfolder(self, folderpath, newbasename):
        """
        If you use this method to rename folders, it will take care of keeping the database intact.
        """
        logger.debug("INVOKED renameexpfolder(%s, %s, %s)", self, folderpath, newbasename)
        logger.warning("Not implemented")

    def renamesubentryfolder(self, folderpath, newbasename):
        """
        If you use this method to rename folders, it will take care of keeping the database intact.
        """
        folderpath = self.path.normpath(folderpath)
        newbasename = self.path.normpath(newbasename)
        if self.path.dirname(newbasename) and self.path.dirname(folderpath) != self.path.dirname(newbasename):
            logger.warning("Called renamesubentryfolder(%s, %s), but the parent dirname does not match, aborting.",
                           folderpath, newbasename)
            raise OSError("Called renamesubentryfolder(%s, %s), but the parent dirname does not match." %
                           (folderpath, newbasename))
        newbasename = self.path.basename(newbasename)
        # Check if a rename is superflouos:
        if self.path.basename(folderpath) == newbasename:
            logger.warning("folderpath and newbasename has same basename: '%s' vs '%s'.", folderpath, newbasename)
        # See if folderpath is in the database:
        SubentryfoldersByExpidSubidx = self.SubentryfoldersByExpidSubidx
        ExpidSubidxByPath = self.ExpidSubidxByFolder
        if folderpath not in ExpidSubidxByPath:
            logger.warning("Called renamesubentryfolder(%s, %s), but folderpath is not in self._expidsubidxbyfolder",
                           folderpath, newbasename)
            return
        # Try to perform filesystem rename:
        try:
            # os.rename returns None if rename operations succeeds. We should do the same.
            self.rename(folderpath, newbasename)
        except OSError as e:
            logger.error("Error while trying to rename '%s' to '%s' --> %s", folderpath, newbasename, e)
            raise ValueError("Error while trying to rename '%s' to '%s' --> %s" % (folderpath, newbasename, e))

        parentfolder = self.path.dirname(folderpath)
        newfolderpath = self.path.normpath(self.path.join(parentfolder, newbasename))

        # Update the database:
        # self.SubentryfoldersByExpidSubidx (cached property)
        # ExpidSubidxByPath = self._expidsubidxbyfolder = self.Expidsubidxbyfolder
        # self._subentryfolderset = None
        # Update ExpidSubidxByFolder:
        expid, subidx = ExpidSubidxByPath.pop(folderpath)   # remove old path
        ExpidSubidxByPath[newfolderpath] = (expid, subidx)  # insert new path
        # Update SubentryfoldersByExpidSubidx (by overwriting old value):
        SubentryfoldersByExpidSubidx[expid][subidx] = newfolderpath
        if self._subentryfolderset:
            self._subentryfolderset.discard(folderpath)
            self._subentryfolderset.add(newfolderpath)

        return newfolderpath


    def ensuresubentryfoldername(self, expid, subidx, subentryfoldername):
        """
        Can be used to ensure that a subentry-folder is correctly named.
        Returns:
            None if expid/subidx is not found in this datastore,
            None if no foldername already matches,
            True if a rename was performed,
            False if renaming failed.
        """
        subentryfoldername = self.path.basename(subentryfoldername)
        subentryfoldersbyexpidsubidx = self.SubentryfoldersByExpidSubidx
        if expid not in subentryfoldersbyexpidsubidx:
            logger.warning("Expid '%s' not present in this satellite store.", expid)
            return
        if subidx not in subentryfoldersbyexpidsubidx[expid]:
            logger.warning("Subentry '%s' for experiment '%s' not present in this satellite store.", subidx, expid)
            return
        currentfolderpath = subentryfoldersbyexpidsubidx[expid][subidx]
        currentfolderbasename = self.path.basename(currentfolderpath)
        if currentfolderbasename == subentryfoldername:
            logger.info("currentfolderbasename == subentryfoldername : '%s' == '%s'", currentfolderbasename, subentryfoldername)
            return
        try:
            # self.rename(currentfolderpath, subentryfoldername)
            # Make sure you use the encapsulated rename to update the database...
            self.renamesubentryfolder(currentfolderpath, subentryfoldername)
        except OSError as e:
            logger.warning("OSError while renaming '%s' to '%s' :: '%s", currentfolderpath, subentryfoldername, e)
            return False
        # subentryfoldersbyexpidsubidx[expid][subidx] = subentryfoldername # Uh... this should be the path... but updating in self.renamesubentryfolder
        return True


    def rename(self, path, newname):
        """ Override in filesystem/ressource-dependent subclass. """
        raise NotImplementedError("rename() not implemented for base class - something is probably wrong.")






class SatelliteFileLocation(SatelliteLocation):
    """
    This is either a local folder or another resource that has been mounted as a local file system,
    and is available for manipulation using standard filehandling commands.
    In other words, if you can use ls, cp, etc on the location, this is the class to use.
    """

    def __init__(self, locationparams):
        super(SatelliteFileLocation, self).__init__(locationparams=locationparams)
        # python3 is just super().__init__(uri, confighandler)
        # old school must be invoked with BaseClass.__init__(self, ...), like:
        # SatelliteLocation.__init__(self,
        self.ensureMount()
        self.path = os.path # Make this class work like the standard os.path.


    def ensureMount(self):
        """
        Ensures that the file location is available.
        """
        if not self.isMounted():
            logger.warning("SatelliteFileLocation does not seem to be correctly mounted (it might just be empty, but hard to tell) -- %s -- will try to mount with mountcommand...", self.URI)
            ec = self.mount()
            return ec
        logger.debug("SatelliteFileLocation correctly mounted (well, it is not empty): %s", self.URI)

    def mount(self, uri=None):
        """
        Uses mountcommand to mount; is specific to each system.
        Not implemented yet.
        Probably do something like #http://docs.python.org/2/library/subprocess.html
        """
        if uri is None:
            uri = self.URI
        mountcommand = self.Mountcommand
        if not mountcommand:
            return
        import subprocess, sys
        errorcode = subprocess.call(mountcommand, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        return errorcode

    def isMounted(self):
        """ Tests if a location is mounted (by checking if it is non-empty)."""
        return len(os.listdir(self.getRealRootPath()))

    def getRealRootPath(self):
        """ Returns self.getRealPath('.') """
        return self.getRealPath()

    def getRealPath(self, path='.'):
        """
        Why not just os.path.realpath(path) for consistency, defaulting to self.Rootdir for path?
        Because we need the URI. Rootdir is the directory APPENDED TO the location's URI.
        """
        return os.path.normpath(os.path.join(self.URI, self.Rootdir, path))

    def listdir(self, path):
        """ Implements directory listing with os.listdir(...) """
        return os.listdir(os.path.join(self.getRealRootPath(), path))

    def join(self, *paths):
        """ Joins filesystem path elements with os.path.join(*paths) """
        return os.path.join(*paths)

    def isdir(self, path):
        """ os.path.isdir(...) """
        res = os.path.isdir(os.path.join(self.getRealRootPath(), path))
        logger.debug("SatelliteFileLocation.isdir(%s) returns %s", path, res)
        return res

    def rename(self, path, newname):
        """ Renames basename of path to newname using os.rename(path, newname) """
        os.rename(path, newname)


    def syncToLocalDir(self, satellitepath, localpath):
        """
        Consider making a call to rsync and see if that is available, and only use the rest as a fallback...
        # Note, if satellitepath ends with a '/', the basename will be ''.
        # This will thus cause the contents of satellitepath to be copied into localpath, rather than localpath/foldername
        # I guess this is also the behaviour of e.g. rsync, so should be ok. Just be aware of it.
        """
        if not os.path.isdir(localpath):
            logger.debug("SatelliteFileLocation.syncToLocalDir() :: localpath '%s' is not a directory, skipping...", localpath)
            return
        realpath = self.getRealPath(satellitepath)
        # If it is just a file:
        if os.path.isfile(realpath):
            self.syncFileToLocalDir(satellitepath, localpath)
            return
        elif not os.path.isdir(realpath):
            logger.debug("SatelliteFileLocation.syncToLocalDir() :: satellitepath '%s' is not a file or directory, skipping...", realpath)
            return
        # We have a folder:
        foldername = os.path.basename(satellitepath)
        # If the folder does not exists in localpath destination, just use copytree:
        if not os.path.exists(os.path.join(localpath, foldername)):
            logger.warning(u"shutil.copytree('%s', os.path.join('%s', '%s'))", realpath, localpath, foldername)
            shutil.copytree(realpath, os.path.join(localpath, foldername))
            return True
        # foldername already exists in local directory, just recurse for each item...
        for item in os.listdir(realpath):
            self.syncToLocalDir(os.path.join(satellitepath, item), os.path.join(localpath, foldername))


    def syncFileToLocalDir(self, satellitepath, localpath):
        """
        Syncs a file to local dir.
        """
        if not os.path.isdir(localpath):
            logger.info("SatelliteFileLocation.syncFileToLocalDir() :: localpath '%s' is not a directory, skipping...", localpath)
            ## Consider perhaps creating destination instead...?
            return
        srcfilepath = self.getRealPath(satellitepath)
        if not os.path.isfile(srcfilepath):
            logger.info("SatelliteFileLocation.syncFileToLocalDir() :: file '%s' is not a file, skipping...", srcfilepath)
            return
        filename = os.path.basename(srcfilepath)
        destfilepath = os.path.join(localpath, filename)
        if not os.path.exists(destfilepath):
            logger.info("syncFileToLocalDir() :: shutil.copy2(\n'%s',\n'%s')", srcfilepath, destfilepath)
            return shutil.copy2(srcfilepath, destfilepath)
        logger.info("SatelliteFileLocation.syncFileToLocalDir() :: NOTICE, destfile exists: '%s' ", destfilepath)
        if os.path.isdir(destfilepath):
            logger.info("SatelliteFileLocation.syncFileToLocalDir() :: destfilepath '%s' is a directory in localpath, skipping...", destfilepath)
            return
        if not os.path.isfile(destfilepath):
            logger.info("SatelliteFileLocation.syncFileToLocalDir() :: destfilepath '%s' exists but is not a file, skipping...", destfilepath)
            return
        # destfilepath is a file, determine if it should be overwritten...
        if os.path.getmtime(srcfilepath) > os.path.getmtime(destfilepath):
            logger.info("SatelliteFileLocation.syncFileToLocalDir() :: srcfile '%s' is newer than destfile '%s', overwriting destfile...", srcfilepath, destfilepath)
            logger.info("shutil.copy2(%s, %s)", srcfilepath, destfilepath)
            shutil.copy2(srcfilepath, destfilepath)
        else:
            logger.info("SatelliteFileLocation.syncFileToLocalDir() :: srcfile '%s' is NOT newer than destfile '%s', NOT overwriting destfile...", srcfilepath, destfilepath)
        logger.info("\n".join("-- {} last modified: {}".format(f, modtime)
                        for f, modtime in (('srcfile ', time.ctime(os.path.getmtime(srcfilepath))),
                                           ('destfile', time.ctime(os.path.getmtime(destfilepath))))))







class SatelliteFtpLocation(SatelliteLocation):
    """
    This class is intended to deal with ftp locations.
    This has currently not been implemented.
    On linux, you can mount ftp resources as a locally-available filesystem using curlftpfs,
    and use the SatelliteFileLocation class to manipulate this location.

    Other resources that might be interesting to implement:
    (probably by interfacing with helper libraries)
    - NFS
    - http
    - webdav
    - ...
    """
    def rename(self, path, newpath):
        raise NotImplementedError("rename() not implemented for FTP class.")




location_types = {'file' : SatelliteFileLocation}


def location_factory(locationparams):
    """
    Create a satellitelocation object, deriving the correct sub-class from the protocol
    in locationparams.
    """
    protocol = locationparams.get('protocol', 'file')
    LocationCls = location_types[protocol]
    return LocationCls(locationparams=locationparams)




if __name__ == '__main__':
    pass
