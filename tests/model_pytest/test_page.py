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


import pytest
from datetime import datetime
import random
import string
import logging
logger = logging.getLogger(__name__)
# Note: Switched to using pytest-capturelog, captures logging messages automatically...



from model.page import WikiPageFactory

## Test doubles:
from model.model_testdoubles.fake_confighandler import FakeConfighandler as ExpConfigHandler
from model.model_testdoubles.fake_server import FakeConfluenceServer as ConfluenceXmlRpcServer


run_random_string = "".join(random.sample(string.ascii_letters, 5))


@pytest.mark.skipif(True, reason="Not ready yet")
def test_factoryNew():
    ch = ExpConfigHandler(pathscheme='test1')
    wikiserver = ConfluenceXmlRpcServer(confighandler=ch, autologin=True)
    factory = WikiPageFactory(wikiserver, ch)
    expid_index = 1
    expid = ch.get('expid_fmt').format(exp_series_index=expid_index)
    current_datetime = datetime.now()
    fmt_params = dict(expid=expid,
                      exp_titledesc="First test page"+run_random_string,
                      datetime=current_datetime,
                      date=current_datetime)
    newpage = factory.new('exp_page', fmt_params=fmt_params)
