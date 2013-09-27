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
import random


#from experiment import Experiment # importing from experiment will produce circular import reference. Import under test instead.
from server import ConfluenceXmlRpcServer
from confighandler import ExpConfigHandler
from page import WikiPage, WikiPageFactory
from utils import *





class JournalAssistant(object):


    def __init__(self, experiment):
        self.Experiment = experiment
        self.Confighandler = experiment.Confighandler
        self.WikiPage = experiment.WikiPage
        self.JournalFilesFolder = ".labfluence"
        self.JournalFilenameFmt = "{subentry_idx}_journal.txt"
        self.JournalFlushBackup = "{subentry_idx}_journal.flushed.bak"
        self.JournalFlushXhtml = "{subentry_idx}_journal.flushed.xhtml"
        self.Current_subentry_idx = None # This could also just be the self.Experiments.Subentries subentry dict directly...?
        self.AppendAtEndIfNoTokenFound = False



    def flushAll(self):
        for subentry_idx in self.Experiment.Subentries:
            self.flush(subentry_idx)


    def flush(self, subentry_idx=None):
        """
        subentry_idx is e.g. 'a', 'b', 'c', ...
        """
        if subentry_idx is None:
            subentry_idx = self.Current_subentry_idx
        if subentry_idx is None:
            print "JournalAssistant.flush() :: ERROR, no subentry available."
            return False
        page = self.WikiPage
        subentryprops = self.makeSubentryProps(dict(subentry_idx=subentry_idx))
        #for itm in ('JournalFilenameFmt', 'JournalFlushBackup', 'JournalFlushXhtml')
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**subentryprops))
        journal_flushed_backup_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFlushBackup.format(**subentryprops)) if self.JournalFlushBackup else None
        journal_flushed_xhtml_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFlushXhtml.format(**subentryprops)) if self.JournalFlushXhtml else None
        try:
            journal_content = open(journal_path).read()
            # I read and then immediately rename. In that way I dont have to keep a lock on the file.
            # This would otherwise be required to prevent another instance from adding a journal entry to the journal
            # which will then be erased by this instance at the end of this flush.
            os.rename(journal_path, journal_path+'.inprogress')
        except IOError as e:
            print e
            return
        except OSError as e:
            print e
            return
        new_xhtml = "\n<p>"+"</br>".join(line.strip() for line in journal_content.split('\n') if line.strip())+"</p>"
        print "new_xhtml:"
        print new_xhtml
        token = self.subentryToken(subentry_idx)
        if page.count(token) < 0:
            alt_token = self.findAltToken(subentry_idx)
            if not alt_token:
                print "JournalAssistant.flush() :: WARNING, no token found. alt_token returned '{}'".format(alt_token)
                if self.AppendAtEndIfNoTokenFound:
                    print "--- appending at end of page..."
                    return page.append(new_xhtml)
                return None
            new_xhtml = new_xhtml+"\n"+token
            token = alt_token
        success = page.appendAtToken(new_xhtml, token, appendBefore=True, replaceLastOccurence=True, 
                                updateFromServer=True, persistToServer=True, 
                                versionComment="Labfluence JournalAssistant.flush()", minorEdit=True)
        if not success:
            print "\n\nJournalAssistant.flush() An error occured in page.appendAtToken! Reverting..."
            os.rename(journal_path+'.inprogress', journal_path)
            return False
        # This should mean that everything worked ok...
        if journal_flushed_backup_path:
            try:
                with open(journal_flushed_backup_path, 'ab') as bak:
                    bak.write(content)
            except IOError as e:
                print e
        if journal_flushed_xhtml_path:
            try:
                with open(journal_flushed_xhtml_path, 'ab') as bak:
                    bak.write(new_xhtml)
            except IOError as e:
                print e
        return res


    def addEntry(self, text, entry_datetime=None, subentry_idx=None):
        if subentry is None:
            subentry = self.CurrentSubentry
        if subentry is None:
            print "JournalAssistant.flush() :: ERROR, no subentry available."
            return False
        if entry_datetime is None:
            entry_datetime = datetime.now()
        props = self.makeSubentryProps(dict(subentry_idx=subentry_idx))
        journal_entry_fmt = self.getConfigEntry('journal_entry_fmt', "[{datetime:%Y%m%d %H:%M:%S}] {text}")
        #for itm in ('JournalFilenameFmt', 'JournalFlushBackup', 'JournalFlushXhtml')
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**props))
        entry_text = journal_entry_fmt.format(text=text, datetime=entry_datetime, **props)
        with open(journal_path, 'a') as f:
            f.write("\n"+entry_text)
        return entry_text


    def getCacheContent(self, subentry_idx):
        """
        subentry_idx is e.g. 'a', 'b', 'c', ...
        """
        subentryprops = self.makeSubentryProps(dict(subentry_idx=subentry_idx))
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**subentryprops))
        try:
            journal_content = open(journal_path).read()
            return journal_content
        except IOError as e:
            print e


    def subentryToken(self, subentry_idx):
        """
        
        """
        # dict:
        subentry = self.Experiment.getSubentry(subentry_idx)
        if 'journal_token' in subentry:
            token = subentry['journal_token']
        else:
            token = subentry['journal_token'] = self.getConfigEntry('journal_subentry_token_fmt').format(random_string(16))
        return token


    def findAltToken(self, subentry_idx):
        found = None
        for alt_token in self.make_journal_subentry_token_alternatives(subentry_idx):
            if self.WikiPage.count(alt_token) > 0:
                found = alt_token
                break
        return found


    def make_journal_subentry_token_alternatives(self, subentry_idx):
        subentryprops = self.makeSubentryProps(dict(subentry_idx=subentry_idx))
        subentryprops['next_subentry_idx'] = increment_idx(subentry_idx)
        token_fmts = ["<h4>{next_subentry_idx}", "<h2>Results"]
        tokens = [token_fmt.format(subentryprops) for token_fmt in token_fmts]
        return tokens



    def makeSubentryProps(self, props):
        subentryprops = dict()
        subentryprops.update(self.Experiment.Props)
        subentryprops.update(props) # doing this after to ensure no override.
        exp_subentryid_fmt = self.getConfigEntry('exp_subentryid_fmt')
        subentryprops['subentryid'] = exp_subentryid_fmt



    def getConfigEntry(self, cfgkey, default=None):
        return self.Experiment.getConfigEntry(cfgkey)





if __name__ == '__main__':

    from experiment import Experiment
    ldir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
    ch = ExpConfigHandler(pathscheme='default1')
    server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=1, prompt='auto', autologin=True)
    e = Experiment(confighandler=ch, localdir=ldir, VERBOSE=10)
    ja = e.JournalAssistant
    ja.Current_subentry_idx = 'a'


    def test_addEntry():
        ja.addEntry("test entry for addEntry test"+random_string(10))

    def test_flush():
        ja.addEntry("test entry for flush test"+random_string(10))
        ja.flush()


