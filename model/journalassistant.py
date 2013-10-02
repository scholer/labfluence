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
from page import WikiPage, WikiPageFactory, TemplateManager
from utils import *





class JournalAssistant(object):


    def __init__(self, experiment):
        self.Experiment = experiment
        self.Confighandler = experiment.Confighandler
        self.WikiPage = experiment.WikiPage
        self.VERBOSE = experiment.VERBOSE
        self.JournalFilesFolder = ".labfluence"
        self.JournalFilenameFmt = "{subentry_idx}_journal.txt"
        self.JournalFlushBackup = "{subentry_idx}_journal.flushed.bak"
        self.JournalFlushXhtml = "{subentry_idx}_journal.flushed.xhtml"
        self.Current_subentry_idx = None # This could also just be the self.Experiments.Subentries subentry dict directly...?
        self.AppendAtEndIfNoTokenFound = False



    def flushAll(self):
        for subentry_idx in self.Experiment.getSubentries().keys():
            self.flush(subentry_idx)



    def addEntry(self, text, entry_datetime=None, subentry_idx=None):
        if subentry_idx is None:
            subentry_idx = self.Current_subentry_idx
            if subentry_idx is None:
                print "JournalAssistant.flush() :: ERROR, no subentry available."
                return False
        # Make sure this is not overwritten by the default from the exp_subentry (which contains just a date)
        if entry_datetime is None:
            entry_datetime = datetime.now()
        fmt_props = self.makeSubentryProps(subentry_idx=subentry_idx, props=dict(datetime=entry_datetime)) # includes a datetime key
        journal_entry_fmt = self.getConfigEntry('journal_entry_fmt', "[{datetime:%Y%m%d %H:%M:%S}] {text}")
        #for itm in ('JournalFilenameFmt', 'JournalFlushBackup', 'JournalFlushXhtml')
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**fmt_props))
        entry_text = journal_entry_fmt.format(text=text, **fmt_props)
        journal_folderpath = os.path.dirname(journal_path)
        if not os.path.isdir(journal_folderpath):
            try:
                os.makedirs(journal_folderpath)
            except OSError as e:
                print "\n{}\nJournalAssistant.addEntry() :: Aborting due to OSError...".format(e)
        with open(journal_path, 'a') as f:
            try:
                f.write("\n"+entry_text)
            except IOError as e:
                print "\n{}\nJournalAssistant.addEntry() :: Aborting due to IOError...".format(e)
        return entry_text


    def getCacheContent(self, subentry_idx=None):
        """
        subentry_idx is e.g. 'a', 'b', 'c', ...
        """
        if subentry_idx is None:
            subentry_idx = self.Current_subentry_idx
            if subentry_idx is None:
                print "JournalAssistant.flush() :: ERROR, no subentry available."
                return False
        subentryprops = self.makeSubentryProps(subentry_idx=subentry_idx)
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**subentryprops))
        try:
            with open(journal_path) as f:
                journal_content = f.read()
            return journal_content
        except IOError as e:
            print e


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
        subentryprops = self.makeSubentryProps(subentry_idx=subentry_idx)
        #for itm in ('JournalFilenameFmt', 'JournalFlushBackup', 'JournalFlushXhtml')
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**subentryprops))
        journal_flushed_backup_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFlushBackup.format(**subentryprops)) if self.JournalFlushBackup else None
        journal_flushed_xhtml_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFlushXhtml.format(**subentryprops)) if self.JournalFlushXhtml else None
        try:
            journal_content = open(journal_path).read()
            # I read and then immediately rename. In that way I dont have to keep a lock on the file.
            # This would otherwise be required to prevent another instance from adding a journal entry to the journal
            # which will then be erased by this instance at the end of this flush.
            if os.path.exists(journal_path+'.inprogress'):
                print "\nJournalAssistant.flush() :: WARNING, old .inprogress file detected! Will include that in the flush also!"
                old_file_content = open(journal_path+'.inprogress').read()
                journal_content = "\n".join([old_file_content, journal_content])
            os.rename(journal_path, journal_path+'.inprogress')
        except IOError as e:
            print e
            return
        except OSError as e:
            print e
            return
        new_xhtml = "\n<p>"+"<br/>".join(line.strip() for line in journal_content.split('\n') if line.strip())+"</p>"
        print "new_xhtml:"
        print new_xhtml
        
        """ old logic, using token-based insertion """
