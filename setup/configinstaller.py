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
# pylint: disable-msg=C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221
# messages:
#   C0301: Line too long (max 80), R0902: Too many instance attributes (includes dict())
#   C0302: too many lines in module; R0201: Method could be a function; W0142: Used * or ** magic
#   R0904: Too many public methods (20 max); R0913: Too many arguments;
#   W0221: Arguments differ from overridden method
"""

Module for installing configs etc.

"""




import os
import shutil
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)






class ConfigInstaller(object):

    """
    Class for installing configs.
    Not sure a class is really, really needed, but makes testing a bit easier.
    """

    def __init__(self, ):
        # Ordered dict of.
        # configtype : ( <copy from path>, <copy-to-path> )
        self.Paths = OrderedDict(system = (os.path.join('setup', 'configs', 'new_install', 'labfluence_sys.yml'),
                                    os.path.join('configs', 'labfluence_sys.yml')),
                            user = (os.path.join('setup', 'configs', 'new_install', 'labfluence_user.yml'),
                                    os.path.join(os.path.expanduser('~'), '.labfluence', 'labfluence_user.yml')),
                            exp = (os.path.join('setup', 'configs', 'new_install', 'labfluence_exp.yml'),
                                    os.path.join(os.path.expanduser('~'), 'Experiments', '.labfluence.yml'))
                           )

    def install_configs(self, ):
        """
        Install configs.
        """
        print "Installing labfluence configuration files..."
        print """Notice: If you select non-default locations for configs,
you must figure out ourself how to activate those with labfluence."""
        locations = dict()
        for cfgtype, (from_path, to_path) in self.Paths.items():
            from_path = os.path.realpath(from_path)
            to_path_fn = os.path.basename(to_path)
            to_path = os.path.realpath(os.path.expanduser(to_path))
            new_dir = self.new_dir_prompt(cfgtype, to_path)
            if new_dir:
                to_path = os.path.join(os.path.expanduser(new_dir), to_path_fn)

            if not os.path.isfile(from_path):
                logger.error("Error, config in path '%s' is not a file, skipping.", from_path)
                continue
            if os.path.exists(to_path):
                overwrite = raw_input(u"Warning, file in path\n    {}\nalready exists. Overwrite with new config? ".format(from_path))
                if not overwrite or not overwrite[0].lower() == 'y':
                    continue
            basedir = os.path.dirname(to_path)
            if not os.path.isdir(basedir):
                try:
                    os.makedirs(basedir)
                    logger.info("Created directory\n    '%s'", basedir)
                except (OSError, IOError) as e:
                    logger.error("Error while making directory\n    '%s'\nfor config '%s': %s",
                                 os.path.basename(to_path), cfgtype, e)
                    continue
            else:
                logger.debug("Basedir exists:\n    %s", basedir)
            try:
                shutil.copy2(from_path, to_path)
                logger.info("Copied file\n    %s\nto path\n    %s", from_path, to_path)
            except (OSError, IOError) as e:
                logger.error("Error while making directory '%s' for config '%s': %s",
                             os.path.basename(to_path), cfgtype, e)
            locations[cfgtype] = to_path

        print u"The following configs were installed: {}".format(locations.keys())
        print """Notice: Before labfluence can be used for anything, you must edit the config files
and insert correct configuration values for e.g. the wiki server, etc."""
        return locations


    def new_dir_prompt(self, cfgtype, to_path):
        """
        Prompts the user for a location for config <cfgtype>,
        defaulting to path <to_path> (to_path must be the final filepath).
        Returns the directory to put it in.
        """
        new_dir = raw_input(u"Where do you want to install the '{}' config (default: [{}]) : \n  ".format(
                        cfgtype, os.path.dirname(to_path)))
        if new_dir and not os.path.isabs(os.path.expanduser(new_dir)):
            print "Specified directory must be absolute, '%s' is not." % new_dir
            new_dir = self.new_dir_prompt(cfgtype, to_path)
        return new_dir


if __name__ == '__main__':
    #logfmt = "%(levelname)s %(name)s:%(lineno)s %(funcName)s() > %(message)s"
    logfmt = "%(levelname)s: %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=logfmt)
    installer = ConfigInstaller()
    installer.install_configs()
