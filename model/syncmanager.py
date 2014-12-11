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
#from six import string_types
import logging
logger = logging.getLogger(__name__) # http://victorlin.me/posts/2012/08/good-logging-practice-in-python/


class SyncManager(object):
    """
    Handles synchronization between satellite locations and the local experiment data tree.
    """

    def __init__(self, experimentmgr, satellitemgr):
        self.Experimentmanager = experimentmgr
        self.Satellitemanager = satellitemgr


    def sync_remotes(self, remotes=None, onlyexpids=None, verbosity=None, dryrun=None):
        """
        Syncs all satellite locations with sync_remote.
        """
        if remotes:
            satlocs = {remote: self.Satellitemanager.get(remote) for remote in remotes}
        else:
            satlocs = self.Satellitemanager.getLocationsSorted()
        logger.debug("Syncing all satellite locations: %s", list(satlocs.keys()))
        if verbosity > 0:
            print("Syncing remotes %s to local data tree..." % list(satlocs.keys()))
        for key, satloc in satlocs.items():
            if satloc.DoNotSync:
                logger.info("Skipping satellite location '%s' (DoNotSync=%s)", key, satloc.DoNotSync)
                if verbosity > 1:
                    print("Skipping satellite location '%s' (DoNotSync=%s)" % (key, satloc.DoNotSync))
                continue
            self.sync_remote(key, onlyexpids=onlyexpids, verbosity=verbosity, dryrun=dryrun)
        if verbosity > 1:
            print("Sync from '%s' complete!" % list(satlocs.keys()))


    def sync_remote(self, remote, onlyexpids=None, verbosity=None, dryrun=None):
        """
        Determines the best method to sync remote based on the remote's folderscheme.
        This must currently be either by subentry or experiment.
        """
        satloc = self.Satellitemanager.get(remote)
        # How to sync depends on the folderscheme:
        # if it is /year/experiment (and no subentries), we have to do it one way,
        # and if the folderscheme includes /subentry/, then we do it another.
        schemekeys = [key for key in satloc.Folderscheme.split('/') if key and key != '.']
        if 'subentry' in schemekeys:
            logger.info("Syncing remote '%s' using sync_subentries()...", remote)
            self.sync_subentries(remote, onlyexpids=onlyexpids, verbosity=verbosity, dryrun=dryrun)
        elif 'experiment' in schemekeys:
            logger.info("Syncing remote '%s' using sync_experimentfolders()...", remote)
            self.sync_experimentfolders(remote, onlyexpids=onlyexpids, verbosity=verbosity, dryrun=dryrun)
        else:
            raise NotImplementedError("Remote is '%s', but folderscheme ('%s') does not include 'subentry' or 'experiment'.\
                                      These must currently be present in folderscheme for sync to work." % (remote, satloc.Folderscheme))

    def sync_experimentfolders(self, remote, onlyexpids=None, verbosity=None, dryrun=None):
        """
        Initializes a one-way sync from remote into the local experiment data tree.
        """
        exps = self.Experimentmanager.findLocalExpsPathGdTupByExpid()
        # exps[expid] = (path, match-group-dict)
        satloc = self.Satellitemanager.get(remote)
        loc_ds = satloc.getExpfoldersByExpid()
        # loc_ds[expid][subentry_idx] = subentry_folder
        logger.debug("Local experiments: %s", list(exps.keys()))
        logger.debug("Satellite experiments: %s", loc_ds.keys())

        # Python 3 dict views support '&', '|' and other set-like operators:
        try:
            common_expids = exps.keys() & loc_ds.keys()
        except TypeError:
            common_expids = exps.viewkeys() & loc_ds.viewkeys() # python 2.7:
        if onlyexpids:
            common_expids = common_expids & set(onlyexpids)
        logger.info("Syncing experiments: %s", common_expids)
        if verbosity > 0:
            print("Syncing experiments: %s" % common_expids)
        for expid in common_expids:
            #exp = exps[expid]
            #localdirpath = exp if isinstance(exp, string_types) else exp.Localdirpath
            localdirpath, _ = exps[expid]
            #logger.info("Syncing for exp '%s' (%s)", expid, localdirpath)
            remotefolder = loc_ds[expid]
            logger.info("Syncing for expriment %s : (%s -> %s)", expid, remotefolder, localdirpath)
            satloc.syncToLocalDir(remotefolder, localdirpath, verbosity=verbosity, dryrun=dryrun)
        logger.info("'%s' sync complete.", remote)


    def sync_subentries(self, remote, onlyexpids=None, verbosity=None, dryrun=None):
        """
        Initializes a one-way sync from remote into the local experiment data tree.
        """
        exps = self.Experimentmanager.findLocalExpsPathGdTupByExpid()
        # exps[expid] = (path, match-group-dict)
        satloc = self.Satellitemanager.get(remote)
        loc_ds = satloc.getSubentryfoldersByExpidSubidx()  # satloc.SubentryfoldersByExpidSubidx    # Use the cached version?
        # loc_ds[expid][subentry_idx] = subentry_folder
        logger.debug("Local experiments: %s", list(exps.keys()))
        logger.debug("Satellite experiments: %s", loc_ds.keys())

        # Python 3 dict views support '&', '|' and other set-like operators:
        try:
            common_expids = exps.keys() & loc_ds.keys()
        except TypeError:
            common_expids = exps.viewkeys() & loc_ds.viewkeys() # python 2:
        if onlyexpids:
            common_expids = common_expids & set(onlyexpids)
        logger.info("Syncing for experiments: %s", common_expids)
        if verbosity > 0:
            print("Syncing experiments: %s" % common_expids)
        for expid in common_expids:
            #exp = exps[expid]
            #localdirpath = exp if isinstance(exp, string_types) else exp.Localdirpath
            localdirpath, _ = exps[expid]
            logger.info("Syncing for exp '%s' (%s)", expid, localdirpath)
            for subidx, subfolder in loc_ds[expid].items():
                logger.info("Syncing for subentry %s%s: ('%s' -> '%s')", expid, subidx, subfolder, localdirpath)
                satloc.syncToLocalDir(subfolder, localdirpath, verbosity=verbosity, dryrun=dryrun)
        logger.info("'%s' sync complete.", remote)


    def duplicates_check(self, ):
        """
        Implementation:
            Just get a list of duplicates, let the user resolve it.
            This is done separately, in ExperimentManager and SatelliteLocation.
            This should be done both for experiments and for subentries.
        """
        pass
        #em = self.ExperimentManager
        #sm = self.SatelliteManager
        ## This should be done by these, separately.
        # For satellite, should be done in satellite_location.
        #remote_exp_scheme = sm.getFolderschemeUpTo('experiment')
        #foldermatchtuples = self.genPathGroupdictTupByPathscheme(regexs, basedir, folderscheme=scheme)

    def check_local_rename(self, ):
        """
        Implementation:
            1) Check for renamed experiments. Only for satellites that has experiment folders.
            2) Check for renamed subentries:
                - Get Expids and subentries from ExperimentManager (how?)
                - Get Expids and subentries with satloc.getSubentryfoldersByExpidSubidx()
                - Run similarly to sync, but just check if the foldername of all remote
                  subentries match that of the local subentry folder.
                - For those that do not match: Give option to rename remote to match local.
                  (If user wants something else, skip rename, rename local to desired name, and run again.)

        Note: This should be run AFTER checking for duplicate experiments/subentries.
        """

        pass



