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

import yaml
import os.path
from collections import OrderedDict


class ConfigHandler(object):

    """
    For now, the configs are "flat", i.e. no nested entries, ala config["subject"]["key"] = value. Only config["key"] = value.
    """

    def __init__(self, systemconfigfn=None, userconfigfn=None, VERBOSE=0): 
        self.VERBOSE = VERBOSE
        self.ConfigPaths = OrderedDict()
        self.Configs = OrderedDict()
        self.Config_path_entries = dict(system='system_config_path', user='user_config_path') # maps e.g. "system_config_path" to 'system'.
        self.ConfigPaths['system'] = systemconfigfn
        self.ConfigPaths['user'] = userconfigfn
        self.Configs['system'] = dict()
        self.Configs['user'] = dict()
        self.DefaultConfig = 'user'
        self.AutoreadNewFnCache = dict() #list()
        self.ReadFiles = set()
        self.ReadConfigTypes = set()
        self.AllowChainToSameType = True # If one system config file has been loaded, allow loading another?
        self.AllowNextConfigOverrideChain = True # Similar, but does not alter the original config filepath.
        


    def getConfigPath(self, what='all', aslist=False):
        if what=='all':
            return self.ConfigPaths.values()
        elif aslist:
            return self.ConfigPaths.get(what, None), 
        else:
            return self.ConfigPaths.get(what, None)


    def getConfig(self, what='all', aslist=False):
        if what == 'combined':
            combined = dict()
            for config in self.Configs.values():
                combined.update(config)
            if aslist:
                return (combined, )
            else:
                return combined
        elif what=='all':
            return self.Configs.values()
        else:
            if aslist:
                return (self.Configs.get(what, None), )
            else:
                return self.Configs.get(what, None)

    def get(self, key, default=None):
        """ 
        Simulated the get method of a dict.
        """
        return self.getConfig(what='combined').get(key, default)

    def setdefault(self, key, value=None):
        for cfgtype, config in self.Configs.items():
            if key in config:
                return config[key]
        # If key is not found, set default in default config ('user')
        return self.Configs.get(self.DefaultConfig).setdefault(key, value)

    def setkey(self, key, value):
        for cfgtype, config in self.Configs.items():
            if key in config:
                config[key] = value
        self.Configs.get(self.DefaultConfig)[key] = value


    def readConfig(self, inputfn, cfgtype='user', VERBOSE=None):
        if VERBOSE is None:
            VERBOSE = self.VERBOSE
        if cfgtype is None:
            cfgtype = self.Configs.values()[0]
        if not self.AllowChainToSameType and cfgtype in self.ReadConfigTypes:
            return
        if inputfn in self.ReadFiles:
            print "WARNING, file already read: {}".format(inputfn)
            return
        newconfig = yaml.load(open(inputfn)) # I dont think this needs with... or open/close logic.
        self.ReadConfigTypes.add(cfgtype)
        self.ReadFiles.add(inputfn) # To avoid recursion...
        self.Configs[cfgtype].update(newconfig)
        if VERBOSE > 3:
            print "\nreadConfig() :: New '{}'-type config loaded:".format(cfgtype)
            self._printConfig(newconfig)
            print "\nreadConfig() :: Updated main '{}' config to be:".format(cfgtype)
            self._printConfig(self.Configs[cfgtype])
        if "next_config_override_fn" in newconfig and self.AllowNextConfigOverrideChain:
            # the next_config_override_fn are read-only, but their content will be persisted to the main configfile.when saved.
            if VERBOSE:
                print "\nreadConfig() :: Reading config defined by next_config_override_fn entry: {}".format(newconfig["next_config_override_fn"])
            self.readConfig(newconfig["next_config_override_fn"], cfgtype)
        reversemap = dict( (val, key) for key,val in self.Config_path_entries.items() )
        for key in set(newconfig.keys()).intersection(self.Config_path_entries.values()):
            if VERBOSE > 2:
                print "\nreadConfig() :: Found the following path_entries key '{}' in the new config: {}".format(key, newconfig[key])
            # I am currently iterating over ConfigPaths. Altering an iterator during iteration causes  problems with Python!
