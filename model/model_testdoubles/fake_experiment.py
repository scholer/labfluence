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
# pylint: disable-msg=C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221,E1101,W0402,E0202,W0201
# pylint: disable-msg=C0111,W0613,R0903
# messages:

# Special for this (and other) fake modules:
# W0613 unused argument
# C0111 missing method docstring
"""
This module provides a fake confluence server which can be used for testing (and offline access, I guess).

"""

from datetime import datetime

from model.utils import increment_idx


class FakePage(object):
    def __init__(self):
        self.Struct = dict(content="""<h2>Experimental section</h2><p>MPJud29yeOCnTW0x</p>
<h2>Results and discussion</h2><h6>Observations</h6><h6>Discussion</h6><h6>Conclusion</h6><h6>Lessons
learned</h6><h6>Outlook</h6>""", contentStatus='current', created='20130918T17:18:18',
    creator='scholer', current=True, homePage=False, id='524303', modified='20130918T17:30:30',
    modifier='scholer', parentId='524296', permissions='0', space='~scholer', title='exp_multi_template',
    url='http://10.14.40.245:8090/display/~scholer/_exp_multi_template', version='2')



class FakeExperiment(object):
    def __init__(self, props=None, localdir=None, server=None, confighandler=None, **kwargs):
        self.Localdir = localdir
        self.Props = props or dict(expid='RS001', exp_titledesc='Fake experiment fake titledesc',
                                   date=datetime(2013, 12, 24) )
        self.Confighandler = confighandler
        self.Server = server
        self.WikiPage = FakePage()
        self.Subentries = dict()
        self.PageId = '917514'
        self.Status = 'active'

    @property
    def Expid(self):
        """Should always be located one place and one place only: self.Props."""
        return self.Props.get('expid')

    def getAbsPath(self):
        return self.Localdir

    def makeFormattingParams(self, subentry_idx=None, props=None):
        fmt_params = dict(datetime=datetime.now())
        # datetime always refer to datetime.datetime objects; 'date' may refer either to da date string or a datetime.date object.
        # edit: 'date' must always be a string date, formatted using 'journal_date_format'.
        fmt_params.update(self.Props) # do like this to ensure copy and not override, just to make sure...
        if subentry_idx:
            fmt_params['subentry_idx'] = subentry_idx
            fmt_params['next_subentry_idx'] = increment_idx(subentry_idx)
            if self.Subentries and subentry_idx in self.Subentries:
                fmt_params.update(self.Subentries[subentry_idx])
        if props:
            fmt_params.update(props) # doing this after to ensure no override.
        fmt_params['date'] = fmt_params['datetime'].strftime(self.Confighandler.get('journal_date_format', '%Y%m%d'))
        return fmt_params


    def getConfigEntry(self, cfgkey, default=None):
        """
        Fake method.
        """
        if cfgkey in self.Props:
            return self.Props.get(cfgkey)
        elif getattr(self, 'Confighandler', None):
            p = getattr(self, 'Localdirpath', None)
            return self.Confighandler.get(cfgkey, default=default, path=p)
