#!/usr/bin/env python
# -*- coding: utf-8 -*-
##    Copyright 2014 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
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
# pylint: disable=C0103,W0212


from __future__ import print_function, division
import os
import sys
#import socket
import argparse
import json

import mwclient

appdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
modeldir = os.path.join(appdir, 'model')
sys.path.append(appdir)

from model.confighandler import ConfigHandler


def get_argparser():
    parser = argparse.ArgumentParser(description="Labfluence file uploader command line tool.")

    parser.add_argument('--printlinks', action='store_true', help="Print a summary with file links when finished.")
    #parser.add_argument('--printlinks', action='store_true')
    parser.add_argument('files', help="Files to upload.")
    return parser


def parse_args(argv=None):
    return get_argparser().parse_args()




def upload_files(files, siteparams=None):

    if config is None:
        config = get_mediawiker_siteparams()

    # Switch to the labfluence AbstractServer class?
    host = (config.get('scheme', 'http'), config['hostname'])
    path = config.get('path')
    clients_useragent = 'Labfluence-Fileuploader'


    # mwclient is a bit weird or overly complicated, separates part of URI as:
    # <scheme>://<hostname><url>,
    # <url> = <path><script><ext>, where <script> is hardcoded to 'api',
    # <path> defaults to /w/, and <ext> defaults to '.php'
    cookies = config.get('cookies')

    connection = mwclient.Site(host, path=path, inject_cookies=cookies, clients_useragent=clients_useragent)




def main(argv=None):
    argns = parse_args(argv)