#        token = self.subentryToken(subentry_idx)
#        if page.count(token) < 0:
#            alt_token = self.findAltToken(subentry_idx)
#            if not alt_token:
#                print "JournalAssistant.flush() :: WARNING, no token found. alt_token returned '{}'".format(alt_token)
#                if self.AppendAtEndIfNoTokenFound:
#                    print "--- appending at end of page..."
#                    return page.append(new_xhtml)
#                return None
#            new_xhtml = new_xhtml+"\n"+token
#            token = alt_token
#        success = page.appendAtToken(new_xhtml, token, appendBefore=True, replaceLastOccurence=True, 
#                                updateFromServer=True, persistToServer=True, 
#                                versionComment="Labfluence JournalAssistant.flush()", minorEdit=True)

        """ new logic, using regex-based insertion """
        insertion_regex_fmt = self.Confighandler.get('wiki_journal_entry_insert_regex_fmt')
        insertion_regex = insertion_regex_fmt.format(**subentryprops)
        wikipage = self.WikiPage
        versionComment = "Labfluence JournalAssistant.flush()"
        if not wikipage:
            print "Experiment.makeWikiSubentry() :: ERROR, no wikipage, aborting...\n - {}".format(self)
            return
        res = wikipage.insertAtRegex(new_xhtml, insertion_regex, versionComment=versionComment)
        
        """ clean-up and write to local backup/log files """
        if not res:
            print "\n\nJournalAssistant.flush() An error occured in page.insertAtRegex! Reverting..."
            os.rename(journal_path+'.inprogress', journal_path)
            return False
        # This should mean that everything worked ok...
        if journal_flushed_backup_path:
            try:
                with open(journal_flushed_backup_path, 'ab') as bak:
                    bak.write(journal_content)
            except IOError as e:
                print e
        if journal_flushed_xhtml_path:
            try:
                with open(journal_flushed_xhtml_path, 'ab') as bak:
                    bak.write(new_xhtml)
            except IOError as e:
                print e
        return res




    def getTemplateManager(self):
        if 'templatemanager' in self.Confighandler.Singletons:
            return self.Confighandler.Singletons['templatemanager']
        else:
            templatemgr = TemplateManager(self.Confighandler, self.Experiment.Server)
            self.Confighandler.Singletons['templatemanager'] = templatemgr
            return templatemgr


    def newExpSubentry(self, subentry_idx, subentry_titledesc=None, updateFromServer=True, persistToServer=True):
        """
        This has currently been delegated to this class, which specializes in inserting 
        content at the right location using regex'es.
        """
        wikipage = self.WikiPage
        if not wikipage:
            print "Experiment.makeWikiSubentry() :: ERROR, no wikipage, aborting...\n - {}".format(self)
            return
        # get subentry and ensure it has a titledesc if none is provided here...:
        subentry = self.Experiment.getSubentry(subentry_idx)
        if subentry_titledesc is None:
            subentry_titledesc = subentry.get('subentry_titledesc', None)
            if subentry_titledesc is None:
                print "Experiment.makeWikiSubentry() :: ERROR, no subentry_titledesc provided and none available in subentry dict either, aborting..."
                return
        fmtparams = self.Experiment.makeFormattingParams(subentry_idx=subentry_idx, props=dict(subentry_titledesc=subentry_titledesc))

        # get template and insert variables:
        templatemgr = self.getTemplateManager()
        template = templatemgr.get('exp_subentry')         #subentry_template = self.getConfigEntry('exp_subentry_template')
        interpolation_mode = self.Confighandler.get('wiki_template_string_interpolation_mode', None)
        if interpolation_mode == 'old':
            subentry_xhtml = template % fmtparams
        elif interpolation_mode == 'template':
            subentry_xhtml = string.Template(template).safe_substitution(fmtparams)
        else:
            subentry_xhtml = template.format(**fmtparams)

        # get regex and insert variables:
        regex_pat_fmt = self.getConfigEntry('wiki_exp_new_subentry_insert_regex_fmt')
        print 'fmtparams:'
        print fmtparams
        regex_pat = regex_pat_fmt.format(**fmtparams)

        if self.VERBOSE:
            print "\JournalAssistant.makeWikiSubentry() :: INFO, adding the following xhtml to wikipage '{}' using regex pattern '{}'".format(wikipage, regex_pat)
            print subentry_xhtml

        # Do page substitution:
        versionComment = "JournalAssistant: Adding new subentry {expid}{subentry_idx}".format(**fmtparams)
        res = wikipage.insertAtRegex(subentry_xhtml, regex_pat, versionComment=versionComment, updateFromServer=updateFromServer, persistToServer=persistToServer)
        
        return res



        # OBSOLETE:
