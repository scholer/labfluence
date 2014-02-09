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
Server module. Provides classes to access e.g. a Confluence server through xmlrpc.
"""

from __future__ import print_function, division
import xmlrpclib
import socket
#import os.path
import itertools
import string
#import sys
from Crypto.Cipher import AES
#import Crypto.Random
from Crypto.Random import random as crypt_random
import inspect
import logging
logger = logging.getLogger(__name__)

# Labfluence modules and classes:
#from confighandler import ConfigHandler, ExpConfigHandler
from utils import login_prompt, display_message

# Decorators:
from decorators.cache_decorator import cached_property

defaultsockettimeout = 3.0




class AbstractServer(object):
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
    def __init__(self, serverparams=None, username=None, password=None, logintoken=None, url=None,
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
        self._url = url
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
    def AutologinEnabled(self, ):
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
    def UI(self, ):
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
        if port:
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
                self.Confighandler.invokeEntryChangeCallback('wiki_server_status')
        logger.debug( "Server: _connectionok is now: %s", self._connectionok)


    def execute(self, function, *args):
        """
        Update: the args should now NOT include the token.
        This is managed by this method, in order to avoid sending a None-type token.
        Executes a server method, setting self._connectionok on suceed and fail on error.
        If the server connection fails and raisetimeouterrors is set to true,
        a socket.error will be raised. Otherwise, this will return None.
        (Which might be hard to check...)
        Note: raiseerrors only apply to e.g. timeout errors, i.e. permanent issues that will not
        change by changing e.g. parameters.
        It does not appy to e.g. xmlrpclib.Fault, which is raised from e.g. an erroneous token
        and can be corrected by providing a correct token or logging in anew.

        Edit: changed policy, execute() and autologin() will always catch socket errors;
        test_token() and login() are allowed to catch xmlrpclib.Fault exceptions,
        while all other methods should not catch any exceptions.
        """
        token = self.Logintoken
        if not token:
            logger.info("%s, self.Logintoken is '%s', will try to obtain anew..", self.__class__.__name__, token)
            if self.AutologinEnabled:
                logger.debug("%s, attempting autologin()...", self.__class__.__name__)
                token = self.autologin() # autologin will setok/notok
            else:
                logger.debug("AotologinEnabled is False.")
            if not token:
                logger.warning("%s, token could not be obtained (is '%s'), aborting.", self.__class__.__name__, token)
                return None
        try:
            logger.debug("%s, trying to execute for function %s with args %s", self.__class__.__name__, inspect.stack()[1][3], args)
            ret = function(token, *args)
            self.setok()
            logger.debug("server request completed, returned value is: %s", type(ret))
            return ret
        except socket.error as e:
            logger.debug("%s, socket error during execution of function %s: %s", self.__class__.__name__, inspect.stack()[1][3], e)
            self.notok()
            logger.debug("self.notok() invoked?")
            #if raiseerrors is None:
            #raiseerrors = self._raiseerrors
            #if raiseerrors is None:
            #    raiseerrors = self.RaiseTimeoutErrors
            #if raiseerrors:
            #    raise e
        except xmlrpclib.Fault as e:
            logger.debug("%s: xmlrpclib.Fault exception raised during execution of function %s:%s", self.__class__.__name__, inspect.stack()[1][3], e)
            cause = self.determineFaultCause(e)
            # causes: PageNotAvailable, IncorrectUserPassword, TooManyFailedLogins, TokenExpired
            logger.debug("Cause of xmlrpclib.Fault determined to be: '%s'", cause)
            if cause in ('TokenExpired', 'IncorrectUserPassword'):
                if self.AutologinEnabled:
                    prompt = 'force' if cause == 'IncorrectUserPassword' else 'auto'
                    logger.debug("%s: invoking self.autologin with prompt=%s", self.__class__.__name__, prompt)
                    token = self.autologin(prompt=prompt) # autologin will set connectionok status
                    if self._connectionok:
                        # try once more:
                        #try:
                        logger.debug("%s, attempting once more to invoke %s with args %s", self.__class__.__name__, inspect.stack()[1][3], args)
                        ret = function(token, *args)
                        self.setok()
                        logger.debug("%s, %s returned %s (returning)", self.__class__.__name__, inspect.stack()[1][3], ret)
                        return ret
                else:
                    self.notok()
                    logger.debug("%s: Autologin disabled. self._connectionok set to '%s'", self.__class__.__name__, self._connectionok)
            elif cause == 'TooManyFailedLogins':
                self.display_message("Server ERROR, too many failed logins. Determined from exception: %r" % e)
                logger.warning("%s: Server ERROR, too many failed logins. Determined from exception: %s", self.__class__.__name__, e)
            elif cause == 'PageNotAvailable':
                logger.info("PageNotAvailable: %s called with args %s. Re-raising the xmlrpclib.Fault exception.", inspect.stack()[1][3], args)
                raise e
            else:
                logger.info("Unknown Fault excepted after calling %s with args %s. Re-raising the xmlrpclib.Fault exception.", inspect.stack()[1][3], args)
                raise e
        logger.debug("end of execute method reached. This should not happen.")
        return None # Default if... But consider raising an exception instead.


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
                logger.info("AbstractServer.getToken() :: Aborting...")
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
        Subclass this
        """
        pass



