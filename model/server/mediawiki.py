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


from __future__ import print_function, division

import json

## MODELS ##
from abstract_clients import AbstractClient



def load_json_config(path):
    with open(path) as fd:
        fileconfig = json.load(fd)
    return fileconfig

def get_json_configs(config_paths):
    config = {}
    if isinstance(config_paths, basestring):
        config_paths = (config_paths, )
    for path in config_paths:
        fileconfig = load_json_config(path)
        config.update(fileconfig)
    return config


def get_mediawiker_siteparams(mediawiker_config_paths):

    config = get_json_configs(mediawiker_config_paths)
    siteparams = {}
    site_name_active = config['mediawiki_site_active']
    #site_list = config('mediawiki_site')
    siteparams = config['mediawiki_site'][site_name_active]
    # siteparams['domain'] is for auth
    if siteparams.get("https"):
        siteparams['scheme'] = 'https'
    return siteparams



class MediawikiClient(AbstractClient):
    """
    Mediawiki client that uses the mwclient library to interact with
    mediawiki's api.php interface.

    The AbstractClient class implements a lot of generic Properties.
    """

    def __init__(self, serverparams=None, username=None, password=None, logintoken=None,
                 url=None, confighandler=None, autologin=None):

        AbstractClient.__init__(self, serverparams, username, password, logintoken, url, confighandler, autologin)
        # Default server parameters:
        self._defaultparams = {'hostname': 'localhost', 'scheme': 'https', 'path': '/w/api.php'}
        self._serverparams = serverparams or {}


    def loadMediawikerServerparams(self, mediawiker_config_paths=None):
        """
        Load server params from Mediawiker config. Because having one is easier than
        keeping several configs updated.
        """
        if mediawiker_config_paths is None:
            mediawiker_config_paths = self.Confighandler.get('mediawiker_config_paths')
        mediawiker_params = get_mediawiker_siteparams(mediawiker_config_paths)
        self._serverparams.update(mediawiker_params)