#            self.ConfigPaths[reversemap[key]] = newconfig[key]
            # instead, do this:
            self.readConfig(newconfig[key], reversemap[key])
            self.AutoreadNewFnCache[reversemap[key]] = newconfig[key]


    def autoRead(self, VERBOSE=None):
        if VERBOSE is None:
            VERBOSE = self.VERBOSE
        if VERBOSE:
            print "ConfigPaths:\n{}".format("\n".join("- {} :\t {}".format(k,v) for k,v in self.ConfigPaths.items()))
        for (cfgtype, inputfn) in self.ConfigPaths.items():
            if inputfn:
                if VERBOSE > 1:
                    print "autoRead() :: Will read config '{}' to current dict: {}".format(inputfn, cfgtype)
                self.readConfig(inputfn, cfgtype)
                if VERBOSE > 1:
                    print "autoRead() :: Finished read config '{}' to dict: {}".format(inputfn, cfgtype)
        if VERBOSE:
            print "autoRead() :: Autoreading done, chained with new filenames: {}".format(self.AutoreadNewFnCache)
        self.ConfigPaths.update(self.AutoreadNewFnCache)
        self.AutoreadNewFnCache.clear()
        if VERBOSE:
            print "\nautoRead() :: Updated ConfigPaths:\n{}".format("\n".join("- {} : {}".format(k,v) for k,v in self.ConfigPaths.items()))


    def saveConfigs(self, what='all'):
        if VERBOSE is None:
            VERBOSE = self.VERBOSE
        #for (outputfn, config) in zip(self.getConfigPath(what='all'), self.getConfig(what='all')):
        for cfgtype,outputfn in self.ConfigPaths.items():
            if (what=='all' or cfgtype in what or cfgtype==what):
                if outputfn: 
                    if VERBOSE:
                        print "saveConfigs() :: Saving config '{}' to file: {}".format(cfgtype, outputfn)
                    self._saveConfig(outputfn, self.Configs[cfgtype])
                else:
                    print "saveConfigs() :: No filename specified for config '{}'".format(cfgtype)

    def _saveConfig(self, outputfn, config, desc=''):
        if VERBOSE is None:
            VERBOSE = self.VERBOSE
        try:
            yaml.dump(config, open(outputfn, 'wb'), default_flow_style=False)
            print "_saveConfig() :: Config saved to file: {}".format(outputfn)
            return True
        except IOError, e:
            # This is to be expected for the system config...
            print "_saveConfig() :: Could not save config to file: {}".format(outputfn)


    def _printConfig(self, config, indent=2):
        for k,v in config.items():
            print "{indent}{k}: {v}".format(indent=' '*indent, k=k, v=v)

    def printConfigs(self, what='all'):
        for cfgtype,outputfn in self.ConfigPaths.items():
            if (what=='all' or cfgtype in what or cfgtype==what):
                print "\nConfig '{}' in file: {}".format(cfgtype, outputfn)
                self._printConfig(self.Configs[cfgtype])


    def getConfigDir(self, what='user'):
        """ Returns the directory of a particular configuration (file); defaulting to the 'user' config.
        Valid arguments are: 'system', 'user', 'exp', etc.
        """
        return os.path.dirname(self.getConfigPath(what))




class ExpConfigHandler(ConfigHandler):
    def __init__(self, systemconfigfn=None, userconfigfn=None, expconfigfn=None, VERBOSE=0, readfiles=True, pathscheme='default1'):
        self.Pathfinder = PathFinder()
        if pathscheme:
            psys, puser, pexp = self.Pathfinder.getScheme(pathscheme)
        systemconfigfn = systemconfigfn or psys
        userconfigfn = userconfigfn or puser
        expconfigfn = expconfigfn or pexp
        ConfigHandler.__init__(self, systemconfigfn, userconfigfn, VERBOSE=VERBOSE)
        self.Configs['exp'] = dict()
        self.ConfigPaths['exp'] = expconfigfn
        self.Config_path_entries['exp'] = "exp_config_path"
        if readfiles:
            if VERBOSE:
                print "__init()__ :: autoreading..."
            self.autoRead()
        elif VERBOSE:
            print "__init()__ :: not autoreading..."



class PathFinder(object):
    def __init__(self, scheme='default1', npathsdefault=3):
        self.Schemes = dict()
        self.Npathsdefault = npathsdefault
        # defautl1 scheme: sysconfig in 'config' folder in current dir; 
        self.Schemes['default1'] = ('config/labfluence_sys.yml', os.path.expanduser(os.path.join('~', '.Labfluence', 'labfluence_user.yml')), None )

    def getScheme(self, scheme):
        return self.Schemes.get(scheme, (None, )*self.Npathsdefault)





if __name__ == '__main__':
    
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    configtestdir = os.path.join(scriptdir, '../test/config')
    paths = [ os.path.join(configtestdir, cfg) for cfg in ('system_config.yml', 'user_config.yml', 'exp_config.yml') ]
    
    def test1():
        ch = ExpConfigHandler(*paths)
        print "\nEnd ch confighandler init...\n\n"
        return ch

    def printPaths():
        print "os.path.curdir:            {}".format(os.path.curdir)
        print "os.path.realpath(curdir) : {}".format(os.path.realpath(os.path.curdir))
        print "os.path.abspath(__file__): {}".format(os.path.abspath(__file__))
        #print "os.path.curdir: {}".format(os.path.curdir)

    printPaths()

    def test_makedata():
        ch = test1()
        print 'ch.Configs:'
        print ch.Configs
        ch.Configs['system']['install_version_str'] = '0.01'
        ch.Configs['user']['username'] = 'scholer'
        ch.Configs['user']['exp_config_path'] = os.path.join(os.path.expanduser("~"), 'Documents', 'labfluence_data_testsetup', '.labfluence.yml')
        usr = ch.setdefault('wiki_username', 'scholer')
        print "Default user: {}".format(usr)
        ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
        print "ch.get('wiki_username') --> {}".format(ch.get('wiki_username'))
        print "Config, combined:"
        print ch.getConfig(what='combined')

    def testConfigTypeChain():
        ch2 = ExpConfigHandler('../test/config/system_config.yml')
        print 'ch2.Configs:'
        print ch2.Configs
        ch2.Configs
        ch2.Configs['system']['user_config_path'] = os.path.join(configtestdir, 'user_config.yml')
        ch2.saveConfigs()
        ch3 = ExpConfigHandler('../test/config/system_config.yml')
        print 'ch3.Configs:'
        print ch3.Configs


    def test_save1():
        ch.saveConfigs()
    
    def test_readdata():
        ch.autoReader()
        for cfg in ('system', 'user', 'exp'):
            print "\n\n{} config:".format(cfg)
            print ch.Configs[cfg]


    def testPfAndChain():
        ch3 = ExpConfigHandler( pathscheme='default1', VERBOSE=10)
        ch3.printConfigs()
        return ch3

    #test_makedata()
    #test_save1()
#    testConfigTypeChain()
    #test_readdata()
    testPfAndChain()

