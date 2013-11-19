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

#from ... import model

#from model.experiment import Experiment
#from model.confighandler import ConfigHandler, PathFinder, ExpConfigHandler
#from model.experiment_manager import ExperimentManager
#from model.server import ConfluenceXmlRpcServer


## Test doubles:
from tests.model_testdoubles.fake_confighandler import FakeConfighandler


import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)
logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():: %(message)s\n"
logging.basicConfig(level=logging.INFO, format=logfmt)
logging.getLogger("__main__").setLevel(logging.DEBUG)
logging.getLogger("tests.model_testdoubles.fake_confighandler").setLevel(logging.DEBUG)
logging.getLogger("model.confighandler").setLevel(logging.DEBUG)



def test_fakeconfighandler_init():
    ch = FakeConfighandler()


def test_fakeconfighandler_get():
    ch = FakeConfighandler()
    assert ch.get('wiki_serverparams')['baseurl'] == "http://10.14.40.245:8090"


def test_fakeconfighandler_setkey_and_get():
    ch = FakeConfighandler()
    #wiki_exp_root_pageId: '524296'
    assert ch.get('wiki_exp_root_pageId') == '524296'
    assert ch.setkey('wiki_exp_root_pageId', '123456') == 'exp'
    assert ch.get('wiki_exp_root_pageId') == '123456'
    # Non-existing key:
    assert ch.get('non_existing_key_10937') == None
    assert ch.setkey('non_existing_key_10937', '124356') == 'user'
    assert ch.get('non_existing_key_10937') == '124356'


def test_fakeconfighandler_setdefault_and_get():
    ch = FakeConfighandler()

    # test for existing key:
    #wiki_exp_root_pageId: '524296'
    assert ch.setdefault('wiki_exp_root_pageId', '123456') == '524296'
    assert ch.get('wiki_exp_root_pageId') == '524296'
    # test with non-existing key:
    assert ch.get('non_existing_key') == None
    assert ch.setdefault('non_existing_key', '123456') == '123456'
    assert ch.get('non_existing_key') == '123456'


def test_fakeconfighandler_popkey():
    ch = FakeConfighandler()
    # test for existing key:
    #wiki_exp_root_pageId: '524296'
    assert ch.get('wiki_exp_root_pageId') == '524296'
    # The popkey output can only be predicted because we have configs in an OrderedDict.
    assert ch.popkey('wiki_exp_root_pageId') == (None, 'system', None, 'user', '524296', 'exp')
    assert ch.popkey('wiki_exp_root_pageId') == (None, 'system', None, 'user', None, 'exp')
    assert ch.get('wiki_exp_root_pageId') == None
    # test with non-existing key:
    assert ch.get('non_existing_key') == None
    assert ch.popkey('non_existing_key') == (None, 'system', None, 'user', None, 'exp')
    assert ch.get('non_existing_key') == None


def test_fakeconfighandler_saveConfigs():
    ch = FakeConfighandler()
    assert ch.saveConfigs() == None


def test_fakeconfighandler_configpaths_and_configs():
    ch = FakeConfighandler()
    assert ch.ConfigPaths['system'] == None
    assert ch.ConfigPaths['user'] == None
    assert ch.ConfigPaths['exp'] == None


def test_singleton_logic():
    ch = FakeConfighandler()
    test_singleton = datetime.now()
    assert ch.setSingleton('mydate', test_singleton) == None
    assert ch.getSingleton('mydate') == test_singleton


def test_registerEntryChangeCallback():
    """
    Confighandler's EntryChange callback system provides two routes by which a callback can be invoked:
    1)  ch.invokeEntryChangeCallback() is invoked with a configentry argument. This will invoke all callbacks
        registrered for that configentry (i.e. all ch.EntryChangeCallbacks).
    2)  As a two-step process, where the configentry is first added to ch.ChangedEntriesForCallbacks (set)
        and then, ch.invokeEntryChangeCallback() is invoked without any arguments, which will then call
        ch.invokeEntryChangeCallback() with all configentry from the ChangedEntriesForCallbacks set.
    """

    class testobject(object):
        def __init__(self):
            self.testvar1 = 0
            self.testvar2 = 0
        def increment(self):
            self.testvar1 += 1
        def addition(self, inc):
            self.testvar2 += inc
        def incrementvar(self, var):
            var += 1


    ch = FakeConfighandler()
    to = testobject()
    ch.registerEntryChangeCallback('testentryA', to.increment)
    ch.registerEntryChangeCallback('testentryB', to.addition, 3)
    assert to.testvar1 == 0
    assert to.testvar2 == 0
    ch.invokeEntryChangeCallback('testentryA')
    assert to.testvar1 == 1
    assert to.testvar2 == 0
    ch.invokeEntryChangeCallback('testentryB')
    assert to.testvar1 == 1
    assert to.testvar2 == 3
    ch.registerEntryChangeCallback('testentryA', to.addition, 10)
    ch.invokeEntryChangeCallback('testentryA')
    assert to.testvar1 == 2
    assert to.testvar2 == 13
    ch.ChangedEntriesForCallbacks.add('testentryA')
    ch.ChangedEntriesForCallbacks.add('testentryB')
    ch.invokeEntryChangeCallback('testentryB')
    assert to.testvar1 == 2
    assert to.testvar2 == 16
    ch.invokeEntryChangeCallback()
    # callbacks for A are invoked, these are to.increment and to.addition(10)
    assert to.testvar1 == 3
    assert to.testvar2 == 26
    ch.ChangedEntriesForCallbacks.add('testentryA')
    ch.ChangedEntriesForCallbacks.add('testentryB')
    ch.invokeEntryChangeCallback()
    # callbacks for both A and B are invoked, these are to.increment and to.addition(10) and to.addition(3)
    assert to.testvar1 == 4
    assert to.testvar2 == 39
    ch.invokeEntryChangeCallback()
    # No callbacks are called, since all elements were cleared from ch.ChangedEntriesForCallbacks
    assert to.testvar1 == 4
    assert to.testvar2 == 39




