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
# pylint: disable-msg=W0621,C0111
"""
Testing limspage/LimsPage module/class.
"""

import pytest
import logging
logger = logging.getLogger(__name__)

#################################
###### System Under Test ########
#################################

from model.limspage import WikiLimsPage

############################
###### Test doubles ########
############################
from model.model_testdoubles.fake_server import FakeConfluenceServer
from model.model_testdoubles.fake_confighandler import FakeConfighandler


@pytest.fixture
def xhtml_teststring():
    xhtml = """
<p>This page is used to keep track of things that we have bought (inventory management). For information on&nbsp;<em>how</em> to purchase items for the JK lab, please refer to&nbsp;<ac:link><ri:page ri:content-title="Orders and Purchases how-to" /></ac:link>.</p>
<p>Here we can keep a list of all the things we have purchased, so as to make it easier for all people in the lab to see what reagents we have in the lab.</p>
<table><tbody>
<tr>
<th><p>Date (yyyymmdd)</p></th>
<th><p>Compound name</p></th>
<th><p>Amount</p></th>
<th><p>Price (dkk)</p></th>
<th><p>Ordered by</p></th>
<th><p>Manufacturer / distributor</p></th>
<th><p>Comments</p></th>
</tr>
<tr><td><p>20110911</p></td><td><p>Quartz cuvette, Hellma QS105.201</p></td><td><p>1 stk</p></td><td><p>1400</p></td><td><p>scholer</p></td><td><p>Hellma / VWR</p></td><td><p>Arrived. For 100 ul. 10 mm LP.</p></td></tr>
<tr><td><p>20110920</p></td><td><p>N-Methyl-2-Pyrrolidinone (NMP)</p></td><td><p>1 L</p></td><td><p>&nbsp;</p></td><td><p>scholer</p></td><td><p>Sigma</p></td><td><p>Arrived and opened. Anhydrous, using sure-seal.</p></td></tr><tr><td><p>20110920</p></td><td><p>Dimethylacetamide (DMA)</p></td><td><p>1 L</p></td><td><p>191</p></td><td><p>scholer</p></td><td><p>BDH Prolabo / VWR</p></td><td><p>&nbsp;</p></td></tr><tr><td><p>20110919</p></td><td><p>1-Propanol</p></td><td><p>1 L</p></td><td><p>&nbsp;</p></td><td><p>scholer</p></td><td><p>BDH Prolabo / VWR</p></td><td><p>Arrived and opened</p></td></tr><tr><td><p>20111012</p></td><td><p>Brown &quot;crimp cap&quot; injection vials for HPLC</p></td><td><p>1000 pcs</p></td><td><p>1033</p></td><td><p>scholer</p></td><td><p>VWR</p></td><td><p>0.3 ml micro vial, PP, amber, snap ring, 32 x 11.6 mm<br class="atl-forced-newline" /> cat.no. 548-0454</p></td></tr><tr><td colspan="1">20121029</td><td colspan="1">EL-USB-TC-LCD</td><td colspan="1">1 stk</td><td colspan="1">750</td><td colspan="1">scholer</td><td colspan="1">Lascar / Microtec</td><td colspan="1">Temperature data logger</td></tr>
</tbody></table>
"""
    return xhtml

@pytest.fixture
def table_teststring():
    xhtml = """
<table><tbody>
<tr>
<th><p>Date (yyyymmdd)</p></th>
<th><p>Compound name</p></th>
<th><p>Amount</p></th>
<th><p>Price (dkk)</p></th>
<th><p>Ordered by</p></th>
<th><p>Manufacturer / distributor</p></th>
<th><p>Comments</p></th>
</tr>
<tr><td><p>20110911</p></td><td><p>Quartz cuvette, Hellma QS105.201</p></td><td><p>1 stk</p></td><td><p>1400</p></td><td><p>scholer</p></td><td><p>Hellma / VWR</p></td><td><p>Arrived. For 100 ul. 10 mm LP.</p></td></tr>
<tr><td><p>20110920</p></td><td><p>N-Methyl-2-Pyrrolidinone (NMP)</p></td><td><p>1 L</p></td><td><p>&nbsp;</p></td><td><p>scholer</p></td><td><p>Sigma</p></td><td><p>Arrived and opened. Anhydrous, using sure-seal.</p></td></tr><tr><td><p>20110920</p></td><td><p>Dimethylacetamide (DMA)</p></td><td><p>1 L</p></td><td><p>191</p></td><td><p>scholer</p></td><td><p>BDH Prolabo / VWR</p></td><td><p>&nbsp;</p></td></tr><tr><td><p>20110919</p></td><td><p>1-Propanol</p></td><td><p>1 L</p></td><td><p>&nbsp;</p></td><td><p>scholer</p></td><td><p>BDH Prolabo / VWR</p></td><td><p>Arrived and opened</p></td></tr><tr><td><p>20111012</p></td><td><p>Brown &quot;crimp cap&quot; injection vials for HPLC</p></td><td><p>1000 pcs</p></td><td><p>1033</p></td><td><p>scholer</p></td><td><p>VWR</p></td><td><p>0.3 ml micro vial, PP, amber, snap ring, 32 x 11.6 mm<br class="atl-forced-newline" /> cat.no. 548-0454</p></td></tr><tr><td colspan="1">20121029</td><td colspan="1">EL-USB-TC-LCD</td><td colspan="1">1 stk</td><td colspan="1">750</td><td colspan="1">scholer</td><td colspan="1">Lascar / Microtec</td><td colspan="1">Temperature data logger</td></tr>
</tbody></table>
"""
    headers = ['Date (yyyymmdd)', 'Compound name', 'Amount', 'Price (dkk)', 'Ordered by', 'Manufacturer / distributor', 'Comments']
    return xhtml