class ConfluenceXmlRpcServerProxy(AbstractServer):
    """

Note regarding long integer vs string for pageIds etc (from the docs):
Confluence uses 64-bit long values for things like object IDs, but XML-RPC's largest supported numeric type is int32.
As a result, all IDs and other long values are converted to Strings when passed through XML-RPC API.

Alternative to xmlrpc (at /rpc/xmlrpc) includes:
* SOAP API, at /rpc/soap-axis/confluenceservice-v2?wsdl
* JSON API, at /rpc/json-rpc/confluenceservice-v2
* REST API, at /confluence/rest/prototype/1/space/ds (/context/rest/api-name/api-version/resource-name)

https://developer.atlassian.com/display/CONFDEV/Confluence+XML-RPC+and+SOAP+APIs
https://developer.atlassian.com/display/CONFDEV/Remote+Confluence+Methods
https://developer.atlassian.com/display/CONFDEV/Remote+Confluence+Data+Objects
https://confluence.atlassian.com/display/DISC/Confluence+RPC+Cmd+Line+Script  (uses XML-RPC API v1, not v2)

TODO: If a UI framework is available, it might be convenient to add a timer-based keep-alive callback
to prevent the login token from expiring.

    """
    def __init__(self, serverparams=None, username=None, password=None, logintoken=None, url=None,
                 confighandler=None, autologin=True):
                 #serverparams=None, username=None, password=None, logintoken=None,
                 #protocol=None, urlpostfix=None, confighandler=None, VERBOSE=0):
        #self._urlformat = "{}:{}/rpc/xmlrpc" if port else "{}/rpc/xmlrpc"
        logger.debug("New %s initializing...", self.__class__.__name__)
        self.CONFIG_FORMAT = 'wiki_{}'
        #self.ConfigEntries = dict( (key, self.CONFIG_FORMAT.format(key.lower()) ) for key in ['Host', 'Port', 'Protocol', 'Urlpostfix', 'Url', 'Username', 'Password', 'Logintoken'] )
        # configentries are set by parent AbstractServer using self.CONFIG_FORMAT
        # Remember, super takes current class as first argument (python2)
        super(ConfluenceXmlRpcServer, self).__init__(serverparams=serverparams, username=username,
                                                     password=password, logintoken=logintoken, url=url,
                                                     confighandler=confighandler, autologin=autologin)
        self._defaultparams = dict(port='8090', urlpostfix='/rpc/xmlrpc', protocol='https')
        #self.UI = ui # Is now a property that goes through confighandler.
        appurl = self.AppUrl
        if not appurl:
            logger.warning("WARNING: Server's AppUrl is '%s', ABORTING init!", appurl)
            return None
        logger.info("%s - Making server with url: %s", self.__class__.__name__, appurl)
        self.RpcServer = xmlrpclib.ServerProxy(appurl, use_datetime=True) # Note: xmlrpclib line 1613: Server = ServerProxy # for compatability.
        if self.AutologinEnabled:
            self.autologin()
        logger.debug("%s initialized.", self.__class__.__name__)

    def autologin(self, prompt='auto'):
        """
        I intend to do something like if prompt='never'/'auto'/'force'
        If prompt is 'force', then the login will NOT attempt to locate a valid login token,
        but will always ask for user credentials.
        If prompt is 'never', then the method will attempt to find a valid token and fail silently
        if no valid token is found.
        If prompt is 'auto', then the method will first attempt to locate a valid token and then
        prompt the user for credentials if no valid token is found.

        If successful login is achieved, self.setok is invoked either by self.login() or
        self.test_token(), provided that doset is true (so that the token is saved in memory - default).
        """
        socket.setdefaulttimeout(3.0) # without this there is no timeout, and this may block the requests
        #oldflag = self._raiseerrors
        # Edit: None of the methods will attempt to catch socket errors;
        # it is only this autologin() and the execute() method that does that.
        #self._raiseerrors = True # Ensure that e.g. timeout errors are raised.
        token = None
        logger.debug("%s.autologin(prompt='%s') invoked.", self.__class__.__name__, prompt)
        try:
            #
            if prompt in ('force', ):
                token = self.login(prompt=True) # doset defaults to True
            else:
                if self._logintoken and self.test_token(self._logintoken, doset=True):
                    token = self._logintoken
                    logger.info('Connected to server using token from self._logintoken, type and length: %s %s', type(token), len(token))
                elif self.Username and self.Password and self.login(doset=True):
                    # Providing a plain-text password should generally not be used;
                    # there is really no need for a password other than for login, only store the token.
                    # Edit: It might be a really good idea to store the password in-memory,
                    # so that it can be used to re-authenticate with the server when a token expires during run.
                    logger.info('Connected to server using provided username and password...')
                    token = self._logintoken
                elif self.find_and_test_tokens(doset=True):
                    logger.info('Token found in the config is valid, login ok...')
                    token = self._logintoken
                elif prompt in ('auto'):
                    logger.debug("Trying to obtain credentials via login(prompt=True)...")
                    token = self.login(prompt=True)
                    logger.debug("login(prompt=True) returned token of type: %s", type(token))
                else:
                    logger.info("Uhm... what?")
        except socket.error as e:
            logger.warning("%s - socket error prevented login, probably timeout, error is: %s", self.__class__.__name__, e)
        #self._raiseerrors = oldflag
        except xmlrpclib.ProtocolError as err:
            logger.warning("ProtocolError raised; This is probably because XML-RPC is not enabled for your Confluence instance under general configuration. Error: %s", err )
        if self.Logintoken:
            self.setok()
        else:
            self.notok()
        return token


    def find_and_test_tokens(self, doset=False):
        """
        Attempts to find a saved token, looking for standard places.
        Found tokens are checked with self.test_token(token).
        Currently only checks the config provided via Confighandler.
        If a valid token is found, returns that token. Otherwise return None.
        """
        # 1) Check the config...:
        token = self.getToken() # returns unencrypted token stored in config (encrypted, hopefully)
        if token and self.test_token(token, doset=doset):
            return token
        else:
            logger.info("find_and_test_tokens() :: No valid token found in config...")
        # 2) Check a list of files? No, the token should be saved in the config or nowhere at all.

    def test_connection(self):
        """
        Return True if connection can be established, false otherwise.
        """
        return bool(self.test_token(doset=False))

    def test_token(self, logintoken=None, doset=True):
        """
        Test a login token; must be decrypted.
        If token=None, will test self.Logintoken
        If doset=True (default), and the token proves valid, this method will store the token in self.
        Returns:
        - True if token is valid.
        - False if token is not valid (or if otherwise failed to connect to server <-- should be fixed...)
        - None if no valid token was provided.
        Note: This should not catch exceptions other than xmlrpclib.Fault and only if it is caused by an invalid token.
        """
        if logintoken is None:
            logintoken = getattr(self, 'Logintoken', None)
        if not logintoken:
            logger.info("ConfluenceXmlRpcServer.test_token() :: No token provided, aborting...")
            return None
        try:
            serverinfo = self._testConnection(logintoken) # _testConnection() and _login() does NOT use the execute method.
            logger.debug("Successfully obtained serverinfo from server (version %s.%s.%s, build %s) via _testConnection using token of type %s",
                         serverinfo['majorVersion'], serverinfo['minorVersion'], serverinfo['patchLevel'], serverinfo['buildId'],
                         type(logintoken))
            if doset:
                self.Logintoken = logintoken
                self.setok()
            return True
        except xmlrpclib.Fault as err:
            logger.debug("ConfluenceXmlRpcServer.test_token() : tested token of length %s did not work; %s: %s",
                         len(logintoken), err.faultCode, err.faultString)
            return False

    def promptForUserPass(self, username=None, msg=None):
        """
        Prompts for user credentials, using either the registrered UI,
        if it has an attribute login_prompt, or else using standard
        terminal prompt.
        """
        promptopts = self.Loginpromptoptions
        if self.UI and hasattr(self.UI, 'login_prompt'):
            logger.debug("Using login_prompt method registrered with self.UI.")
            promptfun = self.UI.login_prompt
        else: # use command line login prompt, defined above.
            promptfun = login_prompt
        username, password = promptfun(username=username, msg=msg, options=promptopts)
        return username, password


    def login(self, username=None, password=None, doset=True,
              prompt=False, retry=3, dopersist=True, msg=None):
        """
        Attempt server login.
        If prompt is True, then username and password will be obtained by prompting the user.
        If doset is True, the token will be stored in memory.
        If dopersist is True, self.saveToken will be invoked after successful login.

        This method should NOT attempt to catch socket errors;
        only autologin() and execute() may do that.
        The method SHOULD catch xmlrpclib.Fault errors,
        """
        logger.debug("server.login invoked, retry=%s, prompt=%s, msg=%s", retry, prompt, msg)
        if retry < 0:
            logger.debug("retry (%s) is less than zero, aborting...", retry)
            return
        username = username or self.Username
        password = password or self.Password
        if prompt is True:
            logger.debug("Calling login prompt...")
            username, password = self.promptForUserPass(username=username, msg=msg)
        if not (username and password):
            logger.info( "%s :: Username or password is boolean False; retrying...", self.__class__.__name__ )
            newmsg = "Empty username or password; please try again. Use Ctrl+C (or cancel) to cancel."
            if password is None:
                logger.info("Password is %s, indicating an aborted prompt, will abort without further retries...", type(password))
                return
            token = self.login(username, doset=doset, prompt=prompt, retry=retry-1, msg=newmsg)
            return token
        try:
            logger.debug("Attempting server login with username: %s", username)
            token = self._login(username, password)
            logger.debug("Token of type %s obtained from server.", type(token))
            if doset:
                logger.debug("Saving login token as server attribute (in memory).")
                self.Logintoken = token
                # If a succesful login is completed, set serverstatus to ok:
                # This is not done by self._login, which does not use execute.
                self.setok()
            if dopersist:
                logger.debug("Persisting login token to config file.")
                self.saveToken(token, username=username)
            if prompt:
                if self.Loginpromptoptions.get('save_username_inmemory', True):
                    self._username = username
                if self.Loginpromptoptions.get('save_password_inmemory', True):
                    self._password = password
            logger.info("Logged in as '%s', received token of length %s", username, len(token))
        except xmlrpclib.Fault as err:
            err_msg = "Login error, catched xmlrpclib.Fault. faultCode and -String is:\n%s: %s" % ( err.faultCode, err.faultString )
            logger.info(err_msg)
            # NOTE: In case of too many failed logins, it will not be possible to log in with xmlrpc,
            # and a browser login is required.
            # Unfortunately, the error is pretty similar, same faultCode and only slightly different faultString.
            # For incorrect username/password, faultCode: faultString is: (and e.args and e.message are both empty)
            # 0: java.lang.Exception: com.atlassian.confluence.rpc.AuthenticationFailedException: Attempt to log in user 'scholer' failed - incorrect username/password combination.
            # For too many failed logins, faultCode: faultString is:
            # 0: java.lang.Exception: com.atlassian.confluence.rpc.AuthenticationFailedException: Attempt to log in user 'scholer' failed. The maximum number of failed login attempts has been reached. Please log into the web application through the web interface to reset the number of failed login attempts.
            #logger.debug("%d: %s" % ( err.faultCode, err.faultString)
            # In case the password has been changed or whatever, reset it:
            if not prompt and self._password:
                # The password did not work. Make sure to unset it, so automatic login attempts will not try to use it again.
                self._password = None
            if prompt and int(retry)>0:
                token = self.login(username, doset=doset, prompt=prompt, retry=retry-1, msg=err_msg)
            else:
                logger.info("server.login failed completely, prompt is '%s' and retry is %s.", prompt, retry)
                return None
        return token


    def determineFaultCause(self, e):
        """
        A convenient source of information regarding Confluence's xmlrpc interface can be found in the confluence
        source code, in
        confluence-5.3.1-source/confluence-project/confluence-plugins/confluence-misc-plugins/confluence-rpc-plugin/src/java/com/atlassian/confluence/rpc/xmlrpc
        - ConfluenceXmlRpcHandler provides a convenient overview
        - ConfluenceXmlRpcHandlerImpl includes most of the source required to understand the confluence xmlrpc interface.

        Most actual calls are relayed through ConfluenceSoapService soapServiceDelegator, from
        confluence-5.3.1-source/confluence-project/confluence-plugins/confluence-misc-plugins/confluence-rpc-plugin/src/java/com/atlassian/confluence/rpc/soap
        although most actual controls are implemented in XhtmlSoapService.java, which in return connects to the following (in soap/services):
            private SpacesSoapService spacesService;
            private PagesSoapService pagesService;
            private UsersSoapService usersService;
            private BlogsSoapService blogsService;
            private AdminSoapService adminSoapService;
            private LabelsSoapService labelsSoapService;
            private AttachmentsSoapService attachmentsService;
            private NotificationsSoapService notificationsService;
        All of these then uses one of the following (from confluence-project/confluence-core/confluence/src/java/com/atlassian/confluence/)
            protected SpaceManager spaceManager;
            protected PermissionManager permissionManager;
            protected PageManager pageManager; - in pages/
            protected LinkManager linkManager;
            protected UserAccessor userAccessor;
            protected ContentEntityManager contentEntityManager;
        Note that these are interface specifications. The actual implementations are usually named in form of:
            DefaultPageManager
        These again uses e.g.
            private AbstractPageDao abstractPageDao; (from com.atlassian.confluence.pages.persistence.dao.AbstractPageDao)
                only interface, implemented by e.g.
        Generally, to find implementations rather than interfaces, search for  grep -nR -P "public class .*PageDao" (to find implementations of AbstractPageDao)
        (use grep -lRZP <regex> <dir> | xargs -0 <command> to open easily)

        It appears there are only three types of exceptions from the xmlrpc:
        * InvalidSessionException
        * NotPermittedException
        * RemoteException
        Additionally, the soap part provides the following:
        * AuthenticationFailedException
        * AlreadyExistsException

        """
        # For incorrect username/password, faultCode: faultString is: (and e.args and e.message are both empty)
        # 0: java.lang.Exception: com.atlassian.confluence.rpc.AuthenticationFailedException: Attempt to log in user 'scholer' failed - incorrect username/password combination.
        # For too many failed logins, faultCode: faultString is:
        # 0: java.lang.Exception: com.atlassian.confluence.rpc.AuthenticationFailedException: Attempt to log in user 'scholer' failed. The maximum number of failed login attempts has been reached. Please log into the web application through the web interface to reset the number of failed login attempts.
        # Exception during getPage invokation can look like:
        # <Fault 0: "java.lang.Exception: com.atlassian.confluence.rpc.RemoteException: You're not allowed to view that page, or it does not exist.">
        # If XML-RPC is not enabled under Confluence General Configuration:
        # xmlrpclib.ProtocolError: <ProtocolError for wiki.cdna.au.dk/rpc/xmlrpc: 403 Forbidden>
        #import string
        # causes: PageNotAvailable, IncorrectUserPassword, TooManyFailedLogins, TokenExpired
        # xmlrpclib.Fault attributes: e.faultCode, e.faultString, e.message, e.args
        # for more rpc exceptions, search the confluence code in
        # <source-dir>/confluence-project/confluence-core/confluence/src/java/com/atlassian/confluence/rpc
        logger.debug("Determining cause of Fault with attributes: faultCode=%s, faultString=%s, message=%s, args=%s", e.faultCode, e.faultString, e.message, e.args)
        import re
        faultRegexs = [
                ("PageNotAvailable",        r"com\.atlassian\.confluence\.rpc\.RemoteException.* You're not allowed to view that page, or it does not exist"),
                ("IncorrectUserPassword",   r"com\.atlassian\.confluence\.rpc\.AuthenticationFailedException.* Attempt to log in user .* failed - incorrect username/password combination"),
                ("TooManyFailedLogins",     r"com\.atlassian\.confluence\.rpc\.AuthenticationFailedException.* Attempt to log in user .* failed\. The maximum number of failed login attempts has been reached\. Please log into the web application through the web interface to reset the number of failed login attempts"),
                ("TokenExpired",            r"User not authenticated or session expired"),
                ]
        for cause, regexpat in faultRegexs:
            match = re.search(regexpat, e.faultString)
            if match:
                logger.debug("Fault determined to be: %s", cause)
                return cause
        return None




    ##############################
    #### Un-managed methods ######
    ##############################

    # Note: These methods should NOT catch any exceptions!
    def _login(self, username, password):
        """
        Returns a login token.
        Raises xmlrpclib.Fauls on auth error/failure.
        Uhm... there might be an infinite cycle here,
        execute->autologin->login->execute...
        """
        return self.RpcServer.confluence2.login(username, password)
        #return self.execute(self.RpcServer.confluence2.login(username,password)

    def _testConnection(self, token=None):
        """
        Used mostly to see if a token is valid.
        This method should be wrapped in a try-except clause.
        """
        if token is None:
            token = self._logintoken
        return self.RpcServer.confluence2.getServerInfo(token)



    ################################
    #### SERVER-level methods ######
    ################################

    def logout(self):
        """
        Returns True if token was present (and now removed), False if token was not present.
        Returns None if no token could be found.
        """
        ret = self.execute(self.RpcServer.confluence2.logout)
        self.clearToken()
        return ret


    def getServerInfo(self):
        """
        returns a list of dicts with space info for spaces that the user can see.
        """
        return self.execute(self.RpcServer.confluence2.getServerInfo)
        #return self.RpcServer.confluence2.getServerInfo(token)


    def getSpaces(self):
        """
        returns a list of dicts with space info for spaces that the user can see.
        """
        logger.debug('self.RpcServer.confluence2.getSpaces() invoked...')
        return self.execute(self.RpcServer.confluence2.getSpaces)


    ################################
    #### USER methods       ########
    ################################

    def getUser(self, username):
        """
        returns a dict with name, email, fullname, url and key.
        """
        return self.execute(self.RpcServer.confluence2.getUser, username)

    def createUser(self, newuserinfo, newuserpasswd):
        """ Creates a new user on the server using provided userinfo and password. """
        return self.execute(self.RpcServer.confluence2.addUser, newuserinfo, newuserpasswd)

    def getGroups(self):
        """ Returns a list of all groups. Requires admin priviledges. """
        return self.execute(self.RpcServer.confluence2.getGroups)

    def getGroup(self, group):
        """ Returns a single group. Requires admin priviledges. """
        return self.execute(self.RpcServer.confluence2.getSpaces, group)

    def getActiveUsers(self, viewAll):
        """ Returns a list of all active users. """
        return self.execute(self.RpcServer.confluence2.getActiveUsers, viewAll)




    ################################
    #### PAGE-level methods ########
    ################################

    def getPages(self, spaceKey):
        """
        returns all the summaries in the space.
        PageSummary datastructs are dicts, with:

Key         Type   Value
-----------------------------------------------------------------------
id          long   the id of the page
space       String the key of the space that this page belongs to
parentId    long   the id of the parent page
title       String the title of the page
url         String the url to view this page online
permissions int    the number of permissions on this page (deprecated: may be removed in a future version)

        """
        return self.execute(self.RpcServer.confluence2.getPages, spaceKey)

    def getPage(self, pageId=None, spaceKey=None, pageTitle=None):
        """
        Wrapper for xmlrpc getPage method.
        Takes pageId as long (not int but string!).
        Edit: xmlrpc only supports 32-bit long ints and confluence uses 64-bit, all long integers should
        be transmitted as strings, not native ints.
        Page datastructs are dicts, with:

Key           Type    Value
---------------------------------------------------------------------------
id            long    the id of the page
space         String  the key of the space that this page belongs to
parentId      long    the id of the parent page
title         String  the title of the page
url           String  the url to view this page online
version       int     the version number of this page
content       String  the page content
created       Date    timestamp page was created
creator       String  username of the creator
modified      Date    timestamp page was modified
modifier      String  username of the page's last modifier
homePage      Boolean whether or not this page is the space's homepage
permissions   int     the number of permissions on this page (deprecated: may be removed in a future version)
contentStatus String  status of the page (eg. current or deleted)
current       Boolean whether the page is current and not deleted

        """
        if pageId:
            pageId = str(pageId) # getPage method takes a long int.
            return self.execute(self.RpcServer.confluence2.getPage, pageId)
        elif spaceKey and pageTitle:
            return self.execute(self.RpcServer.confluence2.getPage, spaceKey, pageTitle)
        else:
            raise ValueError("Must specify either pageId or spaceKey/pageTitle.")

    def removePage(self, pageId):
        """
        Removes a page, returns None.
        takes pageId as string.
        server side raises:
         - no view permit:   RemoteException("You're not allowed to view that page, or it does not exist.")
         - no remove permit: NotPermittedException("You do not have permission to remove this page")
         - if pageId is not latest version: RemoteException("You can't remove an old version of the page - remove the current version.")
         -
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.removePage, pageId)

    def movePage(self, sourcePageId, targetPageId, position='append'):
        """
        moves a page's position in the hierarchy.
        takes pageIds as strings.
        Arguments:
        * sourcePageId - the id of the page to be moved.
        * targetPageId - the id of the page that is relative to the sourcePageId page being moved.
        * position - "above", "below", or "append". (Note that the terms 'above' and 'below' refer to the relative vertical position of the pages in the page tree.)
        Details for position:
        * above -> source and target become/remain sibling pages and the source is moved above the target in the page tree.
        * below -> source and target become/remain sibling pages and the source is moved below the target in the page tree.
        * append-> source becomes a child of the target.
        """
        sourcePageId, targetPageId = str(sourcePageId), str(targetPageId)
        return self.execute(self.RpcServer.confluence2.movePage, sourcePageId, targetPageId, position)

    def getPageHistory(self, pageId):
        """
        Returns all the PageHistorySummaries
         - useful for looking up the previous versions of a page, and who changed them.
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.getPageHistory, pageId)

    def getAncestors(self, pageId):
        """
        # Returns list of page attachments
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.getAncestors, pageId)

    def getChildren(self, pageId):
        """
        Returns all the direct children of this page (as a list of PageSummary structs)
        PageSummary structs has keys: id, space, parentId, title, url, permissions.
        Arguments:
        -   string pageId
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.getChildren, pageId)

    def getDescendents(self, pageId):
        """
        # Returns all the descendants of this page (children, children's children etc).
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.getDescendents, pageId)


    ##############################
    #### Comment  methods   ######
    ##############################

    def getComments(self, pageId):
        """
        # Returns all the comments for this page.
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.getComments, pageId)

    def getComment(self, commentId):
        """
        # Returns an individual comment.
        takes commentId as string.
        """
        commentId = str(commentId)
        return self.execute(self.RpcServer.confluence2.getComment, commentId)

    def removeComment(self, commentId):
        """
        # Returns an individual comment.
        takes commentId as string.
        """
        commentId = str(commentId)
        return self.execute(self.RpcServer.confluence2.removeComment, commentId)

    def addComment(self, comment_struct):
        """ Adds a comment to the page."""
        return self.execute(self.RpcServer.confluence2.addComment, comment_struct)

    def editComment(self, comment_struct):
        """ Updates an existing comment on the page. """
        return self.execute(self.RpcServer.confluence2.editComment, comment_struct)



    ######################################
    #### Attachment-level methods   ######
    ######################################

    def getAttachments(self, pageId):
        """
        Returns list of page attachments,
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.getAttachments, pageId)

    def getAttachment(self, pageId, fileName, versionNumber=0):
        """
        Returns get information about an attachment.
        versionNumber=0 is the current version.
        """
        return self.execute(self.RpcServer.confluence2.getAttachment, pageId, fileName, versionNumber)

    def getAttachmentData(self, pageId, fileName, versionNumber=0):
        """ Returns the contents of an attachment. (bytes) """
        return self.execute(self.RpcServer.confluence2.getAttachmentData, pageId, fileName, versionNumber)

    def addAttachment(self, contentId, attachment_struct, attachmentData):
        """
        Add a new attachment to a content entity object.
        Note that this uses a lot of memory - about 4 times the size of the attachment.
        The 'long contentId' is actually a String pageId for XML-RPC.

        Note: The Experiment class' uploadAttachment() method can take a filpath.
        Use utils.attachmentTupFromFilepath(filepath) to create usable
            attachment_struct, attachmentData
        variables.
        """
        to = socket.getdefaulttimeout() or defaultsockettimeout
        socket.setdefaulttimeout(10) # Increase timeout to allow large downloads to complete.
        ret = self.execute(self.RpcServer.confluence2.addAttachment, contentId, attachment_struct, attachmentData)
        socket.setdefaulttimeout(to)
        return ret

    def removeAttachment(self, contentId, fileName):
        """remove an attachment from a content entity object.
        """
        return self.execute(self.RpcServer.confluence2.removeAttachment, contentId, fileName)

    def moveAttachment(self, originalContentId, originalName, newContentEntityId, newName):
        """move an attachment to a different content entity object and/or give it a new name."""
        return self.execute(self.RpcServer.confluence2.moveAttachment, originalContentId, originalName, newContentEntityId, newName)


    ####################################
    #### Content-level methods   #######
    ####################################


    def storePage(self, page_struct):
        """ adds or updates a page.