#        if not pagetoken or not subentry_template:
#            print "Experiment.makeWikiSubentry() :: ERROR, could not get wiki_exp_new_subentry_token config entries:\n-subentry_template: {}\n-wiki_exp_new_subentry_token: {}".format(subentry_template, pagetoken)
#            return
#        # Two rounds of variable injection: first standard string format insertion; the next is replacement of optional $var template variables.
#        fmt_params = self.makeFormattingParams(props=dict(subentry_idx=subentry_idx, subentry_titledesc=subentry_titledesc))
#        fmt_params['subentry_journal_token'] = self.JournalAssistant.subentryToken(subentry_idx)
#        subentry_xhtml = subentry_template.format(**fmt_params)



#    def subentryToken(self, subentry_idx):
#        """
#        Deprechated; this was a dead-end mechanism. If you really want to insert special stuff, make a plugin...
#        Instead, I am using regular expressions to parse the xml and find the correct insertion place.
#        """
#        # dict:
#        subentry = self.Experiment.getSubentry(subentry_idx)
#        if 'journal_token' in subentry:
#            token = subentry['journal_token']
#        else:
#            token = subentry['journal_token'] = self.getConfigEntry('journal_subentry_token_fmt').format(random_string(16))
#            self.Experiment.PropsChanged = True
#        return token

#    def findAltToken(self, subentry_idx):
#        found = None
#        for alt_token in self.make_journal_subentry_token_alternatives(subentry_idx):
#            if self.WikiPage.count(alt_token) > 0:
#                found = alt_token
#                break
#        return found

#    def make_journal_subentry_token_alternatives(self, subentry_idx):
#        subentryprops = self.makeSubentryProps(subentry_idx=subentry_idx)
#        subentryprops['next_subentry_idx'] = increment_idx(subentry_idx)
#        token_fmts = ["<h4>{next_subentry_idx}", "<h2>Results"]
#        tokens = [token_fmt.format(subentryprops) for token_fmt in token_fmts]
#        return tokens



    def makeSubentryProps(self, subentry_idx=None, props=None):
        return self.Experiment.makeFormattingParams(subentry_idx, props)
#        subentryprops = dict()
#        subentryprops.update(self.Experiment.Props)
#        subentryprops.update(props) # doing this after to ensure no override.
#        exp_subentryid_fmt = self.getConfigEntry('exp_subentryid_fmt')
#        subentryprops['subentryid'] = exp_subentryid_fmt



    def getConfigEntry(self, cfgkey, default=None):
        return self.Experiment.getConfigEntry(cfgkey)





if __name__ == '__main__':

    from experiment import Experiment
    if True:
        ldir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
        ch = ExpConfigHandler(pathscheme='default1')
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=1, prompt='auto', autologin=True)
        e = Experiment(confighandler=ch, server=server, localdir=ldir, VERBOSE=10)
        e.attachWikiPage(dosearch=True)
        ja = e.JournalAssistant
        ja.Current_subentry_idx = 'c'


    def test_addEntry():
        ja.addEntry("Buffer: 10/100 mM HEPES/KCl pH with 0.5 mM biotin."+random_string(5))
        ja.addEntry("""Adding 100 ul buffer to RS102b and running through amicon 3k filter. I dont dilute to 400 ul because I want to be able to trace unreacted DBCO-ddUTP.
Washing retentate 4 more times with 400 ul buffer, collecting filt2-3 and filt4-6.""")
        ja.addEntry("""Doing UVvis quant on nanodrop (if it is still running during the chemists move).
- EDIT: Nanodrop is down due to move, so no quant. I will assume we have 75% yield and recovery during synthesis, so 1.5 nmol in 30 ul giving a concentration of 1500pmol/30ul = 50 uM. (?)""")

    def test_getCacheContent():
        print ja.getCacheContent()

    def test_flush():
        ja.addEntry("test entry for flush test"+random_string(10))
        ja.flush()


    print " ----- test addEntry() -------------- "
    test_addEntry()
    print " ------test getCacheContent() ------- "
    test_getCacheContent()
    print " ------test flush() ----------------- "
    test_flush()
    print " ------journalassistant testing finished ------- "



