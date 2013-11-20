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
"""
fake_confighandler module, provides Fake Confighandler class, used in test cases.
"""

import yaml
import logging
logger = logging.getLogger(__name__)

from model.confighandler import ExpConfigHandler



class FakeConfighandler(ExpConfigHandler):
    """
    Fake Confighandler class, used in test cases.

    Note that there are quite a lot of things that does not work if e.g.
    the 'exp' ConfigPath is not set.

    """
    def __init__(self, pathscheme, enableHierarchy=False, readfiles=False):
        ExpConfigHandler.__init__(self, pathscheme=None, enableHierarchy=False, readfiles=False)

        expconfigyaml = r"""
exp_series_dir_fmt: '{expid} {exp_titledesc}'
exp_series_regex: (?P<expid>RS[0-9]{3})[_ ]+(?P<exp_titledesc>.+)
exp_subentry_dir_fmt: '{expid}{subentry_idx} {subentry_titledesc} ({datetime:%Y%m%d})'
exp_subentry_regex: (?P<date1>[0-9]{8})?[_ ]*(?P<expid>RS[0-9]{3})-?(?P<subentry_idx>[^_
  ])[_ ]+(?P<subentry_titledesc>.+?)\s*(\((?P<date2>[0-9]{8})\))?$
exp_subentry_regex_old: (?P<date1>[0-9]{8})?[_ ]*(?P<expid>RS[0-9]{3})-?(?P<subentry_idx>[^_ ])[_ ]+(?P<subentry_titledesc>.+?)\s?(\((?P<date2>[0-9]{8})\))?$
exp_subentryid_fmt: '{expid}{subentry_idx}'
expid_fmt: RS{exp_series_index:03d}
expid_regex: RS(?P<exp_series_index>[0-9]{3,4})
journal_entry_fmt: '[{datetime:%Y%m%d %H:%M:%S}] {text}'
journal_subentry_token_fmt_obsolete: '<p id="{}"></p>'
journal_date_format: '%Y%m%d'
local_exp_ignoreDirs:
- equipment_data_sync
- 2008-2010_Aarhus
- 2011_Aarhus
- 2012_Aarhus
- 2012_Harvard
local_exp_rootDir: .
local_exp_subDir: ./2013_Aarhus
wiki_exp_root_spaceKey: ~scholer
wiki_exp_root_pageId: '524296'
wiki_exp_archive_pageId: '524308'
wiki_exp_new_subentry_token: <h2>Results and discussion</h2>
wiki_exp_new_subentry_insert_regex_fmt: (?P<before_insert><h2>Experimental section</h2>.*?)(?P<after_insert><h4>{expid}[_-]?[{next_subentry_idx}-z].*?</h4>|<h[1-3]>.*?</h[1-3]>|$)
wiki_journal_entry_insert_regex_fmt: '(?P<before_insert><h2>Experimental section</h2>.*?<h4>{expid}{subentry_idx}.*?</h4>.*?)(?P<after_insert><h[1-4]>.+?</h[1-4]>|$)'
wiki_subentry_parse_regex_fmt: '(?P<exp_section_header><h2>Experimental section</h2>).*?(?P<subentry_header><h4>{expid}{subentry_idx}.+?</h4>)(?P<subentry_xhtml>.*?)(?P<next_header><h[1-4]>.+?</h[1-4]>|$)'
wiki_templates_pageIds:
  exp_page: '524303'
  exp_subentry: '524306'
wiki_template_string_interpolation_mode: 'old'
wiki_template_string_interpolation_mode_comment: can be 'new', 'old' and 'template'. 'new' is curly-braced based string.format; 'old' is %-based moduli substitution and 'template' uses string templates only.
wiki_allow_template_caching: true
wiki_default_newpage_template: 'exp_page'
"""
        userconfigyaml = """
app_active_experiments:
- RS102
- RS134
- RS135
app_recent_experiments:
- RS103
crypt_iv: Ko8E4tmJP7SCgLla
wiki_serverparams:
  baseurl: http://10.14.40.245:8090
wiki_username: scholer
"""

        configyamls = dict(user=userconfigyaml, exp=expconfigyaml)
        for cfg, yml in configyamls.items():
            newconfig = yaml.load(yml)
            self.Configs.setdefault(cfg, dict()).update(newconfig) # 1-liner, replacing the four below:
            #if cfg in self.Configs:
            #    self.Configs[cfg].update(newconfig)
            #else:
            #    self.Configs[cfg] = newconfig
            logger.debug("Config '%s' loaded.", cfg)
        self.__expconfigs = dict()


    #############################
    ### ConfigHandler methods ###
    #############################

    def autoRead(self):
        pass

    def readConfig(self, **kwargs):
        pass

    def saveConfigForEntry(self, key):
        pass

    def _saveConfig(self, outputfn, config, desc=''):
        pass

    def saveConfigs(self, what='all', VERBOSE=None):
        pass


    ################################
    ### ExpConfigHandler methods ###
    ################################

    def getExpConfig(self, path):
        return self.__expconfigs.setdefault(path, dict())

    def loadExpConfig(self, path):
        pass

    def saveExpConfig(self, path, cfg=None):
        pass

    def updateAndPersist(self, path, props=None, update=False):
        pass

    def renameConfigKey(self, oldpath, newpath):
        pass
