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
# pylint: disable-msg=W0621,C0111
"""
Testing journalassistant module/class.
"""

import pytest
import os
import tempfile
import logging
logger = logging.getLogger(__name__)



from model.experiment import Experiment

## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler
from model.model_testdoubles.fake_server import FakeConfluenceServer



## classical xunit setup in pytest: http://pytest.org/latest/xunit_setup.html
## Alternatively, consider using fixtures: http://pytest.org/latest/fixture.html
# module-level setup:
#def setup_module(module):
#    """ setup any state specific to the execution of the given module."""
#    ldir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
#    ch = FakeConfighandler(pathscheme='test1')
#    rootdir = ch.get("local_exp_subDir")
#    server = FakeConfluenceServer(confighandler=ch, autologin=True)
#
## per-function setup:
#def setup_function(function):
#    e = Experiment(confighandler=ch, server=server, localdir=ldir)
#    e.attachWikiPage(dosearch=True)
#    ja = e.JournalAssistant
#    ja.Current_subentry_idx = 'c'


## I think using fixtures is a bit cleaner, for every test, you specify the name of
## a fixture as a required argument. pytest will do the code inspection and see what needs to be filled in,
## searching for functions marked with @pytest.fixture

debug_modules = ('model.journalassistant', 'model.experiment')
logger_states = dict()


# Note: Switched to using pytest-capturelog, captures logging messages automatically...
#def setup_module(module):
#    """ setup any state specific to the execution of the given module."""
#    logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s(): %(message)s\n"
#    logging.basicConfig(level=logging.INFO, format=logfmt)
#    logging.getLogger(__name__).setLevel(logging.DEBUG)
#    logging.getLogger("__main__").setLevel(logging.DEBUG)
#    for module in debug_modules:
#        logger_states[module] = logging.getLogger(module).level
#        logging.getLogger(module).setLevel(logging.DEBUG)
#
#def teardown_module(module):
#    """
#    teardown any state that was previously setup with a setup_module method.
#    """
#    for module in debug_modules:
#        #logger_states[module] = logging.getLogger(module).level
#        logging.getLogger(module).setLevel(logger_states[module])



@pytest.fixture
def tempfiledir():
    newpath = tempfile.mkdtemp() # Returns path to new temp directory, e.g. /tmp/tmpQ938Rj
    return newpath


##############################################################
### JournalAssistant with complete, intact object network ####
###  ordered to use a tempdir as working directory.       ####
##############################################################

@pytest.fixture
def fakeconfighandler(monkeypatch, tempfiledir):
    ch = FakeConfighandler(pathscheme='test1')
    #testdir = os.path.join(os.getcwd(), 'tests', 'test_data', 'test_filestructure', 'labfluence_data_testsetup')
    testdir = os.path.join(tempfiledir, '2013_exp_subdir_test')
    monkeypatch.setattr(ch, 'getConfigDir', lambda x: testdir)
    ch.setkey('local_exp_subDir', testdir)
    ch.setkey('local_exp_rootDir', os.path.dirname(testdir))
    return ch

@pytest.fixture
def experiment_with_ch(fakeconfighandler):
    ch = fakeconfighandler
    subdir = ch.getAbsExpPath('local_exp_subDir')
    foldername = 'RS001 Pytest test experiment'
    localdir = os.path.join(subdir, foldername)
    if not os.path.isdir(localdir):
        logger.info("Creating dir (os.makedirs): %s", localdir)
        os.makedirs(localdir)
    e = Experiment(confighandler=ch, localdir=localdir)
    return e

@pytest.fixture
def ja_for_exp_with_subentry(experiment_with_ch):
    e = experiment_with_ch
    e.addNewSubentry(subentry_titledesc="First subentry in this experiment", makefolder=True)
    return e.JournalAssistant


################################################################
###   JournalAssistant with a mocked object network          ###
### should be faster to initialize and more "unittest" like  ###
################################################################

@pytest.fixture
def ja_mocked(monkeypatch, experiment_with_ch):
    """
    A JournalAssistant where, instead of creating a tempdir,
    all non-SUT methods are simply mocked.
    """
    e = experiment_with_ch
    e.addNewSubentry(subentry_titledesc="First subentry in this experiment", makefolder=False)
    ja = e.JournalAssistant
    ja.__mock_writetofile_cache = dict()
    def mock_writetofile(path, entry_text):
        cache = ja.__mock_writetofile_cache.setdefault(path, "")
        ja.__mock_writetofile_cache[path] = cache + u"\n"+entry_text
        logger.debug("ja.__mock_writetofile_cache.keys(): %s", ja.__mock_writetofile_cache.keys())
        return True
    monkeypatch.setattr(ja, '_writetofile', mock_writetofile)
    def mock_readfromfile(path):
        cache = ja.__mock_writetofile_cache.get(path)
        if cache is None:
            logger.info("mock_readfromfile, path not found in cache; cache is: %s", ja.__mock_writetofile_cache)
        else:
            logger.debug("mock_readfromfile returning cache '%s' for path %s", cache, path)
        return cache
    monkeypatch.setattr(ja, '_readfromfile', mock_readfromfile)
    return ja


#@pytest.mark.skipif(True, reason="Not ready yet")
def test_addEntry_with_mock(ja_mocked):
    ja = ja_mocked
    str1 = "Buffer: 10/100 mM HEPES/KCl pH with 0.5 mM biotin."
    ja.addEntry(str1)
    ja.addEntry("Adding 100 ul buffer to RS102b and running through amicon 3k filter")


#@pytest.mark.skipif(True, reason="Not ready yet")
def test_getCacheContent(monkeypatch, ja_mocked):
    ja = ja_mocked
    str1 = "Buffer: 10/100 mM HEPES/KCl pH with 0.5 mM biotin."
    ja.addEntry(str1)
    cache = ja.getCacheContent()
    assert len(cache) > len(str1)


@pytest.mark.skipif(True, reason="Not ready yet")
def test_addEntry_with_tempdir(ja_for_exp_with_subentry):
    ja = ja_mocked
    str1 = "Buffer: 10/100 mM HEPES/KCl pH with 0.5 mM biotin."
    ja.addEntry(str1)
    ja.addEntry("Adding 100 ul buffer to RS102b and running through amicon 3k filter")


@pytest.mark.skipif(True, reason="Not ready yet")
def test_flush(monkeypatch, ja_for_exp_with_subentry):
    """
    It would be very nice if flush() was made more testable, e.g. by refactoring
    the file-handling stuff to independent, encapsulated/mockable methods.
    Of course, this also makes flush() it self a bit more fragile...
    """
    ja = ja_for_exp_with_subentry
    def insertJournalContentOnWikiPage_mock(self, journal_content, subentryprops):
        res = "<the page's updated xhtml>"
        new_xhtml = "<p>"+"<br/>".join(line.strip() for line in journal_content.split('\n') if line.strip())+"</p>"
        return res, new_xhtml
    monkeypatch.setattr(ja, 'insertJournalContentOnWikiPage', insertJournalContentOnWikiPage_mock)
    str1 = "Buffer: 10/100 mM HEPES/KCl pH with 0.5 mM biotin."
    ja.addEntry(str1)
    ja.flush()