For adding, the Page given as an argument should have space, title and content fields at a minimum.
For updating, the Page given should have id, space, title, content and version fields at a minimum.
The parentId field is always optional. All other fields will be ignored.
The content is in storage format.
Note: the return value can be null, if an error that did not throw an exception occurred.
Operates exactly like updatePage() if the page already exists.
"""
        if self.VERBOSE:
            logger.info("server.storePage() :: Storing page: %s", page_struct)
        return self.execute(self.RpcServer.confluence2.storePage, page_struct)

    def updatePage(self, page_struct, pageUpdateOptions):
        """ updates a page.
The Page given should have id, space, title, content and version fields at a minimum.
The parentId field is always optional. All other fields will be ignored.
Note: the return value can be null, if an error that did not throw an exception occurred.
"""
        return self.execute(self.RpcServer.confluence2.updatePage, page_struct, pageUpdateOptions)


    def convertWikiToStorageFormat(self, wikitext):
        """ Input wiki format, returns xhtml. """
        return self.execute(self.RpcServer.confluence2.convertWikiToStorageFormat, wikitext)


    def renderContent(self, spaceKey=None, pageId=None, content=None):
        """
        Returns the HTML rendered content for this page. The behaviour depends on which arguments are passed:
        * If only pageId is passed then the current content of the page will be rendered.
        * If a pageId and content are passed then the content will be rendered as if it were the body of that page.
        * If a spaceKey and content are passed then the content will be rendered as if it were on a new page in that space.
        * Whenever a spaceKey and pageId are passed the spaceKey is ignored.
        * If neither spaceKey nor pageId are passed then an error will be returned.
        takes pageId as string.
        """
        if pageId:
            pageId = str(pageId)
            if content:
                return self.execute(self.RpcServer.confluence2.renderContent, pageId, content)
            else:
                return self.execute(self.RpcServer.confluence2.renderContent, pageId)
        elif spaceKey and content:
            return self.execute(self.RpcServer.confluence2.renderContent, spaceKey, content)
        logger.warning("server.renderContent() :: Error, must pass either pageId (with optional content) or spaceKey and content.")
        return None



    ##############################
    #### Search methods      #####
    ##############################

    def search(self, query, maxResults, parameters=None):
        """search