@pytest.fixture
def tablerow_teststring():
    xhtml = ("""
<tr>
<th><p>Date (yyyymmdd)</p></th>
<th><p>Compound name</p></th>
<th><p>Amount</p></th>
</tr>
""","""
<tr><td><p>20110911</p></td><td><p>scholer</p></td><td><p>Hellma / VWR</p></td></tr>
""")
    data = (['Date (yyyymmdd)', 'Compound name', 'Amount'],
            ['20110911', 'scholer', 'Hellma / VWR'])
    return zip(xhtml, data)

@pytest.fixture
def tablerowdata_teststring():
    xhtml = ("""
<th><p>Date (yyyymmdd)</p></th>
""","""
<tr><td><p>20110911</p></td><td></tr>
""")
    data = (['Date (yyyymmdd)', ], ['20110911', ])
    return zip(xhtml, data)

@pytest.fixture
def fakeconfighandler():
    return FakeConfighandler()


@pytest.fixture
def fakeserver(fakeconfighandler):
    return FakeConfluenceServer(fakeconfighandler)


@pytest.fixture
def limspage_withserver(monkeypatch, fakeserver):
    limspage = WikiLimsPage('917542', server=fakeserver)#, confighandler=fakeserver.Confighandler)
    return limspage


@pytest.fixture
def limspage_nodeps(monkeypatch, xhtml_teststring):
    # Mock the page and limspage classes so much that you no longer
    # need a server or confighandler.
    # init signature is: def __init__(self, pageId, server=None, confighandler=None, pagestruct=None)
    def mock_updatepage(*args, **kwargs):
        logging.debug("mock_updatepage called with args and kwargs: %s; %s", args, kwargs)
    def mock_reloadfromserver(*args, **kwargs):
        logging.debug("mock_reloadfromserver called with args and kwargs: %s; %s", args, kwargs)
    def mock_content(*args, **kwargs):
        logging.debug("mock_reloadfromserver called with args and kwargs: %s; %s", args, kwargs)
        return xhtml_teststring

    monkeypatch.setattr(WikiLimsPage, 'reloadFromServer', mock_reloadfromserver)
    #monkeypatch.setattr(WikiLimsPage, 'Content', mock_content) # now Content is function handle.
    monkeypatch.setattr(WikiLimsPage, 'Content', mock_content()) #
    limspage = WikiLimsPage('111')
    monkeypatch.setattr(limspage, '_confighandler', dict() )
    #monkeypatch.setattr(limspage, 'Content', mock_content) # does not work.
    #monkeypatch.setattr(limspage, 'Content', 'test') # does not work.
    #monkeypatch.setattr('limspage.Content', mock_content) # does not work here...
    logger.debug("limspage.Content is: %s", limspage.Content)
    monkeypatch.setattr(limspage, 'updatePage', mock_updatepage)
    return limspage

def test_findCellsInTablerow(limspage_nodeps, tablerowdata_teststring, tablerow_teststring):
    page = limspage_nodeps
    for xhtml, data in tablerowdata_teststring:
        logger.info("xhtml is: %s", xhtml)
        logger.info("data is: %s", data)
        assert data == page.findCellsInTablerow(xhtml)
    for xhtml, data in tablerow_teststring:
        assert data == page.findCellsInTablerow(xhtml)


def test_getTableHeaders(limspage_nodeps, table_teststring):
    page = limspage_nodeps
    headers = ['Date (yyyymmdd)', 'Compound name', 'Amount', 'Price (dkk)', 'Ordered by', 'Manufacturer / distributor', 'Comments']
    assert headers == page.getTableHeaders(xhtml=table_teststring)
    #page.getTableHeaders()


