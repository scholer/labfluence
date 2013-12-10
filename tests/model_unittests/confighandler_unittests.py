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

import unittest
import os
import logging
logger = logging.getLogger(__name__)

# As long as you run the test from the main ./labfluence/ directory, it should be able to
# know how to find the model package in ./labfluence/model/
# i.e. do not use relative imports, they dont really work anyways, just run from far away.
from model.confighandler import ExpConfigHandler, PathFinder



class PathFinder_Tests1(unittest.TestCase):

    def setUp():
        self.Confighandler = ch = ExpConfigHandler( pathscheme='test1' )
        self.Pathfinder = pf = PathFinder(VERBOSE=10)


    def testPfAndChain():
        #ch3 = ExpConfigHandler( pathscheme='default1' )
        ch3 = self.Confighandler #ExpConfigHandler( pathscheme='test1' )
        ch3.printConfigs()
        logger.info("\nch3.HierarchicalConfigHandler.Configs:\n{}".format( ch3.HierarchicalConfigHandler.printConfigs() ))
        return ch3

    def testPathFinder1():
        pf = PathFinder(VERBOSE=10)



class Confighandler_Tests1(unittest.TestCase):

    def setUp():
        self.Confighandler = ch = ExpConfigHandler( pathscheme='test1' )

class Confighandler_OldTests1(unittest.TestCase):


    def setUp():
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        configtestdir = os.path.join(scriptdir, '../test/config')
        paths = [ os.path.join(configtestdir, cfg) for cfg in ('system_config.yml', 'user_config.yml', 'exp_config.yml') ]
        self.Confighandler = ch = ExpConfigHandler(*paths)
        logger.info("\nEnd ch confighandler init...\n\n" )
        def printPaths():
            logger.info("os.path.curdir:            {}".format(os.path.curdir) )
            logger.info("os.path.realpath(curdir) : {}".format(os.path.realpath(os.path.curdir)) )
            logger.info("os.path.abspath(__file__): {}".format(os.path.abspath(__file__)) )
            #print "os.path.curdir: {}".format(os.path.curdir)
        printPaths()
        return ch

    def test_makedata(ch=None):
        if ch is None:
            ch = self.Confighandler
        logger.info('ch.Configs:\n{}'.format(ch.Configs))
        ch.Configs['system']['install_version_str'] = '0.01'
        ch.Configs['user']['username'] = 'scholer'
        ch.Configs['user']['exp_config_path'] = os.path.join(os.path.expanduser("~"), 'Documents', 'labfluence_data_testsetup', '.labfluence.yml')
        usr = ch.setdefault('wiki_username', 'scholer')
        logger.info("Default user: {}".format(usr) )
        ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
        logger.info("ch.get('wiki_username') --> {}".format(ch.get('wiki_username')) )
        logger.info("Config, combined:" )
        logger.info(ch.getConfig(what='combined') )
        return ch

    def test_configTypeChain():
        #ch2 = ExpConfigHandler('../test/config/system_config.yml')
        ch2 = self.Confighandler
        logger.info('ch2.Configs:\n{}'.format(ch2.Configs) )
        ch2.Configs
        ch2.Configs['system']['user_config_path'] = os.path.join(configtestdir, 'user_config.yml')
        ch2.saveConfigs()
        ch3 = ExpConfigHandler('../test/config/system_config.yml')
        logger.info('ch3.Configs:\n{}'.format( ch3.Configs ))


    def test_save1():
        #ch = test_makedata()
        ch = self.Confighandler
        ch.saveConfigs()

    def test_readdata():
        ch.autoReader()
        for cfg in ('system', 'user', 'exp'):
            logger.info("{} config: \n{}".format(cfg, ch.Configs[cfg]))
