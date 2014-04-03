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
# pylint: disable=C0103,W0212

import pytest
import os
import yaml
import logging
logger = logging.getLogger(__name__)

### SUT: ###
from directorymockstructure import DirectoryMockstructure


testdatadir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'test_data')

testconfig = yaml.load(r"""
exp_folder_regexs:
  experiment: (?P<expid>RS[0-9]{3})[_ ]+(?P<exp_titledesc>.+)
  subentry: (?P<expid>RS[0-9]{3})-?(?P<subentry_idx>[^_])[_ ]+(?P<subentry_titledesc>.+?)\s*(\((?P<date>[0-9]{8})\))?$
  expidx_from_expid: RS(?P<exp_series_index>[0-9]{3,4})
satellite_locations:
  CDNA AFM:
    uri: /home/scholer/Documents/labfluence_satellite_tests/cdnaafm_cftp
    folderscheme: ./subentry/
    protocol: file
    rootdir: .
  Typhoon:
    protocol: file
    uri: /home/scholer/Documents/labfluence_satellite_tests/typhoon_cftp
    folderscheme: ./subentry/
    mountcommand: curlftpfs ftp://user:password@10.17.75.109 /mnt/typhoon_ftp
    rootdir: .
""")

locations1 = testconfig['satellite_locations']


listofpaths = """
2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410
2014_Aarhus/RS190 NC folded TR Box HCav6V with RNA pur DLS and AGE
2014_Aarhus/RS191 HCav annealing screen1
2014_Aarhus/RS192 Biotin-FRET Box for MJ sm-FRET
2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189a Pipetting TR SS MBL staples for MV (20140109)
2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189b Pipetting TR ss-col410-bg staples with Anders (20140108)
2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189c Pipetting TR.SS cols with new IDT_Jan14 staples (20140115)
2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189c Pipetting TR.SS cols with new IDT_Jan14 staples (20140115)/epmotion-cmd-templates.yml
2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189c Pipetting TR.SS cols with new IDT_Jan14 staples (20140115)/TR.SS.i-4T.colormap
2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189c Pipetting TR.SS cols with new IDT_Jan14 staples (20140115)/TR.SS.i-4T.csv.smmc.sorted
2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189c Pipetting TR.SS cols with new IDT_Jan14 staples (20140115)/TR.SS.i-4T.modulestopipet
""".split('\n')


def test_loadFromFlatListOfPaths():
    ds = DirectoryMockstructure()
    ds.loadFromFlatListOfPaths(listofpaths)
    assert set(ds._directorydictstructure.keys()) == set(['2014_Aarhus'])
    assert set(ds._directorydictstructure['2014_Aarhus'].keys()) == set(filter(None, """
RS189 Pipetting TR SS staples for MBL and col410
RS190 NC folded TR Box HCav6V with RNA pur DLS and AGE
RS191 HCav annealing screen1
RS192 Biotin-FRET Box for MJ sm-FRET""".split('\n')))


def test_loadFromFlatFile():
    print "testdatadir: ", testdatadir
    fp = os.path.join(testdatadir, 'test_filestructure', 'windirstructure.txt')
    assert os.path.isfile(fp)
    ds = DirectoryMockstructure()
    ds.loadFromFlatFile(fp)
    assert set(ds._directorydictstructure.keys()) == set(['2014_Aarhus'])
    assert set(ds._directorydictstructure['2014_Aarhus'].keys()).issuperset(set(filter(None, """
RS189 Pipetting TR SS staples for MBL and col410
RS190 NC folded TR Box HCav6V with RNA pur DLS and AGE
RS191 HCav annealing screen1
RS192 Biotin-FRET Box for MJ sm-FRET""".split('\n'))))


def test_getdirdictnodes_simple():
    ds = DirectoryMockstructure()
    ds.loadFromFlatListOfPaths(listofpaths)
    currentpath = '2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189c Pipetting TR.SS cols with new IDT_Jan14 staples (20140115)'
    dictnodes, nodenames = ds.getdirdictnodes(currentpath)
    assert nodenames == ['<root>'] + currentpath.split('/')
    assert len(dictnodes) == 4
    assert nodenames[-1] in dictnodes[-2]
    for i in range(3):
        assert nodenames[i+1] in dictnodes[i]



def test_rename():
    ds = DirectoryMockstructure()
    ds.loadFromFlatListOfPaths(listofpaths)
    currentpath = '2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189c Pipetting TR.SS cols with new IDT_Jan14 staples (20140115)'
    newfoldername = 'RS189c Pipetting TR.SS cols NEW NEW'
    expectedfolderpath = '2014_Aarhus/RS189 Pipetting TR SS staples for MBL and col410/RS189c Pipetting TR.SS cols NEW NEW'
    ds.rename(currentpath, newfoldername)
    # Assert that this gives an error:
    with pytest.raises(ValueError):
        dictnodes, nodenames = ds.getdirdictnodes(currentpath)
    dictnodes, nodenames = ds.getdirdictnodes(expectedfolderpath)
    assert nodenames == ['<root>'] + expectedfolderpath.split('/')
    assert len(dictnodes) == 4
    assert nodenames[-1] in dictnodes[-2]
    for i in range(3):
        assert nodenames[i+1] in dictnodes[i]
