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


from confighandler import ExpConfigHandler
from page import WikiPage, WikiPageFactory
from journalassistant import JournalAssistant
from utils import *

try:
    import magic
    magic_available = True
    magicmime = magic.Magic(mime=True)
except ImportError:
    magic_available = False
    magicmime = None
    import mimetypes



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
                 doparseLocaldirSubentries=True, subentry_regex_prog=None, loadYmlFn='.labfluence.yml'):
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
        self.WikiPage = wikipage
        """ You should probably link self.Props to confighandler if it is provided..."""
        self.Props = dict() if props is None else props
        #self.Subentries = list() # list of experiment sub-entries
        # edit, subentries is now an element in self.Props, makes it easier to save info...
        self.Subentries_regex_prog = subentry_regex_prog # Allows recycling of a single compiled regex for faster directory tree processing.
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
        #self.Localdir = localdir # Currently not updating; this might be relative...
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
        elif not self.Props:
            # self.Props is still empty. Attempt to populate it using 
            # first the localdirpath and then the wikipage.
            exp_regex = self.getConfigEntry('exp_series_regex')
            exp_regex_prog = re.compile(exp_regex)
            regex_match = exp_regex_prog.match(self.Foldername)
            if regex_match:
                self.Props.update(regex_match.groupdict())
            elif wikipage:
                if not wikipage.Struct:
                    wikipage.reloadFromServer()
                regex_match = exp_regex_prog.match(wikipage.Struct.get('title')
                if regex_match:
                    self.Props.update(regex_match.groupdict())

        if loadYmlFn and not confighandler:
            fn = os.path.join(self.Localdirpath, loadYmlFn) if self.Localdirpath else loadYmlFn
            self.loadProps(fn)

        if doparseLocaldirSubentries and self.Localdirpath:
            self.parseLocaldirSubentries()
        
        """
        I plan to allow for saving file histories, having a dict 
        Fileshistory['RS123d subentry_titledesc/RS123d_c1-grid1_somedate.jpg'] -> list of {datetime:<datetime>, md5:<md5digest>} dicts.
        This will make it easy to detect simple file moves/renames and allow for new digest algorithms.
        """
        #self.Fileshistory = dict()
        self.loadFileshistory()
        if not self.WikiPage:
            wikipage = self.attachWikiPage()
        self.JournalAssistant = JournalAssistant(self)



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
    STUFF RELATED TO WIKI PAGE HANDLING
    """

    def attachWikiPage(self, pageId=None, pagestruct=None, dosearch=False):
        if pageId is None:
            if pagestruct and 'id' in pagestruct:
                pageId = pagestruct['id']
            else:
                pageId = self.Props.get('wiki_pageId')
        if not pageId and self.Server and dosearch:
            print "Experiment.attachWikiPage() :: Searching on server..."
            spaceKey = self.getConfigEntry('wiki_exp_root_spaceKey')
            pageTitle = self.Foldername # No reason to make this more complicated...
            try:
                pagestruct = self.Server.getPage(spaceKey=spaceKey, pageTitle=pageTitle)
                pageId = pagestruct['id']
            except xmlrpclib.Fault:
                # perhaps do some searching...?
                pass
        if not pageId:
            print "\nExperiment.attachWikiPage() :: ERROR, no pageId found...\n"
            return
        self.WikiPage = WikiPage(pageId, self.Server, pagestruct)
        return self.WikiPage


    def makeWikiPage(self):
        pagefactory = WikiPageFactory(wikiserver, ch)
        current_datetime = datetime.now()
        fmt_params = dict(datetime=current_datetime,
                          date=current_datetime)
        fmt_params.update(self.Props)
        self.WikiPage = factory.new('exp_page', fmt_params=fmt_params)
        return self.WikiPage


    def makeWikiSubentry(self, subentry_idx):
        


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
        if magic_available:
            mimetype = magicmime.from_file(filepath)
        else:
            mimetype = mimetypes.guess_type(filepath)
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
        Returns a list of attachments if succeeded, 
        False if failed and None if no attemt was made to upload due to a local Error.
        
        """
        if not getattr(self, 'WikiPage', None):
            print "Experiment.uploadAttachment() :: ERROR, no wikipage attached to this experiment object\n - {}".format(self)
            return None
        print "Experiment.listAttachments() :: Not implemented yet - take care ;)"




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

    # deprechated version...
#    def getConfigEntry(self, key, path=None):
#        confighandler = self.Confighandler or getattr(self.Manager, 'Confighandler', None)
#        if not confighandler:
#            print "No confighandler available..."
#            return
#        return confighandler.get(key, path=path)


    def getAbsPath(self):
        return os.path.abspath(self.Localdirpath)


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





    """ STUFF RELATED TO SUBENTRIES """

    def getSubentry(self, subentry_idx, ensureExisting=True):
        if subentry_idx not in self.Subentries:
            self.initSubentriesUpTo(subentry_idx)
        return self.Subentries[subentry_idx]


    def initSubentriesUpTo(self, subentry_idx):
        if not self.Subentries:
            self.Subentries = OrderedDict()
        for idx in idx_generator(subentry_idx):
            if idx not in self.Subentries:
                self.Subentries[idx] = dict()


    def parseLocaldirSubentries(self, directory=None):
        """
        make self.Subentries by parsing local dirs like '20130106 RS102f PAGE of STV-col11 TR staps (20010203)'.
        
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
                #if 'subentry_idx' in props:
                current_idx = props['subentry_idx']
                # edit: how could subentry_idx possibly not be in res.groupdict? only if not included in regex?
                # anyways, if not present, simply making a new index could be dangerous; what if the directories are not sorted and the next index is not right?
                #else:
                #    current_idx =  self.getNewSubentryIdx() # self.subentry_index_increment(current_idx)
                subentries.setdefault(current_idx, dict()).update(props)
        #self.Props['exp_subentries'] = subentries


    def getNewSubentryIdx(self):
        if not self.Subentries:
            return 'a'
        return increment_idx(self.Subentries.keys()[-1])


    # Deprechated; use utils.increment_idx() instead.
#    def subentry_index_increment(self, current_idx='a'):
#        if isinstance(current_idx, basestring):
#            return chr( ord('current_idx') +1 )


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




    """ -------------------------------------------
    --- STUFF related to local file management ----
    ------------------------------------------- """

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



    """ Other stuff... """

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
