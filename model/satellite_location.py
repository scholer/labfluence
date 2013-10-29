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


import os
import re
import shutil
import time
# FTP not yet implemented...
#from ftplib import FTP
import logging
logger = logging.getLogger(__name__)



class SatelliteLocation(object):

    def __init__(self, uri, confighandler):
        self.URI = uri
        self.Confighandler = confighandler
        self.Protocol = confighandler.get('satellite_locations', dict()).get(uri, dict()).get('protocol', 'file')
        self.Folderscheme = confighandler.get('satellite_locations', dict()).get(uri, dict()).get('folderscheme', './subentry/')
        self.Rootdir = confighandler.get('satellite_locations', dict()).get(uri, dict()).get('rootdir', '.')


    def findSubentries(self, regexpat, basepath='.', folderscheme=None):
        if folderscheme is None:
            folderscheme = self.Folderscheme
        if isinstance(regexpat, basestring):
            regexpat = re.compile(regexpat)
        basepath = self.getRealPath(basepath)
        if folderscheme == './experiment/subentry/':
            subentryfolders = ( (subentry, self.join(basepath, experiment, subentry))
                     for experiment in self.listdir(basepath) if self.isdir(self.join(basepath, experiment))
                        for subentry in self.join(basepath,experiment) if self.isdir(self.join(basepath, experiment, subentry)) )
        else: # e.g. if self.FolderScheme == './subentry/':
            subentryfolders = ( (subentry, self.join(basepath, subentry)) for subentry in self.listdir(basepath) )

        dirs = [path for foldername, path in subentryfolders if regexpat.match(foldername) ]
        return dirs



    def findDirs(self, regexpat, basepath='.'):
        return self.findSubentries(regexpat=regexpat, basepath=basepath, folderscheme='./subentry/')






