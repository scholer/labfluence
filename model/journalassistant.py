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
# pylint: disable-msg=C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221,E1101,W0402
# messages:
#   C0301: Line too long (max 80), R0902: Too many instance attributes (includes dict())
#   C0302: too many lines in module; R0201: Method could be a function; W0142: Used * or ** magic
#   R0904: Too many public methods (20 max); R0913: Too many arguments;
#   W0221: Arguments differ from overridden method,
#   W0402: Use of deprechated module (e.g. string)
#   E1101: Instance of <object> has no <dynamically obtained attribute> member.

# To fix Pylint E1101 false-positive, check out
# http://stackoverflow.com/questions/14280372/pylint-false-positive-e1101-instance-of-popen-has-no-poll-member
# I am almost certain these issues will be fixed in time, but for now, just disable-msg E1101.
"""
Journalassistant module includes all logic to handle journal entries,
including local file-based caching and invokation of WikiPage to write
the entries to the wiki page in the right position.
"""

import os
#import shutil
#from codecs import open
import codecs
#import yaml
#import re
import string
from datetime import datetime
#from collections import OrderedDict
#import xmlrpclib
#import hashlib
#import random
import logging
logger = logging.getLogger(__name__)


#from experiment import Experiment # importing from experiment will produce circular import reference. Import under test instead.
#from server import ConfluenceXmlRpcServer
#from confighandler import ExpConfigHandler
#from page import WikiPage, WikiPageFactory, TemplateManager
from page import TemplateManager
#from utils import *  # This will override the logger with the logger defined in utils.
#from utils import random_string

# Override default open method to provide UTF support.
def open_utf(fp, mode='r'):
    """
    Provides unicode-capable opening of files using codecs.open.
    Not required for python3.
    """
    return codecs.open(fp, mode, encoding='utf-8')


