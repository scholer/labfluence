#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2013 Rasmus Scholer Sorensen, rasmusscholer@gmail.com

"""
This script is provides a basic environment for working with the labfluence models
in an interactive mannor:
* Sets up basic logging

If you want a full-featured model setup, you can invoke:
ch = Confighandler()
server = Server(confighandler=ch)
ch.Singletons['server'] = server

If you just want to init a simple server, use:
server = SimpleConfluenceXmlRpcServer('https://wiki.cdna.au.dk/rpc/xmlrpc')

"""

print "Setting up for interactive environment..."

import logging
logger = logging.getLogger(__name__)
logfmt = "%(levelname)-5s %(name)20s:%(lineno)-4s%(funcName)20s() %(message)s"
logfilefmt = '%(asctime)s %(levelname)-6s - %(name)s:%(lineno)s - %(funcName)s() - %(message)s'
logdatefmt = "%Y%m%d-%H:%M:%S"
logging.basicConfig(format=logfmt, datefmt=logdatefmt, level=logging.DEBUG)

from confighandler import ExpConfigHandler
Confighandler = ExpConfigHandler
from server import ConfluenceXmlRpcServer
Server = ConfluenceXmlRpcServer
from simpleserver import SimpleConfluenceXmlRpcServer
SimpleServer = SimpleConfluenceXmlRpcServer
from experimentmanager import ExperimentManager

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print "Interactive environment loaded!"