class SatelliteFileLocation(SatelliteLocation):
    """
    This is either a local folder or another resource that has been mounted as a local file system,
    and is available for manipulation using standard filehandling commands.
    In other words, if you can use ls, cp, etc on the location, this is the class to use.
    """

    def __init__(self, uri, confighandler):
        super(SatelliteFileLocation, self).__init__(uri, confighandler)
        # python3 is just super().__init__(uri, confighandler)
        # old school must be invoked with BaseClass.__init__(self, ...), like:
        # SatelliteLocation.__init__(self,
        self.ensureMount()


    def ensureMount(self):
        """
        Ensures that the file location is available.
        """
        if not self.isMounted():
            print "\nSatelliteFileLocation does not seem to be correctly mounted (it might just be empty, but hard to tell)\n{}\--will try to mount with mountcommand...".format(self.URI)
            ec = self.mount()
            return ec
        print "\nSatelliteFileLocation correctly mounted (well, it is not empty): {}".format(self.URI)

    def mount(self):
        """
        Uses mountcommand to mount; is specific to each system.
        Not implemented yet.
        Probably do something like #http://docs.python.org/2/library/subprocess.html
        """
        mountcommand = confighandler.get('satellite_locations', dict()).get(uri, dict()).get('mountcommand', None)
        if not mountcommand:
            return
        import subprocess, sys
        errorcode = subprocess.call(mountcommand, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
        return errorcode

    def isMounted(self):
        return len(os.listdir(self.getRealRootPath()))

    def getRealRootPath(self):
        return self.getRealPath()

    def getRealPath(self, path='.'):
        return os.path.normpath(os.path.join(self.URI, self.Rootdir, path))

    def listdir(self, path):
        return os.listdir(os.path.join(self.getRealRootPath(), path))

    def join(self, *paths):
        return os.path.join(*paths)

    def isdir(self, path):
        return os.path.isdir(os.path.join(self.getRealRootPath(), path))


    def syncToLocalDir(self, satellitepath, localpath):
        """
        Consider making a call to rsync and see if that is available, and only use the rest as a fallback...
        """
        if not os.path.isdir(localpath):
            print "\nSatelliteFileLocation.syncToLocalDir() :: localpath '{}' is not a directory, skipping...".format(localpath)
            return
        realpath = self.getRealPath(satellitepath)
        # If it is just a file:
        if os.path.isfile(realpath):
            self.syncFileToLocalDir(satellitepath, localpath)
            return
        elif not os.path.isdir(realpath):
            print "\nSatelliteFileLocation.syncToLocalDir() :: satellitepath '{}' is not a file or directory, skipping...".format(realpath)
            return
        # We have a folder:
        # Note, if satellitepath ends with a '/', the basename will be ''.
        # This will thus cause the contents of satellitepath to be copied into localpath, rather than localpath/foldername
        # I guess this is also the behaviour of e.g. rsync, so should be ok. Just be aware of it.
        foldername = os.path.basename(satellitepath)
        # If the folder does not exists in localpath destination, just use copytree:
        if not os.path.exists(os.path.join(localpath, foldername)):
            print "shutil.copytree({}, os.path.join({},{}))".format(realpath,localpath, foldername)
            shutil.copytree(realpath, os.path.join(localpath, foldername))
            return True
        # foldername already exists in local directory, just recurse for each item...
        for item in os.listdir(realpath):
            self.syncToLocalDir(os.path.join(satellitepath, item), os.path.join(localpath, foldername))


    def syncFileToLocalDir(self, satellitepath, localpath):
        if not os.path.isdir(localpath):
            print "\nSatelliteFileLocation.syncFileToLocalDir() :: localpath '{}' is not a directory, skipping...".format(localpath)
            """Consider perhaps overwriting instead..."""
            return
        srcfilepath = self.getRealPath(satellitepath)
        if not os.path.isfile(srcfilepath):
            print "\nSatelliteFileLocation.syncFileToLocalDir() :: file '{}' is not a file, skipping...".format(srcfilepath)
            return
        filename = os.path.basename(srcfilepath)
        destfilepath = os.path.join(localpath, filename)
        if not os.path.exists(destfilepath):
            print "syncFileToLocalDir() :: shutil.copy2(\n{},\n{})".format(srcfilepath, destfilepath)
            return shutil.copy2(srcfilepath, destfilepath)
            return
        print "\nSatelliteFileLocation.syncFileToLocalDir() :: NOTICE, destfile exists: '{}' ".format(destfilepath)
        if os.path.isdir(destfilepath):
            print "\nSatelliteFileLocation.syncFileToLocalDir() :: destfilepath '{}' is a directory in localpath, skipping...".format(destfilepath)
            return
        if not os.path.isfile(destfilepath):
            print "\nSatelliteFileLocation.syncFileToLocalDir() :: destfilepath '{}' exists but is not a file, skipping...".format(destfilepath)
            return
        # destfilepath is a file, determine if it should be overwritten...
        if os.path.getmtime(srcfilepath) > os.path.getmtime(destfilepath):
            print "\nSatelliteFileLocation.syncFileToLocalDir() :: srcfile '{}' is newer than destfile '{}', overwriting destfile...".format(srcfilepath, destfilepath)
            print "shutil.copy2({}, {})".format(srcfilepath, destfilepath)
            shutil.copy2(srcfilepath, destfilepath)
        else:
            print "\nSatelliteFileLocation.syncFileToLocalDir() :: srcfile '{}' is NOT newer than destfile '{}', NOT overwriting destfile...".format(srcfilepath, destfilepath)
        print "\n".join( "-- {} last modified: {}".format(f, modtime)
                        for f, modtime in ( ('srcfile ', time.ctime(os.path.getmtime(srcfilepath))),
                                            ('destfile', time.ctime(os.path.getmtime(destfilepath))) ) )







class SatelliteFtpLocation(SatelliteLocation):
    """
    This class is intended to deal with ftp locations.
    This has currently not been implemented.
    On linux, you can mount ftp resources as a locally-available filesystem using curlftpfs,
    and use the SatelliteFileLocation class to manipulate this location.

    Other resources that might be interesting to implement:
    - http
    - webdav
    - ...
    """
    pass






if __name__ == '__main__':

    from confighandler import ExpConfigHandler
    ch = ExpConfigHandler(pathscheme='default1')
    satpath = "/home/scholer/Documents/labfluence_satellite_tests/cdnaafm_cftp"
    sfl = SatelliteFileLocation(satpath, ch)


    def test_init():
        print "\n>>>>> test_init() -----------------"
        print sfl.__dict__ # equivalent to vars(sfl)
        print "<<<<< completed test_init() -------"

    def test_findDirs():
        print "\n>>>>> test_findDirs() -----------------"
#        regexpat = ch.get('exp_subentry_regex').format(expid=RS115, subentry_idx=
        regexpat = ch.get('exp_subentry_regex')
        all_subentries = sfl.findDirs(regexpat)
        print 'all_subentries:'
        print "\n".join(all_subentries)
        print "<<<<< completed test_findDirs() -------"

    def test_findSubentries():
        print "\n>>>>> test_findSubentries() -----------------"
#        regexpat = ch.get('exp_subentry_regex').format(expid=RS115, subentry_idx=
        regexpat = ch.get('exp_subentry_regex')
        all_subentries = sfl.findSubentries(regexpat)
        print 'all_subentries:'
        print "\n".join(all_subentries)
        print "<<<<< completed test_findSubentries() -------"



    def test_syncToLocalDir1():
        print "\n>>>>> test_syncToLocalDir1() -----------------"
        destdir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/"
        sfl.syncToLocalDir("20130222 RS115g Dry-AFM of transferin TR",
                "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1")
        print "<<<<< completed test_syncToLocalDir1() -------"

    def test_syncToLocalDir2():
        print "\n>>>>> test_syncToLocalDir2() -----------------"
        # Testing sync-into with trailing '/' on source:
        destdir = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1/RS115g Dry-AFM of Transferrin TR (20130222)"
        if not os.path.exists(destdir):
            os.makedirs(destdir)
        sfl.syncToLocalDir("20130222 RS115g Dry-AFM of transferin TR/", destdir)
        print "<<<<< completed test_syncToLocalDir2() -------"

    def test_syncFileToLocalDir():
        print "\n>>>>> test_syncFileToLocalDir() -----------------"
        sfl.syncFileToLocalDir("20130222 RS115g Dry-AFM of transferin TR/RS115g_c5-grd1_TRctrl_130222_105519.mi",
                    "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS115 Transferrin TR v1/20130222 RS115g Dry-AFM of transferin TR (old)")
        print "<<<<< completed test_syncFileToLocalDir() -------"




    def test_test():
        pass

    print "\n------- starting satellite_locations testing... ----------- "
    test_init()
    test_findSubentries()
    test_findDirs()
#    test_syncFileToLocalDir()
#    test_syncToLocalDir1()
    test_syncToLocalDir2()
    print "\n------- satellite_locations testing complete ----------- "
