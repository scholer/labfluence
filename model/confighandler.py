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
import os
import os.path
from datetime import datetime
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)


# from http://stackoverflow.com/questions/4579908/cross-platform-splitting-of-path-in-python
def os_path_split_asunder(path, debug=False):
    parts = []
    while True:
        newpath, tail = os.path.split(path)
        if debug: print repr(path), (newpath, tail)
        if newpath == path:
            assert not tail
            if path: parts.append(path)
            break
        parts.append(tail)
        path = newpath
    parts.reverse()
    return parts



class ConfigHandler(object):

    """
    For now, the configs are "flat", i.e. no nested entries, ala config["subject"]["key"] = value. Only config["key"] = value.

    A config type can be added through the following mechanisms:
    1.  By specifying ch.ConfigPaths[cfgtype] = <config filepath>.
        ConfigPaths are read during autoRead().
        Specifying this way requires the config filepath to be directly or indirectly
        specified in the source code. This is thus only done for the 'system' and 'user' configs.

    2.  Specifying ch.Config_path_entries[cfgtype] = <config key name>
        During autoRead, if a config contains a key <config key name>, the value of that config entry
        is expected to be a file path for a config of type <cfgtype>.
        This is e.g. how 'exp' cfgtype is set up to load, obtaining the exp config filepath from the 'user' config.
        This requries a defining the cfgtype and config-key in the source code, but no hard-coding of filepaths.
        Note: These configs are added to AutoreadNewFnCache, which is used to
            a) Make sure not to load new configs many times, and
            b) Adding the config filepath to ch.ConfigPaths upon completing ch.autoRead().
        The latter ensures that e.g. 'exp' config can be saved with ch.saveConfig().

    3.  Using ch.addNewConfig(inputfn, cfgtype).
        This will also add the config filepath to ch.ConfigPaths, making it available for ch.saveConfigs().
        (Can be disabled by passing rememberpath=False).

    4.  In a config file by defining: config_define_new: <dict>
        where <dict> = {<cfgtype>: <config filepath>}
        This works as an ad-hoc alternative to setting ch.Config_path_entries.
        This does not require any hard-coding/changes in the source code, but might add some security
        concerns. Therefore, using this requries ch.AllowNewConfigDefinitions=True.
        This is used for e.g. defining 'templates' cfgtype.
    """

    def __init__(self, systemconfigfn=None, userconfigfn=None, VERBOSE=0):
        self.VERBOSE = VERBOSE
        self.ConfigPaths = OrderedDict()
        self.Configs = OrderedDict()
        # For retrieving paths via config entries...
        self.Config_path_entries = dict(system='system_config_path', user='user_config_path') # maps e.g. "system_config_path" to 'system'.
        self.ConfigPaths['system'] = systemconfigfn
        self.ConfigPaths['user'] = userconfigfn
        self.Configs['system'] = dict()
        self.Configs['user'] = dict()
        self.Singletons = dict() # dict for singleton objects; makes it easy to share objects across application objects that already have access to the confighandler singleton.
        self.EntryChangeCallbacks = dict()
        self.ChangedEntriesForCallbacks = set()
        self.DefaultConfig = 'user'
        self.AutoreadNewFnCache = dict() #list()
        self.ReadFiles = set()
        self.ReadConfigTypes = set()
        # Setting either of these to true requires complete trust in the putative users:
        self.AllowChainToSameType = True # If one system config file has been loaded, allow loading another?
        self.AllowNextConfigOverrideChain = True # Similar, but does not alter the original config filepath.
        self.AllowNewConfigDefinitions = True   # Allow one config to define a new config.
        self.AllowCfgtypeOverwrite = False
        """
        Defining a new config can be done in a yaml as:
        config_define_new = {<cfgtype> : <path>}
        where path if relative, is loaded relative to the current config path.
        """


    def addNewConfig(self, inputfn, cfgtype, VERBOSE=None, rememberpath=True):
        if VERBOSE is None:
            VERBOSE = self.VERBOSE
        if cfgtype in set(self.Configs).union(self.ConfigPaths) and not self.AllowCfgtypeOverwrite:
            print "addNewConfig() :: cfgtype already present in configs and overwrite not allowed; aborting..."
            return
        if rememberpath:
            self.ConfigPaths[cfgtype] = inputfn
        self.Configs[cfgtype] = dict()
        self.readConfig(inputfn, cfgtype)


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
        Note that the ExpConfigHandler's get() adds a bit more options...
        """
        return self.getConfig(what='combined').get(key, default)

    def setdefault(self, key, value=None):
        for cfgtype, config in self.Configs.items():
            if key in config:
                return config[key]
        # If key is not found, set default in default config ('user')
        return self.Configs.get(self.DefaultConfig).setdefault(key, value)

    def setkey(self, key, value, cfgtype=None, check_for_existing_entry=True):
        """
        Sets a config key.
        If key is already set in one of the main configs, and check_for_existing_entry
        is set to True then update the config where entry is found. (RECOMMENDED)
        If key is not already set, store in config specified by <cfgtype> arg.
        If cfgtype is not provided, use default config (type), e.g. 'user'.
        Returns the cfgtype where the key was persisted, e.g. 'user'.
        """
        if check_for_existing_entry:
            for cfgtyp, config in self.Configs.items():
                if key in config:
                    config[key] = value
                    return cfgtyp
        if cfgtype is None:
            cfgtype = self.DefaultConfig
        # If key is not already set, set in default config type:
        self.Configs.get(cfgtype)[key] = value
        return cfgtype

    def popkey(self, key, cfgtype=None, check_all_configs=False):
        """
        Simulates the dict.pop method; If cfgtype is specified, only tries to pop from that cfgtype.
        If check_all_configs is True, pop from all configs; otherwise stop when the first is reached.
        Returns a tuple of (value, cfgtype[, value, cfgtype, ...]).
        """
        res = ()
        if cfgtype:
            return (self.Configs[cfgtype].pop(key, None), cfgtype)
        for cfgtype, config in self.Configs.items():
            val = config.pop(key, None)
            res = res + (val, cfgtype)
            if val and not check_all_configs:
                break
        return res

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
        try:
            newconfig = yaml.load(open(inputfn)) # I dont think this needs with... or open/close logic.
        except IOError as e:
            print "readConfig() :: ERROR, could not load yaml config, cfgtype '{}'".format(cfgtype)
            print e
            return False
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
        if "config_define_new" in newconfig and self.AllowNewConfigDefinitions:
            for newtype, newconfigfn in newconfig["config_define_new"].items():
                if not os.path.isabs(newconfigfn):
                    # isabs basically just checks if path[0] == '/'...
                    newconfigfn = os.path.normpath(os.path.join(os.path.dirname(inputfn), newconfigfn))
                print "readConfig: Adding config-defined config '{}' using filepath '{}'".format(newtype, newconfigfn)
                self.addNewConfig(newconfigfn, newtype)

        # Inputting configs through Config_path_entries:
        reversemap = dict( (val, key) for key,val in self.Config_path_entries.items() )
        for key in set(newconfig.keys()).intersection(self.Config_path_entries.values()):
            if VERBOSE > 2:
                print "\nreadConfig() :: Found the following path_entries key '{}' in the new config: {}".format(key, newconfig[key])
            # I am currently iterating over ConfigPaths. Altering an iterator during iteration causes  problems with Python!
#            self.ConfigPaths[reversemap[key]] = newconfig[key]
            # instead, do this:
            self.readConfig(newconfig[key], reversemap[key])
            self.AutoreadNewFnCache[reversemap[key]] = newconfig[key]
        return newconfig


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

    def saveConfigForEntry(self, key):
        """
        Saves the config file that contains a particular entry.
        Useful if you have changed only a single config item and do not want to persist all config files.
        Example: The app changes the value of 'app_active_experiment' and invokes saveConfigForEntry('app_active_experiment')
        Note: For Hierarchical configs, use the path-based save method in ExpConfigHandler.
        """
        for cfgtype, cfg in reversed(self.Configs.items()):
            if key in cfg:
                self.saveConfigs(what=cfgtype)
                return True
        logger.warning("saveConfigForEntry invoked with key '{}', but key not found in any of the loaded configs ({})!".format(key, ",".join(self.Configs)))

    def saveConfigs(self, what='all', VERBOSE=None):
        logger.debug("saveConfigs invoked with configtosave '{}'".format(what))
        if VERBOSE is None:
            VERBOSE = self.VERBOSE
        #for (outputfn, config) in zip(self.getConfigPath(what='all'), self.getConfig(what='all')):
        for cfgtype,outputfn in self.ConfigPaths.items():
            if (what=='all' or cfgtype in what or cfgtype==what):
                if outputfn:
                    logger.info("saveConfigs() :: Saving config '{}' to file: {}".format(cfgtype, outputfn))
                    self._saveConfig(outputfn, self.Configs[cfgtype])
                else:
                    logger.info("saveConfigs() :: No filename specified for config '{}'".format(cfgtype))
            else:
                logger.debug("configtosave '{}' not matching cfgtype '{}' with outputfn '{}'".format(what, cfgtype, outputfn))

    def _saveConfig(self, outputfn, config, desc=''):
        try:
            yaml.dump(config, open(outputfn, 'wb'), default_flow_style=False)
            logger.info("_saveConfig() :: Config saved to file: {}".format(outputfn))
            return True
        except IOError, e:
            # This is to be expected for the system config...
            print "_saveConfig() :: Could not save config to file: {}".format(outputfn)


    def _printConfig(self, config, indent=2):
        for k,v in config.items():
            print "{indent}{k}: {v}".format(indent=' '*indent, k=k, v=v)

    def printConfigs(self, cfgtypestoprint='all'):
        for cfgtype,outputfn in self.ConfigPaths.items():
            if (cfgtypestoprint=='all' or cfgtype in cfgtypestoprint or cfgtype==cfgtypestoprint):
                print "\nConfig '{}' in file: {}".format(cfgtype, outputfn)
                self._printConfig(self.Configs[cfgtype])


    def getConfigDir(self, cfgtype='user'):
        """
        Returns the directory of a particular configuration (file); defaulting to the 'user' config.
        Valid arguments are: 'system', 'user', 'exp', etc.
        """
        return os.path.dirname(self.getConfigPath(cfgtype))


    def registerEntryChangeCallback(self, configentry, function, args=None, kwargs=None):
        """
        Registers a callback for a particular entry (name).
        Actually, this can be used as a simple, general-purpose callback manager, across all objects
        that have access to the Confighandler singleton. The 'configentry' key does not have to
        correspond to an actual configentry, it can just be a name that specifies that particular
        callback by concention.
        Note: I see no reason to add a 'registerConfigChangeCallback' method.
        Although this could provide per-config callbacks (e.g. an experiment that could subscribe to
        changes only for that experiment), I think it is better to code for this situation directly.

        Note that changes are not registrered automatically. It is really not possible to see if
        entries changes, e.g. dicts and lists which are mutable from outside the control of this confighandler.
        Instead, this is a curtesy service, that allows one user of the confighandler to inform
        the other objects subscribed with callbacks that something has changed.
        Use as:
            objB -> registers updateListWidget callable with 'app_active_experiments' using this method.
            objA -> adds an entry to ch.get('app_active_experiments')
            objA -> invokes invokeEntryChangeCallback('app_active_experiments')
            ch   -> calls updateListWidget.
        Alternative scheme:
            objB -> registers updateListWidget callable with 'app_active_experiments' using this method.
            objA -> adds an entry to ch.get('app_active_experiments')
            objA -> does ch.ChangedEntriesForCallbacks.add('app_active_experiments')
            < something else happens>
            objC -> figues it might be a good idea to call ch.invokeEntryChangeCallback() with no args.
            ch   -> searches through the ChangedEntriesForCallbacks set for changes since last callback.
            ch   -> calls updateListWidget.
        """
        if args is None:
            args = list()
        if kwargs is None:
            kwargs = dict()
        # I would have liked this to be a set, but hard to implement set for dict-type kwargs and no frozendict in python2.
        # Just make sure not to register the same callback twice.
        self.EntryChangeCallbacks.setdefault(configentry, list()).append( (function, args, kwargs) )
        logger.debug("Registrered callback for configentry '{}': {}(*{}, **{})".format(configentry, function, args, kwargs))
        # I could also have implemented as dict based on the function is hashable, e.g.:
        #self.EntryChangeCallbacks.setdefault(configentry, dict()).set(function, (args, kwargs) )
        # and invoke with:
        # for function, (args, kwargs) in self.EntryChangeCallbacks[configentry].items():
        #     function(*args, **kwargs)

    def invokeEntryChangeCallback(self, configentry=None):
        """
        Simple invokation of registrered callbacks.
        If configentry is provided, only callbacks registrered to that entry will be invoked.
        If configentry is None (default), all keys registrered in self.ChangedEntriesForCallbacks
        will have their corresponding callbacks invoked.
        When a configentry has had its callbacks invoked, it will be unregistrered from
        self.ChangedEntriesForCallbacks.
        """
        if configentry:
            if configentry in self.EntryChangeCallbacks:
                for function, args, kwargs in self.EntryChangeCallbacks[configentry]:
                    function(*args, **kwargs)
                    logger.debug("callback invoked for configentry '{}': {}(*{}, **{})".format(configentry, function, args, kwargs))
                self.ChangedEntriesForCallbacks.discard(configentry) # Erase this entry if registrered here.
        elif self.ChangedEntriesForCallbacks:
            # Use the self.ChangedEntriesForCallbacks set to determine what to call.
#            for entry in self.ChangedEntriesForCallbacks:
#                self.invokeEntryChangeCallback(entry)
#            self.ChangedEntriesForCallbacks.clear()
            # The ChangedEntriesForCallbacks will change during iteration, so using a while rather than for loop:
            while True:
                try:
                    entry = self.ChangedEntriesForCallbacks.pop()
                    logger.debug("Popped configentry '{}' from ChangedEntriesForCallbacks...".format(configentry))
                    self.invokeEntryChangeCallback(entry)
                except KeyError: # raised when pop on empty set.
                    break




class ExpConfigHandler(ConfigHandler):
    def __init__(self, systemconfigfn=None, userconfigfn=None, expconfigfn=None, VERBOSE=0,
                readfiles=True, pathscheme='default1', hierarchy_rootdir_config_key='local_exp_rootDir',
                enableHierarchy=True, hierarchy_ignoredirs_config_key='local_exp_ignoreDirs'):
        self.Pathfinder = PathFinder()
        pschemedict = self.Pathfinder.getScheme(pathscheme)
        systemconfigfn = systemconfigfn or pschemedict.get('sys')
        userconfigfn = userconfigfn or pschemedict.get('user')
        expconfigfn = expconfigfn or pschemedict.get('exp')
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

        if enableHierarchy and hierarchy_rootdir_config_key:
            rootdir = self.get(hierarchy_rootdir_config_key)
            ignoredirs = self.get(hierarchy_ignoredirs_config_key)
            if VERBOSE:
                print "\nExpConfigHandler.__init__() :: enabling HierarchicalConfigHandler with rootdir: {}".format(rootdir)
            if rootdir:
                self.HierarchicalConfigHandler = HierarchicalConfigHandler(rootdir, ignoredirs, VERBOSE=VERBOSE)
            else:
                print "rootdir is None; hierarchy_rootdir_config_key is {}; config is:".format(hierarchy_rootdir_config_key)
                self.printConfigs()
        else:
            self.HierarchicalConfigHandler = None


    def getHierarchicalEntry(self, key, path, traverseup=True):
        """
        Much like self.get, but only searches the HierarchicalConfigHandler configs.
        This is useful if you need to retrieve options that must be defined at the path-level,
        e.g. an exp_pageId or exp_id.
        If traverseup is set to True, then the HierarchicalConfigHandler is allowed to return a
        config value from a config in a parent directory if none is found in the first looked directory.
        """
        return self.HierarchicalConfigHandler.getEntry(key, path, traverseup=traverseup)


    def getHierarchicalConfig(self, path, rootdir=None):
        return self.HierarchicalConfigHandler.getHierarchicalConfig(path, rootdir=None)


    def get(self, key, default=None, path=None, pathsrelativetoexp=True):
        """
        Simulated the get method of a dict.
        If path is provided, will search HierarchicalConfigHandler for a matching config before
        resolving to the 'main' configs.
        """
        if path and self.HierarchicalConfigHandler:
            val = self.getHierarchicalEntry(key, path)
            if val is not None:
                return val
        # return self.getConfig(what='combined').get(key, default)
        # Optimized, and accounting for the fact that later added cfgs overrides the first added
        for cfgtype, cfg in reversed(self.Configs.items()):
            if key in cfg:
                exp_path = self.getConfigDir('exp')
                # special cases, e.g. paths:
                if pathsrelativetoexp and key in ('local_exp_rootDir', 'local_exp_subDir') and cfg[key][0] == '.':
                    return os.path.normpath(os.path.join(exp_path, cfg[key]))
                elif pathsrelativetoexp and key in ('local_exp_ignoreDirs'):
                    return [os.path.join(exp_path, ignoreDir) for ignoreDir in cfg[key] ]
                return cfg[key]
        return default

    def getExpConfig(self, path):
        return self.HierarchicalConfigHandler.getConfig(path)

    def loadExpConfig(self, path):
        return self.HierarchicalConfigHandler.loadConfig(path)

    def saveExpConfig(self, path, cfg=None):
        return self.HierarchicalConfigHandler.saveConfig(path, cfg)


    def updateAndPersist(self, path, props=None, update=False):
        """
        If props are given, will update config with these.
        If update is a string, loadExpConfig is called before saving, forwarding update, where:
        - False = do not update, just load the config overriding config in memory if present.
        - 'timestamp' = use lastsaved timestamp to determine which config is main.
        - 'file' = file is updated using memory.
        - 'memory' = memory is updated using file.
        """
        exps = self.HierarchicalConfigHandler.Configs
        cfg = exps.setdefault(path, dict())
        if props:
            cfg.update(props)
        if update:
            self.loadExpConfig(path, doloadparent='never', update=update)
        self.saveExpConfig(path)

    def renameConfigKey(self, oldpath, newpath):
        """
        There is probably not a need to do this for the 'system', 'user', 'exp' dicts;
        only the experiments managed by HierarchicalConfigHandler (i.e. after renaming a folder)
        """
        self.HierarchicalConfigHandler.renameConfigKey(oldpath, newpath)



class HierarchicalConfigHandler(object):
    """
    The point of this handler is to provide the ability of having individual configs in different
    branches of the directory tree.
    E.g., the main config might have
        exp_subentry_regex: (?P<exp_id>RS[0-9]{3})-?(?P<subentry_idx>[\ ]) (?P<subentry_titledesc>.*) \((?P<subentry_date>[0-9]{8})\)
    but in the directory 2012_Aarhus, you might want to use the regex:
        exp_subentry_regex: (?P<subentry_date>[0-9]{8}) (?P<exp_id>RS[0-9]{3})-?(?P<subentry_idx>[\ ]) (?P<subentry_titledesc>.*)

    How to implement/use?
    - As an object; use from parent object.     *currently selected*
    - As a "mixin" class, making methods available to parent.
    - As a parent, deriving from e.g. ExpConfigHandler
    - As a wrapper; instantiates its own ConfigHandler object.

    Notice that I originally intended to always automatically load the hierarchy;
    however, it is probably better to do this dynamically/on request, to speed up startup time.

    """
    def __init__(self, rootdir, ignoredirs=None, doautoloadroothierarchy=False, VERBOSE=0):
        self.VERBOSE = VERBOSE
        self.Configs = dict() # dict[path] --> yaml config
        self.ConfigSearchFn = '.labfluence.yml'
        self.Rootdir = rootdir
        if ignoredirs is None:
            ignoredirs = list() # yes, I could use a set instead, but not natively yaml compatible like list.
        self.Ignoredirs = ignoredirs
        #print "HELLO"
        if doautoloadroothierarchy:
            self.loadRootHierarchy()


    def printConfigs(self):
        for path, cfg in sorted(self.Configs.items()):
            print "{} -> {}".format(path, cfg)


    def loadRootHierarchy(self, rootdir=None, clear=False):
        if clear:
            self.Configs.clear()
        if rootdir is None:
            rootdir = self.Rootdir
        if self.VERBOSE > 3:
            print "Searching for {} from rootdir {}".format(self.ConfigSearchFn, rootdir)
            print "Ignoredirs are: {}".format(self.Ignoredirs)
        for dirpath, dirnames, filenames in os.walk(rootdir):
            if dirpath in self.Ignoredirs:
                del dirnames[:] # Avoid walking into child dirs. Do not use dirnames=list(), as os.walk still refers to the old list.
                print "Ignoring dir (incl children): {}".format(dirpath)
                continue
            if self.VERBOSE > 10:
                print "Searching for {} in {}".format(self.ConfigSearchFn, dirpath)
            if self.ConfigSearchFn in filenames:
                self.loadConfig(dirpath)
#                cfg = yaml.load(open(os.path.realpath(os.path.join(dirpath, self.ConfigSearchFn))) )
#                self.Configs[dirpath] = self.Configs[os.path.realpath(dirpath)] = cfg


    def getConfig(self, path):
        """
        Implemented dynamic read; will try to load if config if not already loaded.
        """
        if path not in self.Configs:
            return self.loadConfig(path)
        else:
            return self.Configs[path]


    def getConfigFileAndDirPath(self, path):
        """
        returns dpath and fpath, where
        fpath = full path to config file
        dpath = directory in which config file resides.
        Always use dpath when searching for a config.
        """
        if not os.path.isabs(path):
            print "Edit, this should probably be concatenated using the exp-data-path;"
            print "doing this will use the current working directory as base path..."
            if self.Rootdir:
                path = os.path.realpath(os.path.join(self.Rootdir, path))
            else:
                path = os.path.abspath(path)
        if os.path.islink(path):
            path = os.path.realpath(path)
        if os.path.isdir(path):
            dpath = path
            fpath = os.path.join(path, self.ConfigSearchFn)
        elif os.path.isfile(path):
            fpath = path
            dpath = os.path.dirname(path)
        else:
            print "\n\nCritical warning: Confighandler.getConfigFileAndDirPath() :: Could not find path:\n{}\n".format(path)
            raise ValueError("Confighandler.getConfigFileAndDirPath() :: Could not find path:\n{}".format(path))
            return (None, None)
        return dpath, fpath


    def loadConfig(self, path, doloadparent='new', update='file'):
        """
        update can be either of False, 'file', 'memory', 'timestamp', where
        - False = do not update, just load the config overriding config in memory if present.
        - 'timestamp' = use lastsaved timestamp to determine which config is main.
        - 'file' = file is updated using memory.
        - 'memory' = memory is updated using file.
        The doloadparent can be either of 'never', 'new', or 'reload', where
        - 'never' means never try to load parent directory config,
        - 'new' means try to load parent config from file if not already loaded; and
        - 'reload' means always try load to parent directory config from file.
        """
        dpath, fpath = self.getConfigFileAndDirPath(path)
        try:
            cfg = yaml.load(open(fpath))
            if update and dpath in self.Configs:
                if update == 'file':
                    cfg.update(self.Configs[dpath])
                    self.Configs[dpath] = cfg
                elif update == 'memory':
                    self.Configs[dpath].update(cfg)
            else:
                self.Configs[dpath] = cfg
        except IOError, e:
            if self.VERBOSE:
                print "HierarchicalConfigHandler.loadConfig() :: Could not open path '{}'".format(path)
                print e
            if os.path.exists(fpath):
                print "HierarchicalConfigHandler.loadConfig() :: Critical WARNING -> Could not open path '{}', but it does exists (maybe directory or broken link); I cannot just create a new config then.".format(path)
                raise IOError(e)
            cfg = self.Configs[dpath] = dict() # Best thing is probably to create a new dict then...
        parentdirpath = os.path.dirname(dpath)
        if (doloadparent == 'new' and parentdirpath not in self.Configs) or doloadparent == 'reload':
            self.loadConfig(parentdirpath, doloadparent='never')
        return cfg


    def saveConfig(self, path, cfg=None, docheck=False, VERBOSE=1):
        dpath, fpath = self.getConfigFileAndDirPath(path)
        # optionally perform a check to see if the config was changed since it was last saved...?
        # either using an external file, a timestampt, or something else...
        if cfg is None:
            if path in self.Configs:
                cfg = self.Configs[path]
            elif dpath in self.Configs:
                cfg = self.Configs[dpath]
            else:
                print "HierarchicalConfigHandler.saveConfig() :: Error, no config found to save for path '{}'".format(fpath)
                return None
        cfg['lastsaved'] = datetime.now()
        try:
            yaml.dump(cfg, open(fpath, 'wb'))
            if VERBOSE:
                print "HierarchicalConfigHandler.saveConfig() :: config saved to file '{}'".format(fpath)
            return True
        except IOError, e:
            if VERBOSE:
                print "HierarchicalConfigHandler.saveConfig() :: Could not open path '{}'".format(path)
                print e

    def renameConfigKey(self, oldpath, newpath):
        """
        Note: This only works for regular dicts;
        for OrderedDict you probably need to rebuild...
        """
        self.Configs[newpath] = self.Configs.pop(oldpath)


    def getPathParents(self, path, version=1, topfirst=True):
        """
        get parents list:
        e.g. for /home/scholer/Documents/, return:
         ['/', '/home', '/home/scholer', '/home/scholer/Documents']
        if topfirst is false, returns the above, reversed.
        """
        if version == 1:
            def getparents(path):
                drive, path = os.path.splitdrive(path)
#                print "getparents iterator started; drive, path = {}, {}".format(drive, path)
                while True:
#                    print "{} iterations for yielding path {}".format(it, path)
                    yield path # yield first, to also return the input dir.
                    parent = os.path.dirname(path)
                    if parent == path:
                        break
                    path = parent
            if topfirst:
                return reversed(list(getparents(path)))
            else:
                return getparents(path)
        paths = list()
        if version == 2:
            for dirname in os_path_split_asunder(path):
                if not paths:
                    paths = [dirname]
                else:
                    paths.append(os.path.join(paths[-1], dirname))
            if topfirst:
                return paths
            else:
                return reversed(paths)
            return paths if topfirst else reversed(paths)
        if version == 3:
            while True:
                paths.append(path)
                path, tail = os.path.split(path)
                if not path and tail:
                    break
            return reversed(paths) if topfirst else paths


    def getEntry(self, key, path, traverseup=True, default=None, doload='new'):
        """
        If traverseup is set to True, then the HierarchicalConfigHandler is allowed to return a
        config value from a config in a parent directory if none is found in the first looked directory.
        doload can be either of 'never', 'new', or 'reload', where
        - 'never' means never try to load from file;
        - 'new' means try to load from file if not already loaded; and
        - 'reload' means always try to load from file.
        """
        if not traverseup:
            if doload in ('new', 'never'):
                if path in self.Configs:
                    return self.Configs[path].get(key)
            if doload == ('reload', 'new'):
                cfg = self.loadConfig(path)
                return cfg.get(key, default) if cfg else default
            elif doload == 'never': # and we have already loaded above...
                return default
        # end if not traverseup; begin traverseup case:
        for cand_path in self.getPathParents(path, topfirst=False):
            if cand_path in self.Configs and key in self.Configs[cand_path]:
                    return self.Configs[cand_path][key]


    def getHierarchicalConfig(self, path, rootdir=None, traverseup=True, default=None):
        if not traverseup:
            if path in self.Configs:
                return self.Configs[path].get(key)
            else:
                return default
        if rootdir is None:
            rootdir = self.Rootdir
        cfg = dict()
        drive, path = os.path.splitdrive(os.path.normpath(path))
        # other alternative, with iterator and os.path.dirname
        def getparents(path):
            drive, path = os.path.splitdrive(path)
            while True:
                print "yielding path {}".format(path)
                yield path
                parent = os.path.dirname(path)
                if parent == path or path == rootdir:
                    break
                path = parent
        paths = list(getparents(path))
        for p in reversed(paths):
            if p in self.Configs:
                cfg.update(self.Configs[p])
        return cfg


    def _getHierarchicalConfig_v2(self, path, rootdir):
            # Alternative, based on path splitting:
        dirs = os_path_split_asunder(path)
        jp = ""
        cfg = dict()
        for dirname in dirs:
            jp = os.path.join(jp, dirname)
            if jp in self.Configs:
                cfg.update(self.Configs[jp])
                if VERBOSE:
                    print "getHierarchicalConfig() :: '{}' found in Configs".format(jp)
            elif self.VERBOSE > 2:
                print "getHierarchicalConfig() :: '{}' not found in Configs".format(jp)
        return cfg

    def _getHierarchicalConfig_v3(self, path, rootdir):
        # other alternative, using os.path.split
        cfg = dict()
        while True:
            if path in self.Configs:
                new = self.Configs[path].copy()
                for k,v in new.items():
                    if k not in cfg: cfg[k]=v
                # Alternatively:
#                new.update(cfg)
#                cfg = new
            path, tail = os.path.split(path)
            if not path and tail:
                break
        return cfg






class PathFinder(object):
    def __init__(self, defaultscheme='default1', npathsdefault=3, VERBOSE=0):
        self.VERBOSE = VERBOSE
        self.Schemes = dict()
        self.Schemedicts = dict()
        self.Defaultscheme = defaultscheme
        self.Npathsdefault = npathsdefault
        # defautl1 scheme: sysconfig in 'config' folder in current dir;
        self._schemeSearch = dict()
        self._schemeSearch['default1'] = dict(sys = ('labfluence_sys.yml', ('.', 'config', '..', '../config') ),
                                              user= ('labfluence_user.yml', (os.path.expanduser(os.path.join('~', '.Labfluence')), ) )
                                              )
        self.mkschemedict()
        if VERBOSE > 3:
            print "PathFinder: Schemedicts -->"
            self.printSchemes()
#        self.Schemes['default1'] = ('config/labfluence_sys.yml', os.path.expanduser(os.path.join('~', '.Labfluence', 'labfluence_user.yml')), None )
#        self.Schemedicts['default1'] = dict(sys='config/labfluence_sys.yml', user=os.path.expanduser(os.path.join('~', '.Labfluence', 'labfluence_user.yml')) )


    def mkschemedict(self):
        for scheme, schemesearch in self._schemeSearch.items():
            self.Schemedicts[scheme] = dict( (cfgtype, self.findPath(filename, dircands)) for cfgtype, (filename, dircands) in schemesearch.items()  )


    def getScheme(self, scheme):
#        return self.Schemes.get(scheme, (None, )*self.Npathsdefault)
        return self.getSchemedict(scheme)

    def getSchemedict(self, scheme):
        return self.Schemedicts.get(scheme, dict())

    def findPath(self, filename, dircands):
        #print "filename '{}', dircands: {}".format(filename, dircands)
        for dircand in dircands:
            if not os.path.isdir(dircand):
                if self.VERBOSE > 2:
                    print "'{}' is not a directory...".format(dircand)
                continue
            dircand = os.path.normpath(dircand)
            if filename in os.listdir(dircand):
                if self.VERBOSE > 1:
                    print "config file found: {}".format(os.path.join(dircand, filename))
                return os.path.join(dircand, filename)
                # could also be allowed to be a glob pattern, and do
                # matches = glob.glob(os.join(dircand, filename))
                # if matches: return matches[0]
        if self.VERBOSE:
            print "Warning, no config found for config filename: '{}'\ntested:{}".format(filename, dircands)

    def printSchemes(self, what='all'):
        for scheme, schemedict in self.Schemedicts.items():
            print "scheme '{}': {}".format(scheme, ", ".join("{}='{}'".format(k,v) for k,v in schemedict.items() ) )



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

    def test_makedata(ch=None):
        if ch is None:
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
        return ch

    def testConfigTypeChain():
        ch2 = ExpConfigHandler('../test/config/system_config.yml', VERBOSE=10)
        print 'ch2.Configs:'
        print ch2.Configs
        ch2.Configs
        ch2.Configs['system']['user_config_path'] = os.path.join(configtestdir, 'user_config.yml')
        ch2.saveConfigs()
        ch3 = ExpConfigHandler('../test/config/system_config.yml')
        print 'ch3.Configs:'
        print ch3.Configs


    def test_save1():
        ch = test_makedata()
        ch.saveConfigs()

    def test_readdata():
        ch.autoReader()
        for cfg in ('system', 'user', 'exp'):
            print "\n\n{} config:".format(cfg)
            print ch.Configs[cfg]


    def testPfAndChain():
        ch3 = ExpConfigHandler( pathscheme='default1', VERBOSE=10 )
        ch3.printConfigs()
        print "\nch3.HierarchicalConfigHandler.Configs:"
        ch3.HierarchicalConfigHandler.printConfigs()
        return ch3

    def testPathFinder1():
        pf = PathFinder(VERBOSE=10)

    def test_addNewConfig():
        ch = ExpConfigHandler( pathscheme='default1', VERBOSE=10 )
        ch.addNewConfig("/home/scholer/Documents/labfluence_data_testsetup/.labfluence/templates.yml", "templates")
        print "ch.get('exp_subentry_template'):"
        print ch.get('exp_subentry_template')

    def test_cfgNewConfigDef():
        ch = ExpConfigHandler( pathscheme='default1', VERBOSE=10 )
        #ch.addNewConfig("/home/scholer/Documents/labfluence_data_testsetup/.labfluence/templates.yml", "templates")
        # I have added the following to the 'exp' config:
        # config_define_new:
        #   templates: ./.labfluence/templates.yml
        print "ch.get('exp_subentry_template'):"
        print ch.get('exp_subentry_template')


    def testExpConfig1():
        ch = ExpConfigHandler(pathscheme='default1')
        print "\nch.HierarchicalConfigHandler.Configs:"
        ch.HierarchicalConfigHandler.printConfigs()
        path = "/home/scholer/Documents/labfluence_data_testsetup/2013_Aarhus/RS102 Strep-col11 TR annealed with biotin"
        cfg = ch.loadExpConfig(path)
        if cfg is None:
            print "cfg is None; using empty dict."
            cfg = dict()
        cfg['test_key'] = datetime.now().strftime("%Y%m%d-%H%M%S") # you can use strptime to parse a formatted date string.
        print "\n\nSaving config for path '{}'".format(path)
        ch.saveExpConfig(path)


    def test_registerEntryChangeCallback():
        print "\n\n>>>>>>>>>>>> starting test_registerEntryChangeCallback(): >>>>>>>>>>>>>>>>>>>>"
        #registerEntryChangeCallback invokeEntryChangeCallback
        ch = ExpConfigHandler(pathscheme='default1')
        ch.setkey('testkey', 'random string')
        def printHej(who, *args):
            print "hi {}, other args: {}".format(who, args)
        def printNej():
            print "no way!"
        def argsAndkwargs(arg1, arg2, hej, der, **kwargs):
            print "{}, {}, {}, {}, {}".format(arg1, arg2, hej, der, kwargs)
        ch.registerEntryChangeCallback('app_active_experiments', printHej, ('morten', ) )
        ch.registerEntryChangeCallback('app_recent_experiments', printNej)
        ch.registerEntryChangeCallback('app_recent_experiments', argsAndkwargs, ('word', 'up'), dict(hej='tjubang', der='sjubang', my='cat') )
        ch.ChangedEntriesForCallbacks.add('app_active_experiments')
        ch.ChangedEntriesForCallbacks.add('app_recent_experiments')

        print "\nRound one:"
        ch.invokeEntryChangeCallback('app_active_experiments')
        ch.invokeEntryChangeCallback() # invokes printNej and argsAndkwargs
        print "\nRound two:"
        ch.invokeEntryChangeCallback('app_active_experiments') # still invokes printHej
        ch.invokeEntryChangeCallback() # does not invoke anything...

        print "\n<<<<<<<<<<<<< completed test_registerEntryChangeCallback(): <<<<<<<<<<<<<<<<<<<<"



    #test_makedata()
    #test_save1()
#    testConfigTypeChain()
    #test_readdata()
    #testPathFinder1()
    #testPfAndChain()
    #testExpConfig1()
    #test_addNewConfig()
    #test_cfgNewConfigDef()
    test_registerEntryChangeCallback()