class JournalAssistant(object):
    """
    Class for handling journal entries.
    Entries will be cached locally until they are successfully written to a WikiPage.
    """

    def __init__(self, experiment):
        self.Experiment = experiment
        self.JournalFilesFolder = ".labfluence"
        self.JournalFilenameFmt = "{subentry_idx}_journal.txt"
        self.JournalFlushBackup = "{subentry_idx}_journal.flushed.bak"
        self.JournalFlushXhtml = "{subentry_idx}_journal.flushed.xhtml"
        #self.Current_subentry_idx = None
        self._current_subentry_idx = None
        self.AppendAtEndIfNoTokenFound = False

    @property
    def WikiPage(self):
        """WikiPage property"""
        return self.Experiment.WikiPage

    @property
    def Confighandler(self):
        """Confighandler property"""
        return self.Experiment.Confighandler

    @property
    def Current_subentry_idx(self, ):
        """ Current_subentry_idx property.
        Returns self._current_subentry_idx if set, otherwise the first available
        Experiment subentry
        """
        if self._current_subentry_idx:
            return self._current_subentry_idx
        if self.Experiment.Subentries:
            return min(self.Experiment.Subentries.keys())
        return None

    @Current_subentry_idx.setter
    def Current_subentry_idx(self, value):
        """property setter: Set current subentry"""
        if value not in self.Experiment.Subentries:
            logger.warning("subentry %s not in Experiment.Subentries...")
        self._current_subentry_idx = value


    def addEntry(self, text, entry_datetime=None, subentry_idx=None):
        """
        Adds an entry/line to the journal cache (stored locally as a file on disk).
        """
        if subentry_idx is None:
            subentry_idx = self.Current_subentry_idx
            if subentry_idx is None:
                logger.warning( "JournalAssistant.addEntry() :: ERROR, no subentry available. self.Current_subentry_idx is: %s", subentry_idx)
                return False
        # Make sure this is not overwritten by the default from the exp_subentry (which contains just a date)
        if entry_datetime is None:
            entry_datetime = datetime.now()
        fmt_props = self.makeSubentryProps(subentry_idx=subentry_idx, props=dict(datetime=entry_datetime)) # includes a datetime key
        ### Python 2.x only: Make sure the format string is unicode:
        journal_entry_fmt = unicode(self.getConfigEntry('journal_entry_fmt', "[{datetime:%Y%m%d %H:%M:%S}] {text}"))
        #for itm in ('JournalFilenameFmt', 'JournalFlushBackup', 'JournalFlushXhtml')
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**fmt_props))
        entry_text = journal_entry_fmt.format(text=text, **fmt_props)
        journal_folderpath = os.path.dirname(journal_path)
        if not os.path.isdir(journal_folderpath):
            try:
                os.makedirs(journal_folderpath)
            except OSError as e:
                logger.warning("JournalAssistant.addEntry() failed while doing os.makedirs(journal_folderpath) due to an OSError: %s", e)
                return False
        logger.debug("Adding entry: '%s' to file: %s", entry_text, journal_path)
        if self._writetofile(journal_path, entry_text):
            return entry_text
        else:
            logger.info("self._writetofile seems to have failed, returning False...")
            return False

    def _writetofile(self, journal_path, entry_text):
        """
        Does actual writing to file. Refactored and encapsulated
        in separate method to allow better testing/mocking.
        """
        # Open journal file in append mode:
        with open_utf(journal_path, 'a') as f:
            try:
                #logger.debug("Entry text type: %s", type(entry_text))
                f.write(u"\n"+entry_text)
            except IOError as e:
                logger.warning("JournalAssistant.addEntry() failed due to an IOError: %s", e)
                return False
        logger.debug("%s chars written to file: %s", len(entry_text), journal_path)
        return True

    def _readfromfile(self, journal_path):
        """
        Returns the content of file <journal_path>.
        """
        try:
            with open_utf(journal_path) as f:
                journal_content = f.read()
            logger.debug("%s chars read from journal cache in file '%s'", len(journal_content), journal_path)
            return journal_content
        except IOError as e:
            logger.debug("could not read from file '%s', probably because there is none. Error was: %s", journal_path, e)


    def getCacheContent(self, subentry_idx=None):
        """
        subentry_idx is e.g. 'a', 'b', 'c', ...
        """
        logger.debug("cache requested for subentry_idx: '%s'", subentry_idx)
        if subentry_idx is None:
            subentry_idx = self.Current_subentry_idx
            if subentry_idx is None:
                logger.warning("JournalAssistant ERROR, no subentry available.")
                return False
        subentryprops = self.makeSubentryProps(subentry_idx=subentry_idx)
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**subentryprops))
        logger.debug("Reading journal cache for subentry '%s' in file: '%s'", subentry_idx, journal_path)
        return self._readfromfile(journal_path)

    def flushAll(self):
        """
        Will attempt to flush the entry cache for all subentries.
        Returns True if successful and False otherwise.
        """
        for subentry_idx in self.Experiment.Subentries.keys():
            self.flush(subentry_idx)

    def insertJournalContentOnWikiPage(self, journal_content, subentryprops):
        """
        Convert the journal entries in journal_content for subentry with subentryprops
        and insert it on/with self.WikiPage.
        """
        wikipage = self.WikiPage
        if not wikipage:
            logger.warning("ERROR, no wikipage, aborting... (%s)", self)
            return False
        new_xhtml = "<p>"+"<br/>".join(line.strip() for line in journal_content.split('\n') if line.strip())+"</p>"
        logger.debug("%s, new_xhtml: %s", self.__class__.__name__, new_xhtml)
        ### new logic, using regex-based insertion ###
        insertion_regex_fmt = self.Confighandler.get('wiki_journal_entry_insert_regex_fmt')
        insertion_regex = insertion_regex_fmt.format(**subentryprops)
        subentry_idx = subentryprops['subentry_idx']
        versionComment = u"Labfluence JournalAssistant.flush() for subentry {[expid]}{}".format(subentryprops, subentry_idx)
        res = wikipage.insertAtRegex(new_xhtml, insertion_regex, versionComment=versionComment)
        if not res:
            logger.debug("wikipage.insertAtRegex returned '%s', probably due to failed regex matching of regex_pat '%s', derived from regex_pat_fmt '%s'. self.WikiPage.Struct['content']) is:%s",
                          res, insertion_regex, insertion_regex_fmt, wikipage.Struct if not wikipage.Struct else wikipage.Struct['content'] )
            return False, ""
        return res, new_xhtml


    def flush(self, subentry_idx=None):
        """
        subentry_idx is e.g. 'a', 'b', 'c', ...
        Original implementation would read the file and then rename to temporary filename during flush.
        However, it is much better to keep the file locked in the brief time during the flush.
        Changelog:
        - Removed all legacy code related to .inprogress file handling.

        """
        if subentry_idx is None:
            subentry_idx = self.Current_subentry_idx
        if subentry_idx is None:
            logger.info("flush invoked, but no subentry selected/available so aborting flush request and returning False.")
            return False
        # Do a quick check that a WikiPage object is attached.
        # If it is not, reading the cache content is a moot point.
        if not self.WikiPage:
            logger.info("Experiment.flush() Could not flush, no wikipage, aborting... (%s)", self)
            return False
        # Generate subentry properties from subentry_idx:
        subentryprops = self.makeSubentryProps(subentry_idx=subentry_idx)
        journal_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFilenameFmt.format(**subentryprops))
        try:
            with open_utf(journal_path) as journalfh:
                journal_content = journalfh.read()
                logger.debug("Journal content read from file '%s': %s", journal_path, journal_content)
                res, new_xhtml = self.insertJournalContentOnWikiPage(journal_content, subentryprops)
                if not res:
                    logger.warning("An error occured in page.insertAtRegex causing it to return '%s'. Returning False.", res)
                    return False
            # Instead of instantly deleting the cache, I keep a .lastflush backup.
            # After successful flush, the earlier .lastback file is removed and the
            # cache that was just flushed is renamed to .lastflush.
            try:
                os.remove(journal_path+'.lastflush')
            except OSError as e:
                if os.path.exists(journal_path+'.lastflush'):
                    logger.warning("OSError while removing .lastflush file (%s) for subentry_idx %s, however the file/dir does exists!", journal_path+'.lastflush', subentry_idx)
                else:
                    logger.debug("File '%s' does not exist (the subentry, '%s', is probably new).", journal_path+'.lastflush', subentry_idx)
            try:
                os.rename(journal_path, journal_path+'.lastflush')
            except (IOError, OSError) as e:
                logger.warning("IOError/OSError while renaming journal entry file %s to %s. Error is: %s", journal_path, journal_path+'.lastflush', e)
        except (IOError, OSError) as e:
            if os.path.exists(journal_path+'.lastflush'):
                logger.error("IOError/OSError during flush: %s -- however, the file/directory does exist!", e)
                logger.error("This can be caused by e.g.: a) permission issue, b) the filepath is a directory, c) The file is locked. Either way, this should be resolved manually by you (the user).")
            else:
                logger.debug("File '%s' does not exist (the subentry, '%s', is probably new). Nothing to flush.", journal_path+'.lastflush', subentry_idx)
            return
        # This should mean that everything worked ok...
        # Write journal entries to backup file (containing all flushed entries). Also for equivalent file with xhtml entries.
        journal_flushed_backup_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFlushBackup.format(**subentryprops)) if self.JournalFlushBackup else None
        journal_flushed_xhtml_path = os.path.join(self.Experiment.getAbsPath(), self.JournalFilesFolder, self.JournalFlushXhtml.format(**subentryprops)) if self.JournalFlushXhtml else None
        if journal_flushed_backup_path:
            try:
                with open_utf(journal_flushed_backup_path, 'ab') as bak:
                    # File is opened in 'append, binary' mode.
                    bak.write(journal_content)
            except IOError as e:
                logger.warning("IOError while appending flushed journal entries (text) to backup file: '%s'. Error is: %s", journal_flushed_backup_path, e)
        if journal_flushed_xhtml_path:
            try:
                with open_utf(journal_flushed_xhtml_path, 'ab') as bak:
                    bak.write(new_xhtml)
            except IOError as e:
                logger.warning("IOError while appending flushed journal xhtml to backup file: '%s'. Error is: %s", journal_flushed_xhtml_path, e)
        return res

    def getTemplateManager(self):
        """
        Get a template manager, which is used to retrieve templates,
        located either locally as a config, or on the wiki server.
        """
        if 'templatemanager' in self.Confighandler.Singletons:
            return self.Confighandler.Singletons['templatemanager']
        else:
            templatemgr = TemplateManager(self.Confighandler, self.Experiment.Server)
            self.Confighandler.Singletons['templatemanager'] = templatemgr
            return templatemgr


    def newExpSubentry(self, subentry_idx, subentry_titledesc=None, updateFromServer=True, persistToServer=True):
        """
        This has currently been delegated from model.Experiment to this class,
        since this JournalAssistant class specializes in constructing regexes
        that can be used to insert content at the right location on wikipages.
        Still, most of the logic is handled by wikipage.insertAtRegex.
        Parameters:
        - subentry_idx, subentry_titledesc : The info for the subentry to insert.
        - updateFromServer: Update the Experiment's WikiPage object before performing the insertion. Defaults is True.
        - updateFromServer: Persist the wikipage (struct) after performing the insertion. Defaults is True.

        """
        wikipage = self.WikiPage
        if not wikipage:
            logger.warning( "Experiment.makeWikiSubentry() :: ERROR, no wikipage, self.WikiPage is '%s', aborting...", wikipage)
            return
        # get subentry and ensure it has a titledesc if none is provided here...:
        try:
            subentry = self.Experiment.Subentries[subentry_idx]
        except KeyError:
            logger.warning("Subentry '%s' does not exist, aborting...", subentry_idx)
            return
        if subentry_titledesc is None:
            subentry_titledesc = subentry.get('subentry_titledesc', None)
            if subentry_titledesc is None:
                logger.warning(  "Experiment.makeWikiSubentry() :: ERROR, no subentry_titledesc provided and none available in subentry dict either, aborting..." )
                return
        fmtparams = self.Experiment.makeFormattingParams(subentry_idx=subentry_idx, props=dict(subentry_titledesc=subentry_titledesc))

        # get template and insert variables:
        template = self.getTemplateManager().get('exp_subentry')         #subentry_template = self.getConfigEntry('exp_subentry_template')
        interpolation_mode = self.Confighandler.get('wiki_template_string_interpolation_mode', None)
        if interpolation_mode == 'old':
            subentry_xhtml = template % fmtparams
        elif interpolation_mode == 'template':
            subentry_xhtml = string.Template(template).safe_substitution(fmtparams)
        else:
            subentry_xhtml = template.format(**fmtparams)

        # get regex and insert variables:
        regex_pat_fmt = self.getConfigEntry('wiki_exp_new_subentry_insert_regex_fmt')
        regex_pat = regex_pat_fmt.format(**fmtparams)
        logger.debug("Adding the following xhtml to wikipage '%s' using regex pattern '%s': %s", wikipage, regex_pat, subentry_xhtml )

        # Do page substitution:
        versionComment = "JournalAssistant: Adding new subentry {expid}{subentry_idx}".format(**fmtparams)
        res = wikipage.insertAtRegex(subentry_xhtml, regex_pat, versionComment=versionComment, updateFromServer=updateFromServer, persistToServer=persistToServer)

        return res



    def makeSubentryProps(self, subentry_idx=None, props=None):
        """
        Returns all subentry properties required to format stings.
        This is essentially just the props from the 'exp_subentries' item in
        the experiments metadata (.labfluence.yml file), but with
        extra info such as experiment id, foldername, etc.
        """
        return self.Experiment.makeFormattingParams(subentry_idx, props)



    def getConfigEntry(self, cfgkey, default=None):
        """
        Relay to self.Experiment.getConfigEntry(cfgkey),
        which again relays to confighandler's with the right path argument.
        """
        return self.Experiment.getConfigEntry(cfgkey, default)





if __name__ == '__main__':

    pass
