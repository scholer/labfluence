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
# pylint: disable-msg=C0111,W0613


from model.confighandler import ConfigHandler, PathFinder, ExpConfigHandler

import pytest
import os
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

# Note: Switched to using pytest-capturelog, captures logging messages automatically...
#logfmt = "%(levelname)s:%(name)s:%(lineno)s %(funcName)s():: %(message)s\n"
#logging.basicConfig(level=logging.INFO, format=logfmt)
#logging.getLogger("__main__").setLevel(logging.DEBUG)



@pytest.fixture
def confighandler1():
    ch = ExpConfigHandler( pathscheme='test1' )
    return ch


def test_defaultscheme_test1():
    pathscheme = 'test1'
    pf = PathFinder(defaultscheme=pathscheme)
    expectedscheme = dict(sys=os.path.join(*'setup/configs/test_configs/local_test_setup_1/labfluence_sys.yml'.split('/')),
                          user=os.path.join(*'setup/configs/test_configs/local_test_setup_1/labfluence_user.yml'.split('/')))
#    for cfgtype, path in expectedscheme.items():
#        expectedscheme[cfgtype] = os.path.join(os.getcwd(), path)

    assert pf.getScheme(pathscheme) == expectedscheme
    assert pf.getScheme() == expectedscheme


def test_defaultscheme_default1():
    pathscheme = 'test1'
    pf = PathFinder(defaultscheme=pathscheme)
    expectedscheme = dict(sys=os.path.join(*'setup/configs/test_configs/local_test_setup_1/labfluence_sys.yml'.split('/')),
                          user=os.path.join(*'setup/configs/test_configs/local_test_setup_1/labfluence_user.yml'.split('/')))
    #for cfgtype, path in expectedscheme.items():
    #    expectedscheme[cfgtype] = os.path.join(os.getcwd(), path)

    assert pf.getScheme(pathscheme) == expectedscheme
    assert pf.getScheme() == expectedscheme


def test_schemes_test1_default1():

    pf = PathFinder()
    testscheme = dict(  sys= os.path.join(*'setup/configs/test_configs/local_test_setup_1/labfluence_sys.yml'.split('/')),
                        user=os.path.join(*'setup/configs/test_configs/local_test_setup_1/labfluence_user.yml'.split('/')))

    assert pf.getScheme('test1') == testscheme

    defaultscheme = dict(   sys=os.path.join(*'setup/configs/default/labfluence_sys.yml'.split('/')),
                            user=os.path.realpath(os.path.expanduser('~/.Labfluence/labfluence_user.yml')) )

    assert pf.getScheme() == defaultscheme
    assert pf.getScheme('default1') == defaultscheme




def test_addNewConfig():
    ch = ExpConfigHandler( pathscheme='test1' )
    ch.addNewConfig("/home/scholer/Documents/labfluence_data_testsetup/.labfluence/templates.yml", "templates")
    logger.info("ch.get('exp_subentry_template'):" )
    logger.info(ch.get('exp_subentry_template'))

def test_cfgNewConfigDef():
    ch = ExpConfigHandler( pathscheme='test1' )
    #ch.addNewConfig("/home/scholer/Documents/labfluence_data_testsetup/.labfluence/templates.yml", "templates")
    # I have added the following to the 'exp' config:
    # config_define_new:
    #   templates: ./.labfluence/templates.yml
    logger.info("ch.get('exp_subentry_template'):" )
    logger.info(ch.get('exp_subentry_template') )


def notestExpConfig1():
    ch = ExpConfigHandler(pathscheme='test1')
    logger.info("\nch.HierarchicalConfigHandler.Configs:" )
    ch.HierarchicalConfigHandler.printConfigs()
    path = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
    cfg = ch.loadExpConfig(path)
    if cfg is None:
        logger.info("cfg is None; using empty dict.")
        cfg = dict()
    cfg['test_key'] = datetime.now().strftime("%Y%m%d-%H%M%S") # you can use strptime to parse a formatted date string.
    logger.info("\n\nSaving config for path '{}'".format(path) )
    ch.saveExpConfig(path)


def test_registerEntryChangeCallback():
    logger.info("\n\n>>>>>>>>>>>> starting test_registerEntryChangeCallback(): >>>>>>>>>>>>>>>>>>>>" )
    #registerEntryChangeCallback invokeEntryChangeCallback
    ch = ExpConfigHandler(pathscheme='test1')
    ch.setkey('testkey', 'random string')
    def printHej(who, *args):
        logger.info("hi {}, other args: {}".format(who, args) )
    def printNej():
        logger.info("no way!" )
    def argsAndkwargs(arg1, arg2, hej, der, **kwargs):
        logger.info("{}, {}, {}, {}, {}".format(arg1, arg2, hej, der, kwargs) )
    ch.registerEntryChangeCallback('app_active_experiments', printHej, ('morten', ) )
    ch.registerEntryChangeCallback('app_recent_experiments', printNej)
    ch.registerEntryChangeCallback('app_recent_experiments', argsAndkwargs, ('word', 'up'), dict(hej='tjubang', der='sjubang', my='cat') )
    ch.ChangedEntriesForCallbacks.add('app_active_experiments')
    ch.ChangedEntriesForCallbacks.add('app_recent_experiments')

    logger.info("\nRound one:")
    ch.invokeEntryChangeCallback('app_active_experiments')
    ch.invokeEntryChangeCallback() # invokes printNej and argsAndkwargs
    logger.info("\nRound two:")
    ch.invokeEntryChangeCallback('app_active_experiments') # still invokes printHej
    ch.invokeEntryChangeCallback() # does not invoke anything...

    logger.info("\n<<<<<<<<<<<<< completed test_registerEntryChangeCallback(): <<<<<<<<<<<<<<<<<<<<")
