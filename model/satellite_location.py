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
# messages:
#   C0301: Line too long (max 80), R0902: Too many instance attributes (includes dict())
#   C0302: too many lines in module; R0201: Method could be a function; W0142: Used * or ** magic
#   R0904: Too many public methods (20 max); R0913: Too many arguments;
#   W0221: Arguments differ from overridden method,
#   W0402: Use of deprechated module (e.g. string)
#   E1101: Instance of <object> has no <dynamically obtained attribute> member.
#   R0921: Abstract class not referenced. Pylint thinks any class that raises a NotImplementedError somewhere is abstract.
#   E0102: method already defined in line <...> (pylint doesn't understand properties well...)
#   E0202: An attribute affected in <...> hide this method (pylint doesn't understand properties well...)
#   C0303: Trailing whitespace (happens if you have windows-style \r\n newlines)
#   C0111: Missing method docstring (pylint insists on docstrings, even for one-liner inline functions and properties)
#   W0201: Attribute "_underscore_first_marks_insternal" defined outside __init__ -- yes, I use it in my properties.
# Regarding pylint failure of python properties: should be fixed in newer versions of pylint.
"""
Code for dealing with satellite locations.
Consider using virtualfs python module to normalize external locations,
rather than implementing ftp, etc...
"""
import os
import re
import shutil
import time
# FTP not yet implemented...
#from ftplib import FTP
import logging
logger = logging.getLogger(__name__)



class SatelliteLocation(object):
    """
    Base class for satellite locations, treats the location as if it is a locally available file system.
    """
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
    pass