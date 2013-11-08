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

#import unittest
#from .. import model
import os
if __name__ == '__main__' and __package__ is None:
    os.sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ... import model
from model.experiment import Experiment
from model.confighandler import ExpConfigHandler
from model.experiment_manager import ExperimentManager
from model.server import ConfluenceXmlRpcServer

#from model import experiment, confighandler, experiment_manager, server


class TestExperiment1(object):

    def setUp(self):
        self.seq = range(10)
        #self.Confighandler = confighandler = ExpConfigHandler( pathscheme='default1', VERBOSE=1 )
        rootdir = confighandler.get("local_exp_subDir")
        print "rootdir: {}".format(rootdir)
        print "glob res: {}".format(glob.glob(os.path.join(rootdir, r'RS102*')) )
        #self.Server = server = ConfluenceXmlRpcServer(confighandler=confighandler, VERBOSE=4, autologin=True) if useserver else None
        #self.Experiment = e = Experiment(confighandler=confighandler, server=server, localdir=ldir, VERBOSE=10)


    def test_shuffle(self):
        # make sure the shuffled sequence does not lose any elements
        random.shuffle(self.seq)
        self.seq.sort()
        self.assertEqual(self.seq, range(10))

        # should raise an exception for an immutable sequence
        self.assertRaises(TypeError, random.shuffle, (1,2,3))

    def test_choice(self):
        element = random.choice(self.seq)
        self.assertTrue(element in self.seq)

    def test_sample(self):
        with self.assertRaises(ValueError):
            random.sample(self.seq, 20)
        for element in random.sample(self.seq, 5):
            self.assertTrue(element in self.seq)

    def test_attachWikiPage(self):
        return
        e = self.Experiment
        if not e:
            e = setup1()
        if e.WikiPage:
            print "\nPage already attached: {}".format(e.WikiPage)
        else:
            e.attachWikiPage(dosearch=True)
            print "\nPage attached: {}".format(e.WikiPage)
        return e




if __name__ == '__main__':
    #unittest.main()
    testcase = TestExperiment1()
