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

from confighandler import ExpConfigHandler


class Experiment(object):
    """
    The Prop attribute is a dict which include:
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


    def __init__(self, localdir=None, props=None, server=None, manager=None, confighandler=None, regex_match=None, VERBOSE=0, 
                 doparseLocaldirSubentries=True, subentry_regex_prog=None, loadYmlFn='.labfluence'):
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
        self.Server = server
        self.Manager = manager
        self.Confighandler = confighandler
        """ You should probably link self.Props to confighandler if it is provided..."""
        self.Props = dict() if props is None else props
        #self.Subentries = list() # list of experiment sub-entries
        # edit, subentries is now an element in self.Props, makes it easier to save info...
        self.Subentries_regex_prog = subentry_regex_prog # Allows recycling of a compiled regex for faster processing...
        self.ConfigFn = loadYmlFn
        if localdir is None:
            localdir = self.Props.get('localdir')
        # More logic may be required, e.g. if the dir is relative to e.g. the local_exp_rootDir.
        parentdirpath, foldername = os.path.split(localdir)
        if not parentdirpath:
            # The path provided was relative, e.g. "RS102 Strep-col11 TR annealed with biotin".
            # Assume that the experiment is based in the local_exp_subDir:
            parentdirpath = self.getConfigEntry('local_exp_subDir')
        self.Parentdirpath = parentdirpath
        if not foldername:
            print "Experiment.__init__() :: Huh?"
        self.Foldername = foldername
        self.Localdirpath = os.path.join(self.Parentdirpath, self.Foldername)
        self.Localdir = localdir # Currently not updating; this might be relative...
        """ I belive this should be sufficient to create a stable link... """
        if self.Confighandler:
            cfg = self.Confighandler.getHierarchicalConfig(self.Localdirpath)
            cfg.update(self.Props)
            self.Props = cfg

        self.Subentries = self.Props.setdefault('exp_subentries', OrderedDict())
        if regex_match:
            gd = regex_match.groupdict()
            """ regex is often_like "(?P<expid>RS[0-9]{3}) (?P<exp_title_desc>.*)" """
            #for k, reg in (('expid', 'expid_str'), ('exp_series_shortdesc', 'exp_title_desc'))
            self.Props.update(gd)

        if loadYmlFn and not confighandler:
            if self.Localdirpath:
                fn = os.path.join(self.Localdirpath, loadYmlFn)
            else:
                fn = loadYmlFn
            self.loadProps(fn)

        if doparseLocaldirSubentries and self.Localdirpath:
            self.parseLocaldirSubentries()



    def loadProps(self, fn, clearfirst=False):
        if clearfirst:
            self.Props.clear()
        if not fn:
            print "Experiment.loadProps() :: fn is '{}', aborting...".format(fn)
            return
        try:
            self.Props.update(yaml.load(fn))
        except IOError, e:
            print e
        except ValueError, e:
            print e

    def saveProps(self, path=None):
        if path is None:
            path = self.Localdir
        if self.Confighandler:
            if not os.path.isdir(path):
                path = os.path.dirname(path)
            self.Confighandler.updateAndPersist(path, self.Props)
        else:
            if os.path.isdir(path):
                path = os.path.normpath(os.path.join(self.Localdir, self.ConfigFn))
            print "Experiment.saveProps() :: saving directly to file '{}' (not using confighandler)".format(path)
            yaml.dump(self.Props, open(path, 'wb'))


    def parseLocaldirSubentries(self, directory=None):
        """
        make self.Exp_subentries by parsing local dirs like '20130106 RS102f PAGE of STV-col11 TR staps (20010203)'.
        
        """
        if directory is None:
            directory = self.Localdir
        if directory is None:
            print "Experiment.parseLocaldirSubentries() :: ERROR, no directory provided and no localdir in Props attribute."
            return
#        if not self.Subentries_regex_prog and not self.Manager:
#            print "Experiment.parseLocaldirSubentries() :: ERROR, no self.Subentries_regex_prog and no self.Manager; cannot obtain exp_subentry_regex string."
        # Consider using glob.re
        if self.Subentries_regex_prog:
            regex_prog = self.Subentries_regex_prog
        else:
            regex_str = self.getConfigEntry('exp_subentry_regex', directory) #getExpSubentryRegex()
            if not regex_str:
                print "Warning, no exp_subentry_regex entry found in config!"
            regex_prog = re.compile(regex_str)
        localdirs = sorted([dirname for dirname in os.listdir(directory) if os.path.isdir(os.path.abspath(os.path.join(directory, dirname) ) ) ])
        if self.VERBOSE:
            print "Experiment.parseLocaldirSubentries() :: searching in directory '{}'".format(directory)
            print "Experiment.parseLocaldirSubentries() :: regex = '{}'".format(regex_str)
            print "Experiment.parseLocaldirSubentries() :: localdirs = {}".format(localdirs)
        subentries = self.Props.setdefault('exp_subentries', OrderedDict())
        current_idx = 'a'
        for localdir in localdirs:
            res = regex_prog.match(localdir)
            if self.VERBOSE:
                print "{} found when testing '{}' dirname against regex '{}'".format("MATCH" if res else "No match", localdir, regex_str)
            if res:
                props = res.groupdict()
                # I allow for regex with multiple date entries, i.e. both first and last.
                datekeys = filter(lambda x: 'date' in x and len(x)>4, props.keys())
                for k in sorted(datekeys):
                    val = props.pop(k)
                    if val:
                        props['date']=val
                props['dirname'] = localdir
                if 'subentry_idx' in props:
                    current_idx = props['subentry_idx']
                else:
                    current_idx = self.subentry_index_increment(current_idx)
                subentries.setdefault(current_idx, dict()).update(props)
        #self.Props['exp_subentries'] = subentries


    def subentry_index_increment(self, current_idx='a'):
        if isinstance(current_idx, basestring):
            return chr( ord('current_idx') +1 )


    def getConfigEntry(self, key, path=None):
        confighandler = self.Confighandler or getattr(self.Manager, 'Confighandler', None)
        if not confighandler:
            print "No confighandler available..."
            return
        return confighandler.get(key, path=path)

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


    def __repr__(self):
        return "Experiment in ('{}'), with Props:{}".format(self.Localdir, self.Props)


    def update(self, other_exp):
        """
        Update this experiment with the content from other_exp.
        """
        raise NotImplementedError("Experiment.update is not implemented...")




if __name__ == '__main__':
    def setup1():
        confighandler = ExpConfigHandler( pathscheme='default1', VERBOSE=1 )
        print "----"
        ldir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
        e = Experiment(confighandler=confighandler, localdir=ldir, VERBOSE=10)
        return e

    def test1():
        e = setup1()
        print e
        return e

    def test2():
        e = setup1()
        e.Props['test_key'] = datetime.now().strftime("%Y%m%d-%H%M%S") # you can use strptime to parse a formatted date string.
        print "\n\nSaving props:"
        e.saveProps()

    test2()