if __name__ == '__main__':

    """

    ## TODO: Add check for duplicate Experiments and Subentry folders (locally and remote).

    ## TODO: Add check for whether folders in satellite location has been renamed locally,
             with option to rename the folder on remote.

    ## TODO: Add optional checksum calculation of files before overwriting.

    """

    import argparse
    import time
    import os
    import sys

    scriptdir = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(scriptdir)

    from confighandler import ExpConfigHandler
    from experimentmanager import ExperimentManager
    from satellite_manager import SatelliteManager

    parser = argparse.ArgumentParser("Satellite sync")
    parser.add_argument('remote', nargs='*', help="The remotes to synchronize (by keys, as defined in your config).\
                        If omitted, sync all remotes except those where donotsync is set to True.")
    parser.add_argument('--expids', '-e', nargs='*', help="Sync only for experiments with these Experiment IDs.")
    parser.add_argument('--verbose', '-v', action='count', default=0, help="Increase verbosity of printed output (independent on loglevels).")
    parser.add_argument('--dryrun', '-n', action='store_true', help="Print output but do not actually perform sync.")
    parser.add_argument('--loglevel', default='ERROR', help="Default LOG LEVEL to report.", choices=('debug', 'info', 'warning', 'error'))
    parser.add_argument('--logformat', default='time', help="Logging format to use.", choices=('code', 'time'))
    argns = parser.parse_args()

    # https://docs.python.org/2/library/logging.html, https://docs.python.org/2/howto/logging.html,
    # https://docs.python.org/2/library/time.html#time.strftime
    # Default logging format DOES INCLUDE miliseconds, but only because that is a special case in the standard module's code.
    # However, to have that with a custom datefmt is not super simple. It is possible, but requires a custom logging.Formatter.
    # See http://stackoverflow.com/questions/6290739/python-logging-use-milliseconds-in-time-format for details.
    # Maps a logging key to a pair of (logformat, datefmt) strings. - Nope, just logformats for now, always using default datefmt.
    logfmts = {'code': "%(levelname)-5s%(name)12s:%(lineno)-4s%(funcName)16s()>> %(message)s",     # good for code debugging
               'time': '%(asctime)-23s %(levelname)s - %(message)s'}

    #logging.basicConfig(level=logging.DEBUG, format=logfmt)
    logging.basicConfig(level=getattr(logging, argns.loglevel.upper()), format=logfmts[argns.logformat])
    #logging.getLogger('satellite_location').setLevel(logging.INFO)
    # You may want to have some way to specify verbosity other than logging (but with printing...)
    #logging.getLogger('__main__').setLevel(logging.INFO)


    ch = ExpConfigHandler()
    em = ExperimentManager(ch)
    sm = SatelliteManager(ch)
    syncmgr = SyncManager(em, sm)

    #print("argns.verbose:",argns.verbose)

    if argns.verbose:
        print("%s : Sync started..." %  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    logger.info("Syncing remote '%s' to local data tree..." % argns.remote)
    syncmgr.sync_remotes(argns.remote, onlyexpids=argns.expids, verbosity=argns.verbose, dryrun=argns.dryrun)
    if argns.verbose:
        print("%s : Sync completed!" %  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    logger.info("Sync from '%s' complete!" % argns.remote)
