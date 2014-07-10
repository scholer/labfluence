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
# pylint: disable-msg=C0103,C0301,R0201,R0904,W0142
"""
Abstract serverproxy module. Provides AbstractServerProxy base class.

AbstractServer serves two purposes:
1) Define a standard "serverproxy" interface, specifying what methods and
properties a server is expected to implement.
2) Define some of the basic serverproxy functionality which is common
to all implemented server proxies.

"""

from __future__ import print_function, division
import socket
import itertools
import string
from Crypto.Cipher import AES
from Crypto.Random import random as crypt_random
import inspect
import logging
logger = logging.getLogger(__name__)

# Labfluence modules and classes:
from utils import login_prompt, display_message

# Decorators:
from decorators.cache_decorator import cached_property

__version__ = "0.1-dev"


class AbstractServerProxy(object):
    """
    To test if server is connected, just use "if server".
    (To test whether server is was not initialized, use the more specific "if server is None")

    Edits:
    -   Well, the whole ConfigEntries and automatic attribute creation was a bit overly complicated.
        Especially considering that it was only used once, to make the URL from which the RpcServer
        is initialized. Then, the RpcServer object is used the rest of the time.
        Also, the whole "uh, I gotta make sure the base class does not override any attributes in the
        child class is unnessecary.

    """
    def __init__(self, serverparams=None, username=None, password=None, logintoken=None, #url=None,
                 confighandler=None, autologin=True, VERBOSE=0):
        """
        Using a lot of hasattr checks to make sure not to override in case this is set by class descendants.
        However, this could also be simplified using getattr...
        """
        logger.debug("AbstractServer init started.")
        self.VERBOSE = VERBOSE
        #dict(host=None, url=None, port=None, protocol=None, urlpostfix=None)
        self._defaultparams = dict(host="localhost", port='80', protocol='http',
                                   urlpostfix='/rpc/xmlrpc', username='', logintoken='',
                                   raisetimeouterrors=False)
        self._serverparams = serverparams
        self._username = username
        self._password = password
        #logger.debug("%s, init arguments: %s", self.__class__.__name__, locals())
        self._logintoken = logintoken
        self._autologin = autologin
        #self._url = url
        self.Confighandler = confighandler
        self._loginpromptoptions = None
        self._defaultpromptoptions = dict(save_username_inmemory=True, save_password_inmemory=True)
        self._raiseerrors = None # For temporary overwrite.
        #self._raisetimeouterrors = True # Edit: Hardcoded not here but in the attribute getter.
        self._connectionok = None # None = Not tested, False/True: Whether the last connection attempt failed or succeeded.
        ## THIS is essentially just to make it easy to take config entries and make them local object attributes.
        ## It is nice, but not sure why this was so important, though...
        if not hasattr(self, 'CONFIG_FORMAT'):
            self.CONFIG_FORMAT = 'server_{}'

    # Properties
    @property
    def Username(self):
        "Property: Returns the username to use (if available)."
        return  self._username or \
                self.Confighandler.get(self.CONFIG_FORMAT.format('username'), None) or \
                self.Confighandler.get('username', None)
    @property
    def Password(self):
        "Property: Returns the password to use (if available)."
        return  self._password or \
                self.Confighandler.get(self.CONFIG_FORMAT.format('password'), None) or \
                self.Confighandler.get('password', None)
    @property
    def Logintoken(self):
        "Property: Returns the login token to use (if available)."
        return self._logintoken
    @Logintoken.setter
    def Logintoken(self, newtoken):
        "Property setter: Sets the login token to use."
        # Possibly include som auto-persisting, provided it has been requested in config or at runtime?
        self._logintoken = newtoken
    @property
    def Loginpromptoptions(self):
        """
        Property: properties specifying the login prompt behaviour,
        including whether to set username and password in memory.
        (save_username_inmemory, save_password_inmemory).
        Can be set either as self._loginpromptoptions
        or using the confighandlers CONFIG_FORMAT loginpromptoptions
        or app_loginpromptoptions config key,
        defaulting to self._defaultpromptoptions.
        """
        return  self._loginpromptoptions or \
                self.Confighandler.get(self.CONFIG_FORMAT.format('loginpromptoptions'), None) or \
                self.Confighandler.get('app_loginpromptoptions', self._defaultpromptoptions)
    @property
    def AutologinEnabled(self):
        """ Boolean property returning whether autologin should be used. """
        serverparams = self.Serverparams
        if 'autologin_enabled' in serverparams:
            logger.debug("AutologinEnabled found in serverparams.")
            return serverparams['autologin_enabled']
        elif self._autologin is not None:
            logger.debug("AutologinEnabled defined by self._autologin: %s", self._autologin)
            return self._autologin
        else:
            logger.debug("AutologinEnabled defaulting to True")
            return True

    @property
    def UI(self):
        """ Property; Returns the registrered UI to use from the confighandler. """
        if self.Confighandler:
            return self.Confighandler.getSingleton("ui")

    @property
    def Serverparams(self):
        """ Property; Returns the server parameters with which the server was initialized. """
        params = self._defaultparams or dict()
        if self.Confighandler:
            config_params = self.Confighandler.get(self.CONFIG_FORMAT.format('serverparams'), dict()) \
                            or self.Confighandler.get('serverparams', dict())
            logger.debug("config_params: %s", config_params)
            params.update(config_params)
        runtime_params =  self._serverparams or dict()
        params.update(runtime_params)
        return params

    def configs_iterator(self):
        """ Returns an iterator over the various config sources. """
        yield ('runtime params', self._serverparams)
        if self.Confighandler:
            yield ('config params', self.Confighandler.get(self.CONFIG_FORMAT.format('serverparams'), dict()) \
                        or self.Confighandler.get('serverparams', dict()) )
        yield ('hardcoded defaults', self._defaultparams)

    def getServerParam(self, key, default=None):
        """ Returns a particular configuration parameter key. """
        configs = self.configs_iterator()
        for desc, cfg in configs:
            if cfg and key in cfg: # runtime-params
                logger.debug("Returning %s from %s[%s]", cfg[key], desc, key)
                return cfg[key]
        logger.debug("param '%s' not found, returning None.", key)
        return default

    @property
    def RaiseTimeoutErrors(self):
        """ Returns whether to raise timeout errors by querying the server config. """
        return self.getServerParam('raisetimeouterrors', True)
    @property
    def Hostname(self):
        """ Returns the server's hostname by querying the server config. """
        return self.getServerParam('hostname')
    @property
    def Port(self):
        """ Returns the server's port by querying the server config. """
        return self.getServerParam('port')
    @property
    def Protocol(self):
        """ Returns the protocol by which to connect to the server (http/https) by querying the server config. """
        return self.getServerParam('protocol')
    @property
    def UrlPostfix(self):
        """ Returns the server's url postfix (e.g. /rpc/xmlrpc/ by querying the server config. """
        return self.getServerParam('urlpostfix') or ""
    @property
    def BaseUrl(self):
        """ Returns the server's base url by querying the server config. """
        serverparams = self.Serverparams
        if 'baseurl' in serverparams:
            return serverparams['baseurl']
        try:
            url = "://".join( serverparams[itm] for itm in ("protocol", "hostname") )
        except KeyError:
            return None
        port = serverparams.get('port', None)
        if port and port not in (80, 443):
            url += ":{}".format(port)
        return url
    @property
    def AppUrl(self):
        """ Returns the server's application url by querying the server config. """
        params = self.Serverparams
        url = params.get('appurl', None)
        if url:
            return url
        baseurl = self.BaseUrl
        urlpostfix = self.UrlPostfix
        logger.debug("baseurl: %s     urlpostfix: %s", baseurl, urlpostfix)
        if baseurl:
            return baseurl + self.UrlPostfix
        else:
            return None

    @cached_property(ttl=30)
    def CachedConnectStatus(self):
        """ Cached connection status, returning result of self.test_connection. """
        return self.test_connection()


    def UserAgent(self):
        """ User-Agent string reported to the server, if applicable. """
        return "{user} via {appname}/{version} (appurl; appemail)".format(
            username=self.Username, appname="Labfluence", appversion=__version__ ,
            appurl='http://bitbucket.org/rasmusscholer/labfluence/',
            appemail='rasmusscholer@gmail.com')


    def __nonzero__(self):
        return bool(self._connectionok)

    def test_connection(self):
        """
        Should be overridden by child classes.
        Must return True if connection can be established, false otherwise.
        """
        return False

    def setok(self):
        """ Invoke to indicate that the serverproxy is properly connected. """
        if not self._connectionok:
            self._connectionok = True
            if self.Confighandler:
                logger.debug("Invoking confighandler entry change callbacks for 'wiki_server_status'")
                self.Confighandler.invokeEntryChangeCallback('wiki_server_status')
        logger.debug( "Server: _connectionok is now: %s", self._connectionok)
    def notok(self):
        """ Invoke to indicate that the serverproxy NOT is properly connected. """
        logger.debug("server.notok() invoked, earlier value of self._connectionok is: %s", self._connectionok)
        if self._connectionok is not False:
            self._connectionok = False
            if self.Confighandler:
                # If you implement a per-object callback system (instead of having it all in the confighandler),
                # This is a suitable candidate for a callback property.
                self.Confighandler.invokeEntryChangeCallback('wiki_server_status')
        logger.debug( "Server: _connectionok is now: %s", self._connectionok)


    def display_message(self, message):
        """
        Displays a message to the user using the registrered UI.
        """
        if hasattr(self, 'UI') and hasattr(self.UI, 'display_message'):
            try:
                self.UI.display_message(message)
                return
            except AttributeError as e:
                logger.warning("AttributeError while calling self.UI.display_message: %s", e)
        display_message(message)

    def autologin(self, prompt=None):
        """
        The autologin method can always be called, and will attempt to
        It is thus safer to call than login(), since it will not do
        anything if either:
        a) autologin is disabled (e.g. by request)
        b) the server is already connected.
        This method should be defined/overridden by subclasses...
        """
        if prompt is None:
            prompt = login_prompt
        logger.warning("autologin called, but not implemented for class %s", self.__class__.__name__)

    def getToken(self, token_crypt=None):
        """
        Get encrypted token from the confighandler and decrypt it.
        """
        # Obtain encrypted token from sources (currently only confighandler)
        if token_crypt is None:
            token_crypt = self.Confighandler.get('wiki_logintoken_crypt')
        if not token_crypt:
            logger.warning("AbstractServer.getToken() :: ERROR, token_crypt is '%s'; aborting...", token_crypt)
            return
        crypt_key_default = '6xytURQ4JITKMhgN'
        crypt_key = self.Confighandler.get('crypt_key', crypt_key_default)
        crypt_iv = self.Confighandler.get('crypt_iv', None)
        # The IV is set along with the encrypted token; if the IV is not present, the encrypted token cannot be decrypted.
        # Using an initiation vector different from the one used to encrypt the message will produce scamble.
        if crypt_iv is None:
            logger.warning("AbstractServer.getToken() :: Warning, could not retrieve initiation vector for decrypting token...")
            token_unencrypted = self.Confighandler.get('wiki_logintoken')
            if token_unencrypted:
                logger.warning("AbstractServer.getToken() :: unencrypted logintoken found in config. Returning this, but please try to transfer to encrypted version.")
                return token_unencrypted
            else:
                logger.info("AbstractServer): Could not find an unencrypted token in the config, aborting (returning None)...")
                return
        # Uh, it might be better to use AES.MODE
        cryptor = AES.new(crypt_key, AES.MODE_CFB, crypt_iv)
        token = cryptor.decrypt(token_crypt)
        # Perform a check; I believe the tokens consists of string.ascii_letters+string.digits only.
        char_space = string.ascii_letters+string.digits
        if not all( char in char_space for char in token ):
            logger.error("getToken() :: ERROR, invalid token decrypted, decrypted token is '%s'", token)
            return None
        logger.debug("getToken returns token of type %s and length %s", type(token), len(token))
        return token

    def encryptToken(self, token):
        """
        Encrypts token, returning:
            (token_crypt, crypt_iv, crypt_key)
        where:
            token_crypt : encrypted token
            crypt_iv    : the initialization vector used for encryption
            crypt_key   : the encryption key used for encryption
        """
        if token is None:
            logger.error("AbstractServer.saveToken() :: ERROR, token is None; aborting...")
            return
        crypt_key_default = '6xytURQ4JITKMhgN'
        crypt_key = self.Confighandler.get('crypt_key', '6xytURQ4JITKMhgN') # crypt key should generally be stored in the system config; different from the one where crypt_iv is stored...
        # Note: I'm pretty sure the initiation vector needs to be randomly generated on each encryption,
        # but not sure how to do this in practice... should the IV be saved for later decryption?
        # Probably only relevant for multi-message encrypted communication and not my simple use-case...?
        # crypt_iv = self.Confighandler.get('crypt_key', 'Ol6beVHM91ZBh7XP')
        # ok, edit: I'm generating a random IV on every new save; this can be "publically" readable...
        # But, it probably does not make a difference either way; the crypt_key is readable anyways...
        if crypt_key == crypt_key_default:
            new_crypt_key = "".join(crypt_random.sample(string.ascii_letters+string.digits, 16))
            if 'system' in self.Confighandler.Configs:
                self.Confighandler.setkey('crypt_key', new_crypt_key, 'system', autosave=True)
                crypt_key = new_crypt_key
                logger.info("System encryption key set to new random string of length %s", len(new_crypt_key))
            else:
                logger.info("Using default crypt_key for encryption. You should create a 'system' config file, \
                            optionally using labfluence --createconfig system.")
        else:
            logger.debug("Using crypt_key from confighandler...")
        crypt_iv = "".join(crypt_random.sample(string.ascii_letters+string.digits, 16))
        # Not exactly 128-bit worth of bytes since ascii_letters+digits is only 62 in length, but should be ok still; I want to make sure it is realiably persistable with yaml.
        cryptor = AES.new(crypt_key, AES.MODE_CFB, crypt_iv)
        token_crypt = cryptor.encrypt(token)
        logger.debug("Token successfully encrypted (using newly generated crypt iv)")
        return (token_crypt, crypt_iv, crypt_key)


    def saveToken(self, token, username=None):
        """
        When saving token, it is probably only sane also to be able to persist the username.
        From what I can tell, it is not easy to retrieve a username based on a token...
        Note that AES encryption of tokens are different from e.g. saving a password or password hash.
        If saving a password or password hash, you should use a slow encrypting or hashing algorithm,
        e.g. bcrypt or similar for making password hashes.
        """
        token_crypt, crypt_iv, crypt_key = self.encryptToken(token)
        # cfgtype only specifies the "recommended config" to store the config item in.
        # If a key is already set in another config, that is the config that will be used.
        cfgtypes = set()
        if username:
            cfgtypes.add(self.Confighandler.setkey('wiki_username', username, 'user', autosave=False))
        cfgtypes.add(self.Confighandler.setkey('wiki_logintoken_crypt', token_crypt, 'user', autosave=False))
        cfgtypes.add(self.Confighandler.setkey('crypt_iv', crypt_iv, 'user', autosave=False))
        self.Confighandler.saveConfigs(cfgtypes)
        return (token_crypt, crypt_iv, crypt_key)

    def clearToken(self):
        """
        Deletes the current token from all locations.
        """
        self.Logintoken = None
        cfgtypes = set()
        for key in ('wiki_logintoken','wiki_logintoken_crypt'):
            res = self.Confighandler.popkey(key, check_all_configs=True)
            if res:
                # How to use izip to add every other entry in list/tuple:
                # izip(iter, iter) makes pairs (iter[0]+iter[1]), (iter[2], iter[3]), ...)
                # Note that this ONLY works because iterators are single-run generators; does not work with e.g. lists.
                cfgs = ( pair[1] for pair in itertools.izip(*[(x for x in res)]*2) )
                cfgtypes.add(cfgs) # only adding the first key, but should be ok I believe.
        self.Confighandler.saveConfigs(cfgtypes)


    def determineFaultCause(self, e):
        """
        Subclass this, depending on the serverproxy type. (server and API, for confluence server e.g. xmlrpc, REST.)
        """
        pass