def test_getTableHeaders_withserver(limspage_withserver, table_teststring):
    page = limspage_withserver
    headers = ['Date (yyyymmdd)', 'Compound name', 'Amount', 'Price (dkk)', 'Ordered by', 'Manufacturer / distributor', 'Comments']
    assert headers == page.getTableHeaders(xhtml=table_teststring)


#@pytest.mark.skipif(True, reason="Temporary disabled.")
def test_addEntry_withserver(limspage_withserver, xhtml_teststring):
    page = limspage_withserver
    headers = ['Date (yyyymmdd)', 'Compound name', 'Amount', 'Price (dkk)', 'Ordered by', 'Manufacturer / distributor', 'Comments']
    values  = ['20131224', 'Christmas present', '1 pcs', '1000', 'Mommy', 'Santa', 'Red is preferred']
    entry_dict = dict( zip(headers, values) )
    new_xhtml = page.addEntry(entry_dict)
    assert new_xhtml in page.Content
    for item in headers+values:
        assert item in new_xhtml



#@pytest.mark.skipif(True, reason="Temporary disabled.")
def test_addEntry(limspage_nodeps, xhtml_teststring):
    page = limspage_nodeps
    expected_xhtml = """
<p>This page is used to keep track of things that we have bought (inventory management). For information on&nbsp;<em>how</em> to purchase items for the JK lab, please refer to&nbsp;<ac:link><ri:page ri:content-title="Orders and Purchases how-to" /></ac:link>.</p>
<p>Here we can keep a list of all the things we have purchased, so as to make it easier for all people in the lab to see what reagents we have in the lab.</p>
<table><tbody>
<tr>
<th><p>Date (yyyymmdd)</p></th>
<th><p>Compound name</p></th>
<th><p>Amount</p></th>
<th><p>Price (dkk)</p></th>
<th><p>Ordered by</p></th>
<th><p>Manufacturer / distributor</p></th>
<th><p>Comments</p></th>
</tr><tr><td><p>20131224</p></td><td><p>Christmas present</p></td><td><p>1 pcs</p></td><td><p>1000</p></td><td><p>Mommy</p></td><td><p>Santa</p></td><td><p>Red is preferred</p></td></tr>
<tr><td><p>20110911</p></td><td><p>Quartz cuvette, Hellma QS105.201</p></td><td><p>1 stk</p></td><td><p>1400</p></td><td><p>scholer</p></td><td><p>Hellma / VWR</p></td><td><p>Arrived. For 100 ul. 10 mm LP.</p></td></tr>
<tr><td><p>20110920</p></td><td><p>N-Methyl-2-Pyrrolidinone (NMP)</p></td><td><p>1 L</p></td><td><p>&nbsp;</p></td><td><p>scholer</p></td><td><p>Sigma</p></td><td><p>Arrived and opened. Anhydrous, using sure-seal.</p></td></tr><tr><td><p>20110920</p></td><td><p>Dimethylacetamide (DMA)</p></td><td><p>1 L</p></td><td><p>191</p></td><td><p>scholer</p></td><td><p>BDH Prolabo / VWR</p></td><td><p>&nbsp;</p></td></tr><tr><td><p>20110919</p></td><td><p>1-Propanol</p></td><td><p>1 L</p></td><td><p>&nbsp;</p></td><td><p>scholer</p></td><td><p>BDH Prolabo / VWR</p></td><td><p>Arrived and opened</p></td></tr><tr><td><p>20111012</p></td><td><p>Brown &quot;crimp cap&quot; injection vials for HPLC</p></td><td><p>1000 pcs</p></td><td><p>1033</p></td><td><p>scholer</p></td><td><p>VWR</p></td><td><p>0.3 ml micro vial, PP, amber, snap ring, 32 x 11.6 mm<br class="atl-forced-newline" /> cat.no. 548-0454</p></td></tr><tr><td colspan="1">20121029</td><td colspan="1">EL-USB-TC-LCD</td><td colspan="1">1 stk</td><td colspan="1">750</td><td colspan="1">scholer</td><td colspan="1">Lascar / Microtec</td><td colspan="1">Temperature data logger</td></tr>
</tbody></table>
"""
    headers = ['Date (yyyymmdd)', 'Compound name', 'Amount', 'Price (dkk)', 'Ordered by', 'Manufacturer / distributor', 'Comments']
    values  = ['20131224', 'Christmas present', '1 pcs', '1000', 'Mommy', 'Santa', 'Red is preferred']
    entry_dict = dict( zip(headers, values) )
    new_xhtml = page.addEntry(entry_dict)
    print new_xhtml
    assert expected_xhtml == new_xhtml
