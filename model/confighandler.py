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
# pylint: disable-msg=C0103,C0301,C0302,R0902,R0201,W0142,R0913,R0904,W0221
# messages:
#   C0301: Line too long (max 80), R0902: Too many instance attributes (includes dict())
#   C0302: too many lines in module; R0201: Method could be a function; W0142: Used * or ** magic
#   R0904: Too many public methods (20 max); R0913: Too many arguments;
#   W0221: Arguments differ from overridden method
"""
Confighandler module includes all logic to read, parse and save config and

"""

import yaml
import os
import os.path
from datetime import datetime
import collections
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)
from Tkinter import TclError

# from http://stackoverflow.com/questions/4579908/cross-platform-splitting-of-path-in-python
def os_path_split_asunder(path, debug=False):
    """
    Can be used to split directory paths into individual parts.
    """
    parts = []
    while True:
        newpath, tail = os.path.split(path)
        if debug:
            logger.debug(repr(path), (newpath, tail) )
        if newpath == path:
            assert not tail
            if path:
                parts.append(path)
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

        Defining a new config can be done in a yaml as:
        config_define_new = {<cfgtype> : <path>}
        where path if relative, is loaded relative to the current config path.

    """

    def __init__(self, systemconfigfn=None, userconfigfn=None):
        self.VERBOSE = 0
        self.ConfigPaths = OrderedDict()
        self.Configs = OrderedDict()
        # For retrieving paths via config entries...
        self.Config_path_entries = dict(system='system_config_path', user='user_config_path')
        # Config_path_entries is used to map config entries to a config type,
        # for instance, with the setting above, the config key "system_config_path" can be used to
        # specify a file path for the 'system' config.
        self.ConfigPaths['system'], self.ConfigPaths['user'] = systemconfigfn, userconfigfn
        self.Configs['system'] = dict()
        self.Configs['user'] = dict()
        self.Singletons = dict() # dict for singleton objects; makes it easy to share objects across application objects that already have access to the confighandler singleton.
        self.DefaultConfig = 'user' # which config to save new config items to.
        self.AutoreadNewFnCache = dict() #list()
        self.ReadFiles = set() # which files have been read.
        self.ReadConfigTypes = set() # which config types have been read. Used to avoid circular imports.
        self.Autosave = False # if set to true, will automatically save a config to file after
        self.CheckFileTimeBeforeSave = False # (not implemented) if set to True, will check the file's changetime before overwriting.
        self.CheckFileTimeAgainstCache = False # (not implemented) if set to True, will check
        # a config file's last-modified time status before returning the cached value.
        # If the file's last-modified time is later than the cache's last-save time, the
        # config is read from file and used to update the cache. If self.Autosave is True,
        # the updated config is then saved to file.

        # Setting either of these to true requires complete trust in the putative users:
        self.AllowChainToSameType = True # If one system config file has been loaded, allow loading another?
        self.AllowNextConfigOverrideChain = True # Similar, but does not alter the original config filepath.
        self.AllowNewConfigDefinitions = True   # Allow one config to define a new config.
        self.AllowCfgtypeOverwrite = False

        # Attributes for the callback system:
        self.EntryChangeCallbacks = dict()   # dict with: config_key : <list of callbacks>
        self.ChangedEntriesForCallbacks = set() # which config keys has been changed.
        logger.debug("ConfigPaths : %s", self.ConfigPaths)


    def getSingleton(self, key):
        """
        Return a registrered singleton by key, e.g.:
            getSingleton('ui') -> return registrered UI
        """
        return self.Singletons.get(key)

    def setSingleton(self, key, value):
        """
        Set application-wide singleton by key, e.g.:

        """
        if key in self.Singletons:
            logger.info("key '%s' already in self.Singletons, overriding with new singleton object '%s'.", key, value)
        self.Singletons[key] = value


    def addNewConfig(self, inputfn, cfgtype, rememberpath=True):
        """
        Add a new config to the list of configs, e.g.:
            addNewConfig('config/test_config.yml', 'test')
        """
        if cfgtype in set(self.Configs).union(self.ConfigPaths) and not self.AllowCfgtypeOverwrite:
            logger.warning("addNewConfig() :: cfgtype already present in configs and overwrite not allowed; aborting...")
            return
        if rememberpath:
            self.ConfigPaths[cfgtype] = inputfn
        self.Configs[cfgtype] = dict()
        self.readConfig(inputfn, cfgtype)


    def getConfigPath(self, what='all', aslist=False):
        """
        Get the path for a particular config, has three return values:
            getConfigPath('all') -> returns self.ConfigPaths.values()
            getConfigPath('sys') -> return self.ConfigPaths['sys']
            getConfigPath('sys', aslist=True) -> return ( self.ConfigPaths['sys'], ) tuple.
        """
        if what == 'all':
            return self.ConfigPaths.values()
        elif aslist:
            return self.ConfigPaths.get(what, None),
        else:
            return self.ConfigPaths.get(what, None)


    def getConfig(self, what='all', aslist=False):
        """
        Returns the config for a particular config type.
        Five return behaviours:
        0) getConfig('combined') -> returns the combined, effective config for all configs.
        1) getConfig('combined') -> Return 1-element list with the combined, effective config as sole element.
        2) getConfig('sys') -> returns the 'sys' config.
        3) getConfig('all') -> returns self.Configs.values() list.
        4) getConfig('sys', aslist=True) -> returns a tuple with the 'sys' config as sole element.
        """
        if what == 'combined':
            combined = dict()
            for config in self.Configs.values():
                combined.update(config)
            if aslist:
                return (combined, )
            else:
                return combined
        elif what == 'all':
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

    def setdefault(self, key, value=None, autosave=None):
        """
        Mimicks dict.setdefault, will return configentry <key>.
        Use as:
            setdefault('username', 'niceuser')
        If configentry 'username' is not set in any of the loaded configs,
        a new configentry with key 'username' and value 'niceuser' will be
        set, using the default config.
        If a configentry already exists, will simply return that value,
        without setting anything.
        """
        if autosave is None:
            autosave = self.Autosave
        for config in self.Configs.values():
            if key in config:
                return config[key]
        # If key is not found, set default in default config (usually 'user')
        val = self.Configs[self.DefaultConfig].setdefault(key, value)
        self.ChangedEntriesForCallbacks.add(key)
        if autosave:
            self.saveConfig(self.DefaultConfig)
        return val

    def set(self, key, value):
        """ Alias for setkey (I can never remember that one...)
        """
        self.setkey(key, value)

    def setkey(self, key, value, cfgtype=None, check_for_existing_entry=True, autosave=None):
        """
        Sets a config key.
        If key is already set in one of the main configs, and check_for_existing_entry
        is set to True then update the config where entry is found. (RECOMMENDED)
        If key is not already set, store in config specified by <cfgtype> arg.
        If cfgtype is not provided, use default config (type), e.g. 'user'.

        PLEASE NOTE THAT setkey IS DIFFERENT FROM A NORMAL set METHOD, IN THAT setkey()
        returns the cfgtype where the key was persisted, e.g. 'user'.
        """
        if autosave is None:
            autosave = self.Autosave
        if check_for_existing_entry:
            #for cfgtyp, config in self.Configs.items():
            #    if key in config:
            #        config[key] = value
            #        return cfgtyp
            cfgtype = next( (cfgtype for cfgtype, config in self.Configs.items()
                                if key in config),
                            self.DefaultConfig)
        else:
            # If key is not found in any of the existing configs, set in default config type:
            if cfgtype is None:
                cfgtype = self.DefaultConfig
        # Set config key to value:
        try:
            self.Configs.get(cfgtype)[key] = value
        except TypeError:
            logger.warning("TypeError when trying to set key '%s' in cfgtype '%s', self.Configs.get('%s') returned: %s, self.Configs.keys(): %s",
                           key, cfgtype, cfgtype, self.Configs.get(cfgtype), self.Configs.keys())
            return False
        self.ChangedEntriesForCallbacks.add(key)
        logger.debug("cfgtype:key=type(value) | %s:%s=%s", cfgtype, key, type(value))
        if autosave:
            logger.debug("Autosaving config: %s", cfgtype)
            self.saveConfig(cfgtype)
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
            logger.debug("popped value '%s' from config '%s'. res is now: '%s'", val, cfgtype, res)
            if val and not check_all_configs:
                break
        return res

    def readConfig(self, inputfn, cfgtype='user'):
        """
        Reads a (yaml-based) configuration file from inputfn, loading the
        content into the config given by cfgtype.
        Note: This is a relatively low-level method.
        """
        VERBOSE = self.VERBOSE
        if cfgtype is None:
            cfgtype = self.Configs.values()[0]
        if not self.AllowChainToSameType and cfgtype in self.ReadConfigTypes:
            return
        if inputfn in self.ReadFiles:
            logger.warning("WARNING, file already read: %s", inputfn)
            return
        try:
            newconfig = yaml.load(open(inputfn)) # I dont think this needs with... or open/close logic.
        except IOError as e:
            logger.warning("readConfig() :: ERROR, could not load yaml config, cfgtype: %s, error: %s", cfgtype, e)
            return False
        self.ReadConfigTypes.add(cfgtype)
        self.ReadFiles.add(inputfn) # To avoid recursion...
        self.Configs[cfgtype].update(newconfig)
        if VERBOSE > 3:
            logger.info("readConfig() :: New '%s'-type config loaded:", cfgtype)
            logger.debug("Loaded config is: %s", newconfig)
            logger.debug("readConfig() :: Updated main '%s' config to be: %s", cfgtype, self._printConfig(self.Configs[cfgtype]) )
        if "next_config_override_fn" in newconfig and self.AllowNextConfigOverrideChain:
            # the next_config_override_fn are read-only, but their content will be persisted to the main configfile.when saved.
            if VERBOSE:
                logger.debug("readConfig() :: Reading config defined by next_config_override_fn entry: %s", newconfig["next_config_override_fn"])
            self.readConfig(newconfig["next_config_override_fn"], cfgtype)
        if "config_define_new" in newconfig and self.AllowNewConfigDefinitions:
            for newtype, newconfigfn in newconfig["config_define_new"].items():
                if not os.path.isabs(newconfigfn):
                    # isabs basically just checks if path[0] == '/'...
                    newconfigfn = os.path.normpath(os.path.join(os.path.dirname(inputfn), newconfigfn))
                logger.info("readConfig: Adding config-defined config '%s' using filepath '%s'", newtype, newconfigfn)
                self.addNewConfig(newconfigfn, newtype)

        # Inputting configs through Config_path_entries:
        reversemap = dict( (val, key) for key, val in self.Config_path_entries.items() )
        for key in set(newconfig.keys()).intersection(self.Config_path_entries.values()):
            if VERBOSE > 2:
                logger.debug("Found the following path_entries key '%s' in the new config: %s", key, newconfig[key])
            self.readConfig(newconfig[key], reversemap[key])
            self.AutoreadNewFnCache[reversemap[key]] = newconfig[key]
        return newconfig


    def autoRead(self):
        """
        autoRead is used to read all config files defined in self.ConfigPaths.
        autoRead and the underlying readConfig() methods uses AutoreadNewFnCache attribute to
        keep track of which configs has been loaded and make sure to avoid cyclic config imports.
        (I.e. avoid the situation where ConfigA says "load ConfigB" and ConfigB says "load ConfigA).
        """
        logger.debug("ConfigPaths: %s", self.ConfigPaths.items())
        for (cfgtype, inputfn) in self.ConfigPaths.items():
            if inputfn:
                logger.debug("Will read config '%s' to current dict: %s", inputfn, cfgtype)
                self.readConfig(inputfn, cfgtype)
                logger.debug("Finished read config '%s' to dict: %s", inputfn, cfgtype)
            logger.debug("Autoreading done, chained with new filenames: %s", self.AutoreadNewFnCache)
        self.ConfigPaths.update(self.AutoreadNewFnCache)
        self.AutoreadNewFnCache.clear()
        logger.debug("Updated ConfigPaths: %s", self.ConfigPaths.items())

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
        logger.warning("saveConfigForEntry invoked with key '%s', but key not found in any of the loaded configs (%s)!",
                       key, ",".join(self.Configs))

    def saveConfigs(self, what='all'):
        """
        Persist config specified by what argument.
        Use as:
            saveConfigs('all') --> save all configs (default)
            saveConfigs('sys') --> save the 'sys' config. (or use the simpler: saveConfig(cfgtype))
            saveConfigs(('sys', 'exp') --> save the 'sys' and 'exp' config.
        """
        logger.info("saveConfigs invoked with configtosave '%s'", what)
        for cfgtype, outputfn in self.ConfigPaths.items():
            if (what=='all' or cfgtype in what or cfgtype==what):
                if outputfn:
                    logger.info("Saving config '%s' to file: %s", cfgtype, outputfn)
                    self._saveConfig(outputfn, self.Configs[cfgtype])
                else:
                    logger.info("No filename specified for config '%s'", cfgtype)
            else:
                logger.debug("configtosave '%s' not matching cfgtype '%s' with outputfn '%s'", what, cfgtype, outputfn)

    def saveConfig(self, cfgtype):
        """
        Saves a particular config.
        saveConfig('system') --> save the 'system' config.
        """
        if cfgtype not in self.ConfigPaths or cfgtype not in self.Configs:
            logger.warning("cfgtype '%s' not found in self.Configs or self.ConfigPaths, aborting...")
            return False
        config = self.Configs[cfgtype]
        outputfn = self.ConfigPaths[cfgtype]
        logger.debug("Saving config %s using outputfn %s", cfgtype, outputfn)
        self._saveConfig(outputfn, config)
        return True


    def _saveConfig(self, outputfn, config):
        """
        For internal use; does the actual saving of the config.
        Can be easily mocked or overridden by fake classes to enable safe testing environments.
        """
        try:
            yaml.dump(config, open(outputfn, 'wb'), default_flow_style=False)
            logger.info("Config saved to file: %s", outputfn)
            return True
        except IOError, e:
            # This is to be expected for the system config...
            logger.warning("Could not save config to file '%s', error raised: %s", outputfn, e)


    def _printConfig(self, config, indent=2):
        """
        Returns a pretty string representation of a config.
        """
        return "\n".join( u"{indent}{k}: {v}".format(indent=' '*indent, k=k, v=v) for k, v in config.items() )


    def printConfigs(self, cfgtypestoprint='all'):
        """
        Pretty print of all configs specified by configstoprint argument.
        Default is 'all' -> print all configs.
        """
        for cfgtype, outputfn in self.ConfigPaths.items():
            if (cfgtypestoprint=='all' or cfgtype in cfgtypestoprint or cfgtype==cfgtypestoprint):
                print u"\nConfig '{}' in file: {}".format(cfgtype, outputfn)
                print self._printConfig(self.Configs[cfgtype])
        return "\n".join( "\n".join([ u"\nConfig '{}' in file: {}".format(cfgtype, outputfn),
                                      self._printConfig(self.Configs[cfgtype]) ])
                          for cfgtype,outputfn in self.ConfigPaths.items()
                          if (cfgtypestoprint=='all' or cfgtype in cfgtypestoprint or cfgtype==cfgtypestoprint)
                         )


    def getConfigDir(self, cfgtype='user'):
        """
        Returns the directory of a particular configuration (file); defaulting to the 'user' config.
        Valid arguments are: 'system', 'user', 'exp', etc.
        """
        cfgpath = self.getConfigPath(cfgtype)
        if cfgpath:
            return os.path.dirname(self.getConfigPath(cfgtype))
        else:
            logger.info("ConfigDir requested for config '%s', but that is not specified ('%s')", cfgtype, cfgpath)


    def registerEntryChangeCallback(self, configentry, function, args=None, kwargs=None, pass_newvalue_as=False):
        """
        Registers a callback for a particular entry (name).
        Actually, this can be used as a simple, general-purpose callback manager, across all objects
        that have access to the Confighandler singleton. The 'configentry' key does not have to
        correspond to an actual configentry, it can just be a name that specifies that particular
        callback by concention.
        Of cause, this is not quite as powerfull as using qt's QObject and signal connections and
        emitting, but is is ok for simple callbacks, especially for singleton-like objects and variables.
        (see http://pyqt.sourceforge.net/Docs/PyQt4/qobject.html for more info on QObject's abilities.)
        Note: I see no reason to add a 'registerConfigChangeCallback' method.
        Although this could provide per-config callbacks (e.g. an experiment that could subscribe to
        changes only for that experiment), I think it is better to code for this situation directly.

        If a callback sets pass_newvalue_as=<key>, this will cause the new config value to be passed to the
        callback in the kwargs, as:
            kwargs['pass_newvalue_as'] = new_configentry_value
        Note that there is currently no guarantee that whoever calls invoke
            invokeEntryChangeCallback(self, configentry=None, new_configentry_value=None)
        will actually set the new_configentry_value. I might add a 'if-set', option,
        but since None is also commonly used as a 'not specified' value for kwargs, I think it is ok.

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
        elif not isinstance(args, collections.Iterable):
            logger.debug("registerEntryChangeCallback received 'args' argument with non-iterable value '%s', will convert to tuple.", args)
            args = (args, )
        if kwargs is None:
            kwargs = dict()
        # I would have liked this to be a set, but hard to implement set for dict-type kwargs and no frozendict in python2.
        # Just make sure not to register the same callback twice.
        self.EntryChangeCallbacks.setdefault(configentry, list()).append( (function, args, kwargs, pass_newvalue_as) )
        logger.debug("Registrered callback for configentry '%s': %s(*%s, **%s) with pass_newvalue_as=%s", configentry, function, args, kwargs, pass_newvalue_as)
        # I could also have implemented as dict based on the function is hashable, e.g.:
        #self.EntryChangeCallbacks.setdefault(configentry, dict()).set(function, (args, kwargs) )
        # and invoke with:
        # for function, (args, kwargs) in self.EntryChangeCallbacks[configentry].items():
        #     function(*args, **kwargs)

    def unregisterEntryChangeCallback(self, configentries=None, function=None, args=None, kwargs=None):
        """
        Notice that a function may be registered multiple times.
        self.EntryChangeCallbacks[configentry] = list of (function, args, kwargs) tuples.

        The unregister call is powerful and generic: callbacks can be removed based not only on the function,
        but also on the arguments passed to the function as well as the configentries.
        This means that, for instance, all callbacks that receives the keyword arguments {'hello': 'there'}
        can be removed by calling:
            unregisterEntryChangeCallback(configentries=None, function=None, args=None, kwargs={'hello': 'there'} )
        This is because all callbacks satisfying the filter:
            all( criteria in (None, callbacktuple[i]) for i,criteria in enumerate( (function, args, kwargs) ) )
        will be removed.
        Thus, if unregisterEntryChangeCallback() is called without arguments,
        ALL REGISTRERED CALLBACKS WILL BE REMOVED!
        """
        if all(a is None for a in (function, args, kwargs) ):
            if configentries is None:
                logger.warning("NOTICE: unregisterEntryChangeCallback called without any arguments. All registrered callbacks will be removed.")
            else:
                logger.info("Removing all registrered callbacks for configentries '%s' - since unregisterEntryChangeCallback was called with configentries as only argument.", configentries)
        if configentries is None:
            configentries = self.EntryChangeCallbacks.keys()
        elif isinstance(configentries, basestring):
            configentries = (configentries, )

        for configentry in configentries:
            #removelist = filter(callbackfilter, self.EntryChangeCallbacks[configentry])
            # Changed, now using generator alternative instead of filter builtin (which is in bad
            # standing with the BDFL, http://www.artima.com/weblogs/viewpost.jsp?thread=98196)
            removelist = (  callbacktuple for callbacktuple in self.EntryChangeCallbacks[configentry]
                            if all( criteria in (None, callbacktuple[i])
                                   for i, criteria in enumerate((function, args, kwargs)) )
                         )
            logger.debug("Removing callbacks from self.EntryChangeCallbacks[%s]: %s", configentry, removelist)
            for callbacktuple in removelist:
                self.EntryChangeCallbacks[configentry].remove(callbacktuple)


    def invokeEntryChangeCallback(self, configentry=None, new_configentry_value=None):
        """
        Simple invokation of registrered callbacks.
        If configentry is provided, only callbacks registrered to that entry will be invoked.
        If configentry is None (default), all keys registrered in self.ChangedEntriesForCallbacks
        will have their corresponding callbacks invoked.
        When a configentry has had its callbacks invoked, it will be unregistrered from
        self.ChangedEntriesForCallbacks.

        ## Done: implement try clause in confighandler.invokeEntryChangeCallback and
        ## automatically unregister failing calls.
        ## Done: Implement ability to route the newvalue parameter to the callbacks.
        ##       As it is now, each of the callbacks have to invoke self.Confighandler.get(configkey)
        ## -fix: The new value is passed to callback as keyword argument 'pass_newvalue_as'.
        ##       The new value can also be injected by setting new_configentry_value
        ##       as kwargument when invoking this method (invokeEntryChangeCallback)
        ##
        """
        if configentry:
            if configentry in self.EntryChangeCallbacks:
                failedfunctions = list()
                for function, args, kwargs, pass_newvalue_as in self.EntryChangeCallbacks[configentry]:
                    if pass_newvalue_as:
                        kwargs[pass_newvalue_as] = new_configentry_value
                    logger.debug("invoking callback for configentry '%s': %s(*%s, **%s)", configentry, function, args, kwargs)
                    try:
                        function(*args, **kwargs)
                    except TclError as e:
                        logger.error("Error while invoking callback for configentry '%s': %s(*%s, **%s): %s",
                                     configentry, function, args, kwargs, e)
                        logger.info("Marking callback as failed: '%s': %s(*%s, **%s)", configentry, function, args, kwargs)
                        failedfunctions.append(function)
                for function in failedfunctions:
                    logger.info("Unregistrering callbacks for function: %s(...)", function)
                    self.unregisterEntryChangeCallback(function=function)
                # Erase this entry if registrered here. (discard does not do anything if the item is not a member of the set)
                self.ChangedEntriesForCallbacks.discard(configentry)
            else:
                logger.debug("invokeEntryChangeCallback called with configentry '%s', but no callbacks are registrered for that entry...", configentry)
        elif self.ChangedEntriesForCallbacks:
            # The ChangedEntriesForCallbacks will change during iteration, so using a while rather than for loop:
            while True:
                try:
                    entry = self.ChangedEntriesForCallbacks.pop() # Raises KeyError when dict is empty.
                    logger.debug("Popped configentry '%s' from ChangedEntriesForCallbacks...", configentry)
                    self.invokeEntryChangeCallback(entry)
                except KeyError: # raised when pop on empty set.
                    break



class ExpConfigHandler(ConfigHandler):
    """
    ExpConfigHandler adds four functionalities:
    1)  It enables a default 'exp' config, specifying an 'exp_config_path' config key,
        which specifies an 'exp' config file to be read.
    2)  It implements "Hierarchical" path-based configurations,
        by relaying many "path augmented" calls to a HierarchicalConfigHandler object.
        This makes it possible to have different configs for different experiment folders,
        i.e. for different years or for different projects or different experiments.
        In other words, if calling get(key=<a config key>, path=<dir>) with a <dir> value of
        '2013/ProjectB/ExpAB123 Important experiment v11', then the search path for a config with key <a config key>
        will be:
        1) '2013/ProjectB/ExpAB123 Important experiment v11/.labfluence.yml'
        2) '2013/ProjectB/.labfluence.yml'
        3) '2013/.labfluence.yml'
        4) Search the already loaded config types in order, e.g. 4.1) 'exp', 4.2) 'user', 4.3) 'sys'.
    3)  Relative experiment paths will be returned as absolute paths, i.e. for the config keys:
        if local_exp_rootDir = '2013' --> return os.path.join(exp_path, cfg[key]
        and equivalent for local_exp_subDir and local_exp_ignoreDirs (which is a list of paths).
    4)  It employs a PathFinder to automatically locate config paths by searching local directories,
        according to a specified path scheme.
        The default path scheme, 'default1', will e.g. search for the user config in '~/.Labfluence/',
        while the path scheme 'test1' will search for both 'sys' and 'user' configs
        in the relative directory 'setup/configs/test_configs/local_test_setup_1'.

    """
    def __init__(self, systemconfigfn=None, userconfigfn=None, expconfigfn=None,
                readfiles=True, pathscheme='default1', hierarchy_rootdir_config_key='local_exp_rootDir',
                enableHierarchy=True, hierarchy_ignoredirs_config_key='local_exp_ignoreDirs'):
        self.Pathfinder = PathFinder()
        pschemedict = self.Pathfinder.getScheme(pathscheme) if pathscheme else dict()
        systemconfigfn = systemconfigfn or pschemedict.get('sys')
        userconfigfn = userconfigfn or pschemedict.get('user')
        expconfigfn = expconfigfn or pschemedict.get('exp')
        # init super:
        ConfigHandler.__init__(self, systemconfigfn, userconfigfn)
        self.Configs['exp'] = dict()
        self.ConfigPaths['exp'] = expconfigfn
        self.Config_path_entries['exp'] = "exp_config_path"
        if readfiles:
            logger.debug("__init()__ :: autoreading..." )
            self.autoRead()
        if enableHierarchy and hierarchy_rootdir_config_key:
            rootdir = self.get(hierarchy_rootdir_config_key)
            ignoredirs = self.get(hierarchy_ignoredirs_config_key)
            logger.debug("Enabling HierarchicalConfigHandler with rootdir: %s", rootdir)
            if rootdir:
                self.HierarchicalConfigHandler = HierarchicalConfigHandler(rootdir, ignoredirs)
            else:
                logger.info("rootdir is %s; hierarchy_rootdir_config_key is %s; configs are (configpaths): %s",
                    rootdir, hierarchy_rootdir_config_key, self.ConfigPaths )

        else:
            self.HierarchicalConfigHandler = None
        logger.debug("ConfigPaths : %s", self.ConfigPaths)


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
        """
        Returns a hierarchically-determined config, based on a path and rootdir.
        Relays to HierarchicalConfigHandler.getHierarchicalConfig
        """
        return self.HierarchicalConfigHandler.getHierarchicalConfig(path, rootdir=rootdir)


    def get(self, key, default=None, path=None, pathsrelativetoexp=True):
        """
        Simulated the get method of a dict.
        If path is provided, will search HierarchicalConfigHandler for a matching config before
        resolving to the 'main' configs.
        """
        if path and self.HierarchicalConfigHandler:
            val = self.getHierarchicalEntry(key, path)
            # perhaps raise a KeyError if key is not found in the hierarchical confighandler;
            # None could be a valid value in some cases...?
            if val is not None:
                return val
        # Optimized, and accounting for the fact that later added cfgs overrides the first added
        for cfg in reversed(self.Configs.values()):
            if key in cfg:
                ## special cases, e.g. paths: ##
                # Case 1, config keys specifying a single path:
                if pathsrelativetoexp and key in ('local_exp_rootDir', 'local_exp_subDir') and cfg[key][0] == '.':
                    exp_path = self.getConfigDir('exp')
                    if exp_path:
                        return os.path.normpath(os.path.join(exp_path, cfg[key]))
                # Case 2, config keys specifying a list of paths:
                elif pathsrelativetoexp and key in ('local_exp_ignoreDirs'):
                    exp_path = self.getConfigDir('exp')
                    return [os.path.join(exp_path, ignoreDir) for ignoreDir in cfg[key] ]
                return cfg[key]
        return default

    def getExpConfig(self, path):
        """
        Returns a hierarchically determined experiment config.
        Similar to getConfig, but will not fall back to use the standard
        (non-hierarchical) configs.
        """
        return self.HierarchicalConfigHandler.getConfig(path)

    def loadExpConfig(self, path, doloadparent=None, update=None):
        """
        Relay to self.HierarchicalConfigHandler.loadConfig(path)
        """
        return self.HierarchicalConfigHandler.loadConfig(path, doloadparent, update)

    def saveExpConfig(self, path, cfg=None):
        """
        Relay to self.HierarchicalConfigHandler.saveConfig(path)
        """
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
    r"""
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
        """
        Make a pretty string representation of the loaded configs for e.g. debugging.
        """
        return "\n".join( u"{} -> {}".format(path, cfg) for path, cfg in sorted(self.Configs.items())  )

    def loadRootHierarchy(self, rootdir=None, clear=False):
        """
        Load all labfluence config/metadata files in the directory hierarchy using self.Rootdir as base.
        """
        if clear:
            self.Configs.clear()
        if rootdir is None:
            rootdir = self.Rootdir
        if self.VERBOSE or True:
            logger.debug("Searching for %s from rootdir %s; ignoredirs are: %s", self.ConfigSearchFn, rootdir, self.Ignoredirs)
        for dirpath, dirnames, filenames in os.walk(rootdir):
            if dirpath in self.Ignoredirs:
                del dirnames[:] # Avoid walking into child dirs. Do not use dirnames=list(), as os.walk still refers to the old list.
                logger.debug("Ignoring dir (incl children): %s", dirpath)
                continue
            if self.VERBOSE > 3:
                logger.debug("Searching for %s in %s", self.ConfigSearchFn, dirpath)
            if self.ConfigSearchFn in filenames:
                self.loadConfig(dirpath)


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
            logger.debug("Edit, this should probably be concatenated using the exp-data-path;"+\
                         "doing this will use the current working directory as base path...")
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
            logger.error("Critical warning: Confighandler.getConfigFileAndDirPath() :: Could not find path: '%s'", path)
            raise ValueError(u"Confighandler.getConfigFileAndDirPath() :: Could not find path:\n{}".format(path))
        return dpath, fpath


    def loadConfig(self, path, doloadparent=None, update=None):
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
        if doloadparent is None:
            doloadparent = 'new'
        if update is None:
            update = 'file'
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
                logger.warning("HierarchicalConfigHandler.loadConfig() :: Could not open path '%s'. Error is: %s", path, e)
            if os.path.exists(fpath):
                logger.error("""HierarchicalConfigHandler.loadConfig() :: Critical WARNING -> Could not open path '%s',
                             but it does exists (maybe directory or broken link);
                             I cannot just create a new config then.""", path)
                raise IOError(e)
            cfg = self.Configs[dpath] = dict() # Best thing is probably to create a new dict then...
        parentdirpath = os.path.dirname(dpath)
        if (doloadparent == 'new' and parentdirpath not in self.Configs) or doloadparent == 'reload':
            self.loadConfig(parentdirpath, doloadparent='never')
        return cfg


    def saveConfig(self, path, cfg=None, docheck=False):
        """
        Save config <cfg> to path <path>.
        If cfg is not given, the method will check if a config from <path> was
        already loaded. In that case, that config will be saved to path.
        docheck argument can be used to force checking that the file provided by
        <path> has not been updated.
        Returns True if successful and False otherwise.
        """
        dpath, fpath = self.getConfigFileAndDirPath(path)
        # optionally perform a check to see if the config was changed since it was last saved...?
        # either using an external file, a timestampt, or something else...
        if cfg is None:
            if path in self.Configs:
                cfg = self.Configs[path]
            elif dpath in self.Configs:
                cfg = self.Configs[dpath]
            else:
                logger.warning("HierarchicalConfigHandler.saveConfig() :: Error, no config found to save for path '%s'", fpath)
                return None
        if docheck:
            fileconfig = yaml.load(cfg, open(fpath))
            if fileconfig.get('lastsaved'):
                if not cfg.get('lastsaved') or cfg.get('lastsaved') < fileconfig['lastsaved']:
                    logger.warning("Attempted to save config to path '%s', but checking the existing file\
                                   reveiled that the existing config has been updated (from another location). Aborting...")
                    return False
        cfg['lastsaved'] = datetime.now()
        try:
            yaml.dump(cfg, open(fpath, 'wb'))
            logger.debug("HierarchicalConfigHandler.saveConfig() :: config saved to file '%s'", fpath)
            return True
        except IOError, e:
            logger.warning("HierarchicalConfigHandler.saveConfig() :: Could not open path '%s'. Error is: %s", path, e)
            return False


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
        Implemented in three different ways, determined by 'version'.
        """
        if version == 1:
            def getparents(path):
                """
                A generator, that returns the path and its parents
                """
                _, path = os.path.splitdrive(path)
                while True:
                    yield path # yield first, to also return the input dir.
                    parent = os.path.dirname(path)
                    if parent == path:
                        break
                    path = parent
            if topfirst:
                return reversed(list(getparents(path)))
            else:
                return getparents(path)
        # other implementations:
        #paths = list()
        #if version == 2:
        #    for dirname in os_path_split_asunder(path):
        #        if not paths:
        #            # Set the first element in paths.
        #            paths = [dirname]
        #        else:
        #            paths.append(os.path.join(paths[-1], dirname))
        #    if topfirst:
        #        return paths
        #    else:
        #        return reversed(paths)
        #    return paths if topfirst else reversed(paths)
        #if version == 3:
        #    while True:
        #        paths.append(path)
        #        path, tail = os.path.split(path)
        #        if not path and tail:
        #            break
        #    return reversed(paths) if topfirst else paths


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
        """
        Returns a config in the directory hierarchy, starting with path.
        If rootdir is not given, self.Rootdir is used.
        If traverseup is True (default), the search will progress upwards from path
        until a config file is found or the rootdir is reached.
        Will return default if no config were found.
        """
        if not traverseup:
            if path in self.Configs:
                return self.Configs[path]
            else:
                return default
        if rootdir is None:
            rootdir = self.Rootdir
        cfg = dict()
        _, path = os.path.splitdrive(os.path.normpath(path))
        # other alternative, with iterator and os.path.dirname
        def getparents(path):
            """
            Using the generator implementation defined in getPathParents(..., version=1)
            """
            _, path = os.path.splitdrive(path)
            while True:
                logger.debug("yielding path %s", path)
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



class PathFinder(object):
    """
    Class used to find config files.
    Takes a 'defaultscheme' argument in init.
    This can be used to easily change the behavior of the object.
    I.e., if 'defaultscheme' is st to 'default1', then the following search paths are used:
    - sys config: '.', './config/', './setup/default/', '..', '../config' (all relative to the current working directory)
    - user config: '~/.Labfluence'.
    - exp config: path should be defined in the user config.
    If defaultscheme='test1':
    - sys config: setup/configs/test_configs/local_test_setup_1
    """
    def __init__(self, defaultscheme='default1', npathsdefault=3, VERBOSE=0):
        self.VERBOSE = VERBOSE
        self.Schemes = dict()
        self.Schemedicts = dict()
        self.Defaultscheme = defaultscheme
        self.Npathsdefault = npathsdefault
        # defautl1 scheme: sysconfig in 'config' folder in current dir;
        self._schemeSearch = dict()
        # notation is:
        # configtype : (<filename to look for>, (list of directories to look in))
        self._schemeSearch['default1'] = dict(sys = ('labfluence_sys.yml',  ('.', 'config', 'setup/configs/default/') ),
                                              user= ('labfluence_user.yml',
                                                     (os.path.expanduser(os.path.join('~', dir)) for dir in
                                                      ('.labfluence', '.Labfluence', os.path.join('.config', '.labfluence') ) )
                                                    )
                                              )
        self._schemeSearch['test1'] =  dict(  sys = ('labfluence_sys.yml',  ('setup/configs/test_configs/local_test_setup_1',) ),
                                              user= ('labfluence_user.yml', ('setup/configs/test_configs/local_test_setup_1', ) )
                                              )

        self._schemeSearch['install'] =  dict(  sys = ('labfluence_sys.yml',  ('setup/configs/new_install/',) ),
                                                user= ('labfluence_user.yml', ('setup/configs/new_install/', ) ),
                                                exp = ('labfluence_exp.yml', ('setup/configs/new_install/', ) )
                                              )

        #self.mkschemedict() # I've adjusted the getScheme() method so that this will happen on-request.
        logger.debug("%s initialized, self.Defaultscheme='%s'", self.__class__.__name__, self.Defaultscheme )

    def mkschemedict(self):
        """
        This will find all configs for all schemes defined in _schemeSearch.
        It might be a bit overkill to do this at every app start.
        Could be optimized so you only find the config filepaths when a particular scheme is requested.
        """
        for scheme, schemesearch in self._schemeSearch.items():
            self.Schemedicts[scheme] = dict( (cfgtype, self.findPath(filename, dircands)) for cfgtype, (filename, dircands) in schemesearch.items()  )

    def getScheme(self, scheme=None, update=True):
        """
        I have updated this method, so instead of invoking mkschemedict() which will find configs for *all* schemes defined in _schemeSearch,
        it will only make a scheme for the specified scheme.
        Note that this is designed to fail with a KeyError if scheme is not specified in self._schemeSearch.
        """
        if scheme is None:
            scheme = self.Defaultscheme
        if update:
            self.Schemedicts[scheme] = dict( (cfgtype, self.findPath(filename, dircands)) for cfgtype, (filename, dircands) in self._schemeSearch[scheme].items()  )
            logger.debug("PathFinder.Schemedicts updated to: %s", self.Schemedicts)
        logger.debug("PathFinder.getScheme('%s', update=%s) returns path scheme: %s", scheme, update, self.Schemedicts[scheme])
        return self.Schemedicts[scheme]

    def getSchemedict(self, scheme):
        """
        return self.Schemedicts.get(scheme, dict())
        """
        return self.Schemedicts.get(scheme, dict())

    def findPath(self, filename, dircands):
        """
        Given an ordered list of candidate directories, return the first directory
        in which filename is found. If filename is not present in either
        of the directory candidates, return None.
        Changes: replaced for-loops with a sequence of generators.
        """

        okdirs = ( dircand for dircand in dircands if os.path.isdir(dircand) )
        normdirs = ( os.path.normpath(dircand) for dircand in okdirs )
        dirswithfilename = ( dircand for dircand in normdirs if filename in os.listdir(dircand) )
        firstdir = next(dirswithfilename, None)
        if firstdir:
            winnerpath = os.path.join(firstdir, filename)
            logger.debug("%s, config file found: %s", self.__class__.__name__, winnerpath)
            return winnerpath
        else:
            logger.debug("Warning, no config found for config filename: '%s'; tested: %s", filename, dircands)

    def printSchemes(self):
        """
        Returns a pretty string representation of all schemes in self.Schemedicts .
        """
        ret = "\n".join( u"scheme '{}': {}".format(scheme, ", ".join(u"{}='{}'".format(k, v) \
                    for k, v in schemedict.items() ) ) \
                    for scheme, schemedict in self.Schemedicts.items() )
        return ret