String token, String query, int maxResults, map parameters
 return a list of results which match a given search query (including pages and other content types). This is the same as a performing a parameterised search (see below) with an empty parameter map.
 with paramters argument:
  (since 1.3) like the previous search, but you can optionally limit your search by adding parameters to the parameter map. If you do not include a parameter, the default is used instead.
Parameters for Limiting Search Results
spaceKey
* search a single space
* Values: (any valid space key)
* Default: Search all spaces
type
* Limit the content types of the items to be returned in the search results.
* Values: page, blogpost, mail, comment, attachment, spacedescription, personalinformation
* Default: Search all types
modified
* Search recently modified content
* Valus: TODAY, YESTERDAY, LASTWEEK, LASTMONTH
* Default: No limit
contributor:
* The original creator or any editor of Confluence content. For mail, this is the person who imported the mail, not the person who sent the email message.
* values: Username of a Confluence user.
* default: Results are not filtered by contributor
        """
        if parameters:
            return self.execute(self.RpcServer.confluence2.search, query, parameters, maxResults)
        else:
            return self.execute(self.RpcServer.confluence2.search, query, maxResults)


    def searchForWikiPage(self, spaceKey, pageTitle, required=None, optional=None, searchlevel=1):
        """
        Will only return a single match. Increasing <extended> will produce matches of decreasing
        confidence.
        Arguments:
            <extended> is used to control how much search you want to do.
            <required> dict of lists used to filter results. Any matching result must pass all criteria,
                so if required={'title': ('RS123',), 'creator': ('scholer',)}
                then the page MUST have RS123 in the title and 'scholer' as creator.
            <optional> dict of optional elements. Will contribute to the final score.
        Note that required elements can be either a string (matched by if elem in field)
        or a compiled regex.
        Optional elements are scored by len(elem)/len(field)/sqrt(<number of elem for field>);
        a matching regex scores 1/sqrt(<number of elem for field>).
        Search strategy:
        1) Find page on wiki in space <spaceKey> with pageTitle matching pagetitle (exactly).
        (if extended >= 1:)
        2) Find pages in space with user as contributor and expid in title.
           # If multiple results are returned, filter pages by parentId matching wiki_exp_root_pageId? No, would be found by #2.
        4) Find pages in all spaces with user as contributor and ...?
        5) Find pages in user's space without user as contributor and expid in title?
        """

        # Simple search by matching pagetitle and spacekey:
        logger.info("Performing exact spacekey+pagetitle search on server...")
        try:
            # First try to find a wiki page with an exactly matching pageTitle.
            pagestruct = self.getPage(spaceKey=spaceKey, pageTitle=pageTitle)
            logger.debug("self.getPage returned pagestruct of type '%s'", type(pagestruct))
            if pagestruct:
                logger.info("Exact match in space '%s' found for page '%s'", spaceKey, pageTitle)
                return pagestruct
            else:
                logger.debug(" pagestruct is empty: '%s'", pagestruct)
        except xmlrpclib.Fault:
            # Although execute() catches xmlrpclib.Fault exceptions, it will currently re-raise
            # the exception if it is caused by a PageNotAvailable error.
            logger.info("xmlrpclib.Fault raised, indicating that no exact match found for '%s' in space '%s', searching by query...", pageTitle, spaceKey)

        user = self.Confighandler.get('wiki_username') or self.Confighandler.get('username')
        def search_argument_generator(spaceKey, pageTitle, optional, required):
            """ Yields a range of search arguments for search_filter_rank() """
            params = dict(spaceKey=spaceKey, contributor=user, type='page')
            searchlevel = 1
            if optional:
                if 'title' in optional:
                    optional['title'] = list(optional['title']) + pageTitle.split()
                else:
                    optional['title'] = pageTitle.split()
            else:
                optional = dict(title=pageTitle.split())
            yield (pageTitle, params, required, optional, searchlevel)
            params = dict(contributor=user, type='page')
            yield (pageTitle, params, required, optional, searchlevel)
            params = dict(spaceKey=spaceKey, type='page')
            yield (pageTitle, params, required, optional, searchlevel)

        # Perform various searches on the wiki:
        for query, params, required, optional, arglevel in search_argument_generator(spaceKey, pageTitle, optional, required):
            if arglevel > searchlevel:
                return None
            logger.info("Performing slightly more extended search_filter_rank with query=%s, params=%s, required=%s, optional=%s",
                        pageTitle, params, required, optional)
            results = self.search_filter_rank(query, parameters=params, required=required, optional=optional)
            logger.debug("len(results)=%s returned from search_filter_rank()", len(results))
            if len(results) == 1:
                pagestruct = results[0]
                logger.info("pagestruct keys: %s", pagestruct.keys() )
                # pagestruct keys returned for a server search is: 'id', 'title', 'type', 'url', 'excerpt'
                logger.info("Experiment.searchForWikiPageWithQuery() :: A single hit found : '%s: %s: %s'",
                              pagestruct['space'], pagestruct['id'], pagestruct['title'] )
                return pagestruct
            elif len(results) > 1:
                logger.info("Many hits found, but only allowed to return a single match: %s",
                [ u"{} ({})".format(page['title'], page['id']) for page in results ] )
                return False
        logger.debug("Unable to locate wiki page. Returning None...")
        return None


    def search_filter_rank(self, query, parameters, required=None, optional=None):
        """
        Will search on server using query and parameters, then filter the results
        by required criteria and finally rank the results by optional criteria.
        Arguments:
            <query>     : string
            <parameters>: dict with strings
            <required>  : dict with tuples
            <optional>  : dict with tuples

        Search for wiki page using query <query> and parameters <parameters>.
        These are used to obtain a list of results from the server.
        The <required> argument is then used to filter the returned list.
        The list is then scored by entries in <optional>.

        # UNFORTUNATELY, server results only contains: title, url, excerpt, type, id.

        Note that tuple elements in <required> and <optional> can be either strings
        or compiled regex programs.
        Note that this method may return a list with 0, 1 or more elements.
        """
        # pylint: disable-msg=C0111,W0613
        def evaluate_criteria(criteria, value):
            if isinstance(criteria, basestring):
                if criteria in value:
                    return len(criteria)/len(value)
                else:
                    #logger.debug("Criteria '%s' not in value '%s'", criteria, value)
                    return 0
            else:
                # compiled regex prog:
                return 1 if criteria.match(value) else 0
        if not optional:
            def score_result(result):
                return 0
        else:
            def score_result(result):
                return sum(evaluate_criteria(criteria, result[key])
                                for key, criterias in optional.items()
                                    for criteria in criterias)
        if not required:
            def result_passes_required(result):
                return True
        else:
            logger.debug("Required filter: %s", required)
            def result_passes_required(result):
                return all(evaluate_criteria(criteria, result[key])
                                for key, criterias in required.items()
                                    for criteria in criterias)

        results = self.search(query, 30, parameters)
        logger.debug("Query and parameters returned %s results, filtering and ranking...", len(results))
        if results:
            if required:
                if any(isinstance(value, basestring) for value in required.values()):
                    logger.warning("Basestrings found directly in required dict and not as list/tuples as they should be! required = %s", required)
                results = [page for page in results if result_passes_required(page) ]
            return sorted(results, key=score_result, reverse=True)
        return results



    ####################################
    #### Easier assist methods   #######
    ####################################

    #def getPageAttachments(self, pageId):
    #    return self.getAttachments(self.Logintoken, pageId)


    def storePageContent(self, pageId, spaceKey, newContent, contentformat='xml'):
        """
        Modifies the content of a Confluence page.
        :param page:
        :param space:
        :param content:
        :return: bool: True if succeeded
        """
        page_struct = self.getPage(pageId, spaceKey)
        #logger.warning(data
        if contentformat == 'wiki':
            newContent = self.convertWikiToStorageFormat(newContent)
        page_struct['content'] = newContent
        page = self.execute(self.RpcServer.confluence2.storePage, page_struct)
        return page


ConfluenceXmlRpcServer = ConfluenceXmlRpcServerProxy

# init: (host=None, url=None, port=None, username=None, password=None, logintoken=None, autologin=True, protocol=None, urlpostfix=None)



if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)




"""