def test_unregisterEntryChangeCallback():
    """
    Confighandler's EntryChange callback system provides two routes by which a callback can be invoked:
    1)  ch.invokeEntryChangeCallback() is invoked with a configentry argument. This will invoke all callbacks
        registrered for that configentry (i.e. all ch.EntryChangeCallbacks).
    2)  As a two-step process, where the configentry is first added to ch.ChangedEntriesForCallbacks (set)
        and then, ch.invokeEntryChangeCallback() is invoked without any arguments, which will then call
        ch.invokeEntryChangeCallback() with all configentry from the ChangedEntriesForCallbacks set.
    """

    class testobject(object):
        def __init__(self):
            self.testvar1 = 0
            self.testvar2 = 0
        def increment(self):
            self.testvar1 += 1
        def addition(self, inc):
            self.testvar2 += inc
        def incrementvar(self, var):
            var += 1


    ch = FakeConfighandler()
    to = testobject()
    ch.registerEntryChangeCallback('testentryA', to.increment)
    ch.registerEntryChangeCallback('testentryB', to.addition, (3,) )
    ch.registerEntryChangeCallback('testentryA', to.addition, (10,) )
    assert to.testvar1 == 0
    assert to.testvar2 == 0

    ## Also testing unregisterEntryChangeCallback
    ch.invokeEntryChangeCallback('testentryA')
    assert to.testvar1 == 1
    assert to.testvar2 == 10

    ch.unregisterEntryChangeCallback('testentryA', to.increment)
    ch.invokeEntryChangeCallback('testentryA')
    assert to.testvar1 == 1
    assert to.testvar2 == 20

    ch.unregisterEntryChangeCallback(None, to.addition)
    ch.invokeEntryChangeCallback('testentryA')
    ch.invokeEntryChangeCallback('testentryB')
    assert to.testvar1 == 1
    assert to.testvar2 == 20

    ch.registerEntryChangeCallback('testentryA', to.increment)
    ch.registerEntryChangeCallback('testentryA', to.addition, (3,) )
    ch.invokeEntryChangeCallback('testentryA')
    ch.invokeEntryChangeCallback('testentryB')
    assert to.testvar1 == 2
    assert to.testvar2 == 23

    #ch.registerEntryChangeCallback('testentryA', to.increment, (3,) ) # if this is registrered, it will also be unregistrered by the call below:
    ch.unregisterEntryChangeCallback(None, None, (3,) )
    # now only to.increment should be registrered:
    ch.invokeEntryChangeCallback('testentryA')
    assert to.testvar1 == 3
    assert to.testvar2 == 23

    # Registering and removing based on kwargs:
    ch.registerEntryChangeCallback('testentryA', to.increment, None, {'hello': 'there'} )
    ch.unregisterEntryChangeCallback(kwargs={'hello': 'there'})
    # now only to.increment should be registrered:
    ch.invokeEntryChangeCallback('testentryA')
    assert to.testvar1 == 4
    assert to.testvar2 == 23

    # Removing all for a particular configentry:
    ch.registerEntryChangeCallback('testentryB', to.addition, (4,) )
    ch.unregisterEntryChangeCallback('testentryA')
    #  callbacks should be registrered:
    ch.invokeEntryChangeCallback('testentryA')
    assert to.testvar1 == 4
    assert to.testvar2 == 23
    ch.invokeEntryChangeCallback('testentryB')
    assert to.testvar1 == 4
    assert to.testvar2 == 27

    # Removing all
    ch.unregisterEntryChangeCallback()
    # no callbacks should be registrered:
    ch.invokeEntryChangeCallback('testentryA')
    ch.invokeEntryChangeCallback('testentryB')
    assert to.testvar1 == 4
    assert to.testvar2 == 27
