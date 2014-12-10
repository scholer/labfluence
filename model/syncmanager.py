#!/usr/bin/env python3
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
# pylint: disable=C0103,C0301,W0142,R0902,R0904,R0913,R0201,R0912
# pylint: disable=C0103,C0301
# xx C0302,R0902,R0201,W0142,R0913,R0904,W0221,E1101,W0402,E0202,W0201,E0102

"""

Module to synchronize files.

Primarily used to handle one-way sync, pulling new files from satellite locations into the main
experiment data file structure.

                        SyncManager
                       /           \
            SatelliteMgr          ExperimentManager
           /
SatelliteLocation

HOW to implement "one-way sync to pull new files from sat loc to local exp data file structure":
 a) ExpManager parses local experiment directory tree, getting a list of expids.
    SatLoc parses remote tree, getting a list of expids.
    For each local experiment, sync all remote subentry folders into the experiment's local directory.
    This could be handled by the (already large) experimentmanager module, or it could be
    delegated to a separate module, syncmanager.py

Notes:

  * While this can also be used to sync just a single experiment, this intended way to do this
    is by having an experiment request a sync via its personal filemanager.

"""
from __future__ import print_function
from six import string_types
import logging
logger = logging.getLogger(__name__) # http://victorlin.me/posts/2012/08/good-logging-practice-in-python/


class SyncManager(object):
    """
    Handles synchronization between satellite locations and the local experiment data tree.
    """

    def __init__(self, experimentmgr, satellitemgr):
        self.Experimentmanager = experimentmgr
        self.Satellitemanager = satellitemgr



    def oneway_sync(self, remote):
        """
        Initializes a one-way sync from remote into the local experiment data tree.
        """
        exps = self.Experimentmanager.ExperimentsById
        satloc = self.Satellitemanager.get(remote)
        loc_ds = satloc.SubentryfoldersByExpidSubidx
        logger.info("Local experiments: %s", list(exps.keys()))
        logger.info("Satellite experiments: %s", loc_ds.keys())

        # Python 3 dict views support '&', '|' and other set-like operators:
        try:
            common_expids = exps.keys() & loc_ds.keys()
        except TypeError:
            common_expids = exps.viewkeys() & loc_ds.viewkeys() # python 2:
        logger.info("Syncing experiments: %s", common_expids)
        for expid in common_expids:
            exp = exps[expid]
            localdirpath = exp if isinstance(exp, string_types) else exp.Localdirpath
            logger.info("Syncing exp '%s' (%s)", expid, localdirpath)
            for subidx, subfolder in loc_ds[expid].items():
                logger.info("Syncing %s %s : %s -> %s", expid, subidx, subfolder, localdirpath)
                #satloc.syncToLocalDir(subfolder, localdirpath)
        logger.info("'%s' sync complete.", remote)




if __name__ == '__main__':


    logfmt = "%(levelname)-5s %(name)20s:%(lineno)-4s%(funcName)20s() %(message)s"
    #logging.basicConfig(level=logging.DEBUG, format=logfmt)
    logging.basicConfig(level=logging.INFO, format=logfmt)
    logging.getLogger('satellite_location').setLevel(logging.DEBUG)
    logging.getLogger('__main__').setLevel(logging.DEBUG)

    import argparse
    from confighandler import ExpConfigHandler
    from experimentmanager import ExperimentManager
    from satellite_manager import SatelliteManager

    parser = argparse.ArgumentParser("Satellite sync")
    parser.add_argument('remote')
    argns = parser.parse_args()

    ch = ExpConfigHandler()
    em = ExperimentManager(ch)
    sm = SatelliteManager(ch)
    syncmgr = SyncManager(em, sm)

    print("Syncing remote '%s' ..." % argns.remote)
    syncmgr.oneway_sync(argns.remote)
    print("Sync to '%s' complete!" % argns.remote)