Other Confluence xmlrpc API projects:
* https://github.com/al3xandr3/ruby/blob/master/confluence.rb
* https://confluence.atlassian.com/x/cITjCg


NOTES ON ENCRYPTION:
- Currently using pycrypto with CFB mode AES. Requires combiling platform-dependent binaries.
--- I previously used CBC mode, but that requires plaintext and cipertext lenghts being an integer of 16. CFB does not require this.
--- Although according to litterature, OCB mode would be better. But this is patented and not available in pycrypto as far as I can tell.
- SimpleCrypt module also requires pycrypto.
--- Only uses pycrypto for legacy encryption; uses openssl (via process call) for encryption. Not sure how this ports to e.g. windows?
--- Both new and legacy methods uses CBC MODE with AES.
--- It also currently uses random.randint as entrypy provider which is not as good as the random library provided by pycrypto.
- alo-aes 0.3: Does not seem mature; very little documentation.
- M2Crypto
--- Rather big, contains functionality for ssl certificates, etc.
- m2secret
--- Easy-to-use interface to M2Crypto, contained in a single file.
- pyOCB, https://github.com/kravietz/pyOCB
--- This seems to be a pure-python OCB mode AES cryptography module. Only two files.
--- When mature, this is probably the best option for small passwords...
- AESpython (aka pythonAES)
--- another pure-python implementation. However, does not have an easy-to-use interface.
- wheezy.security: simple wrapper for pycrypto.
- https://github.com/alex/cryptography
--- discussion in https://news.ycombinator.com/item?id=6194102

In conclusion:
- I currently use PyCrypto which should be good, except that it requires separate installation
  of platform-dependent binaries.
- pyOCB is probably the best pure-python replacement: only depends on the build-in math module,
  is contained in just two files (__init__.py and AES.py).

REGARDING MODE:
- input length and padding:
--- http://stackoverflow.com/questions/14179784/python-encrypting-with-pycrypto-aes


CRYPTOGRAPHY REFS:
- pycrypto: www.dlitz.net/software/pycrypto/
- http://stackoverflow.com/questions/1220751/how-to-choose-an-aes-encryption-mode-cbc-ecb-ctr-ocb-cfb
- http://www.codinghorror.com/blog/2009/05/why-isnt-my-encryption-encrypting.html (mostly the comments...)
- http://csrc.nist.gov/publications/nistpubs/800-38a/sp800-38a.pdf
- https://github.com/dlitz/pycrypto/pull/33 <- This discussion (from 2013) is interesting. It discusses addition of AEAD modes, of which OCB is one type.
- http://scienceblogs.com/goodmath/2008/08/07/encryption-privacy-and-you/ (OT)




OTHER CONFLUENCE RPC API refs:
* https://bobswift.atlassian.net/wiki/display/CSOAP

"""
