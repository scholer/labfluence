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


import xmlrpclib
import socket
import os.path
import itertools
import string
from Crypto.Cipher import AES
#import Crypto.Random
from Crypto.Random import random as crypt_random
import inspect
import logging
logger = logging.getLogger(__name__)

# Labfluence modules and classes:
from confighandler import ConfigHandler, ExpConfigHandler

# Decorators:
from decorators.cache_decorator import cached_property


def login_prompt(username=None, msg="", options=dict() ):
    """
    The third keyword argument, options, can be modified in-place by the login handler,
    changing e.g. persistance options ("save in memory").
    """
    import getpass
    if username is None:
        username = getpass.getuser() # returns the currently logged-on user on the system. Nice.
    print "\n{}\nPlease enter credentials:".format(msg)
    username = raw_input('Username (enter={}):'.format(username)) or username # use 'username' if input is empty.
    password = getpass.getpass()
    logger.debug("login_prompt returning username, password: {}, {}".format(username, password))
    return username, password

def display_message(message):
    print "\n".join("\n\n", "-"*80, message, "-"*80, "\n\n")

"""
Edits:
-   Well, the whole ConfigEntries and automatic attribute creation was a bit overly complicated.
    Especially considering that it was only used once, to make the URL from which the RpcServer
    is initialized. Then, the RpcServer object is used the rest of the time.
    Also, the whole "uh, I gotta make sure the base class does not override any attributes in the
    child class is unnessecary.

"""


class AbstractServer(object):
    """
    To test if server is connected, just use "if server".
    (To test whether server is was not initialized, use the more specific "if server is None")
    """
    def __init__(self, serverparams=None, username=None, password=None, logintoken=None, url=None,
                 confighandler=None, autologin=True, VERBOSE=0):
        """
        Using a lot of hasattr checks to make sure not to override in case this is set by class descendants.
        However, this could also be simplified using getattr...
        """
        logger.debug("AbstractServer init started.\n")
        self.VERBOSE = VERBOSE
        #dict(host=None, url=None, port=None, protocol=None, urlpostfix=None)
        self._defaultparams = dict(host="localhost", port='80', protocol='http',
                                   urlpostfix='/rpc/xmlrpc', username='', logintoken='',
                                   raisetimeouterrors=False)
        self._serverparams = serverparams
        self._username = username
        self._password = password
        self._logintoken = logintoken
        self._autologin = autologin
        self._url = url
        self._loginpromptoptions = None
        self._defaultpromptoptions = dict(save_username_inmemory=True, save_password_inmemory=True)
        self._raiseerrors = None # For temporary overwrite.
        #self._raisetimeouterrors = True # Edit: Hardcoded not here but in the attribute getter.
        self._connectionok = None # None = Not tested, False/True: Whether the last connection attempt failed or succeeded.
        self.Confighandler = confighandler
       ## THIS is essentially just to make it easy to take config entries and make them local object attributes.
        ## It is nice, but not sure why this was so important, though...
        if not hasattr(self, 'CONFIG_FORMAT'):
            self.CONFIG_FORMAT = 'server_{}'

    # Properties
    @property
    def Username(self):
        return  self._username or \
                self.Confighandler.get(self.CONFIG_FORMAT.format('username'), None) or \
                self.Confighandler.get('username', None)
    @property
    def Password(self):
        return  self._password or \
                self.Confighandler.get(self.CONFIG_FORMAT.format('password'), None) or \
                self.Confighandler.get('password', None)
    @property
    def Logintoken(self):
        return self._logintoken
    @Logintoken.setter
    def Logintoken(self, newtoken):
        # Possibly include som auto-persisting, provided it has been requested in config or at runtime?
        self._logintoken = newtoken
    @property
    def Loginpromptoptions(self):
        return  self._loginpromptoptions or \
                self.Confighandler.get(self.CONFIG_FORMAT.format('loginpromptoptions'), None) or \
                self.Confighandler.get('loginpromptoptions', self._defaultpromptoptions)
    @property
    def AutologinEnabled(self, ):
        serverparams = self.Serverparams
        if 'autologin_enabled' in serverparams:
            return serverparams['autologin_enabled']
        elif self._autologin is not None:
            return self._autologin
        else:
            return True

    @property
    def Serverparams(self):
        params = self._defaultparams or dict()
        if self.Confighandler:
            config_params = self.Confighandler.get(self.CONFIG_FORMAT.format('serverparams'), dict()) \
                            or self.Confighandler.get('serverparams', dict())
            logger.debug("config_params: {}".format(config_params))
            params.update(config_params)
        runtime_params =  self._serverparams or dict()
        params.update(runtime_params)
        return params

    def configs_iterator(self):
        yield ('runtime params', self._serverparams)
        if self.Confighandler:
            yield ('config params', self.Confighandler.get(self.CONFIG_FORMAT.format('serverparams'), dict()) \
                        or self.Confighandler.get('serverparams', dict()) )
        yield ('hardcoded defaults', self._defaultparams)

    def getServerParam(self, key, default=None):
        configs = self.configs_iterator()
        for desc, cfg in configs:
            if cfg and key in cfg: # runtime-params
                logger.debug("Returning {} from {}[{}]".format(cfg[key], desc, key))
                return cfg[key]
        logger.debug("param '{}' not found, returning None.".format(key))
        return default

    @property
    def RaiseTimeoutErrors(self):
        return self.getServerParam('raisetimeouterrors', True)
    @property
    def Hostname(self):
        return self.getServerParam('hostname')
    @property
    def Port(self):
        return self.getServerParam('port')
    @property
    def Protocol(self):
        return self.getServerParam('protocol')
    @property
    def UrlPostfix(self):
        return self.getServerParam('urlpostfix') or ""
    @property
    def BaseUrl(self):
        serverparams = self.Serverparams
        #logger.debug("serverparams: {}".format(serverparams)
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
        params = self.Serverparams
        url = params.get('appurl', None)
        if url:
            return url
        baseurl = self.BaseUrl
        urlpostfix = self.UrlPostfix
        logger.debug("baseurl: {}     urlpostfix: {}".format(baseurl, urlpostfix))
        if baseurl:
            return baseurl + self.UrlPostfix
        else:
            return None

    def __nonzero__(self):
        return bool(self._connectionok)

    def setok(self):
        if not self._connectionok:
            self._connectionok = True
            if self.Confighandler:
                self.Confighandler.invokeEntryChangeCallback('wiki_server_status')
        logger.info("Server: _connectionok set to: '{}' (should be True)".format(self._connectionok) )
    def notok(self):
        logger.debug("server.notok() invoked, earlier value of self._connectionok is: {}".format(self._connectionok))
        if self._connectionok is not False:
            self._connectionok = False
            if self.Confighandler:
                self.Confighandler.invokeEntryChangeCallback('wiki_server_status')
        logger.info( "Server: _connectionok is now: '{}' (should be False)".format(self._connectionok) )


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
            if not token:
                logger.warning("%s, token could not be obtained (is '%s'), aborting.", self.__class__.__name__, token)
            return None
        try:
            logger.debug("%s, trying to execute for function %s with args %s", self.__class__.__name__, inspect.stack()[1][3], args)
            ret = function(token, *args)
            self.setok()
            return ret
        except socket.error as e:
            logger.debug("%s, socket error during execution of function %s:\n%s", self.__class__.__name__, inspect.stack()[1][3], e)
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
                self.display_message("Server ERROR, too many failed logins.\nDetermined from exception:\n{}".format(e))
                logger.warning("%s: Server ERROR, too many failed logins. Determined from exception: %s", self.__class__.__name__, e)
            elif cause == 'PageNotAvailable':
                logger.info("PageNotAvailable: %s called with args %s. Re-raising the xmlrpclib.Fault exception.", inspect.stack()[1][3], args)
                raise e
        return None # Default if... But consider raising an exception instead.


    def display_message(self, message):
        if hasattr(self, 'UI') and hasattr(self.UI, 'display_message'):
            try:
                self.UI.display_message(message)
                return
            except AttributeError as e:
                logger.warning("AttributeError while calling self.UI.display_message: %s", e)
        display_message(message)

    def autologin(self):
        pass

    def getToken(self, token_crypt=None):
        if token_crypt is None:
            token_crypt = self.Confighandler.get('wiki_logintoken_crypt')
        if token_crypt is None:
            logger.warning("\nAbstractServer.getToken() :: ERROR, token_crypt is None; aborting...")
            return
        crypt_key_default = '6xytURQ4JITKMhgN'
        crypt_key = self.Confighandler.get('crypt_key', crypt_key_default)
        if crypt_key == crypt_key_default:
            logger.warning("\nAbstractServer.getToken() :: Warning, using default crypt_key for encryption. You should manually edit the labfluence system config and set this to something else.")
        crypt_iv = self.Confighandler.get('crypt_iv', None)
        # The IV is set along with the encrypted token; if the IV is not present, the encrypted token cannot be decrypted.
        # Using an initiation vector different from the one used to encrypt the message will produce scamble.
        if crypt_iv is None:
            logger.warning("\nAbstractServer.getToken() :: Warning, could not retrieve initiation vector for decrypting token...")
            token_unencrypted = self.Confighandler.get('wiki_logintoken')
            if token_unencrypted:
                logger.warning("\nAbstractServer.getToken() :: unencrypted logintoken found in config. Returning this, but please try to transfer to encrypted version.")
                return token_unencrypted
            else:
                logger.info("AbstractServer.getToken() :: Aborting...")
                return
        # Uh, it might be better to use AES.MODE
        cryptor = AES.new(crypt_key, AES.MODE_CFB, crypt_iv)
        token = cryptor.decrypt(token_crypt)
        # Perform a check; I believe the tokens consists of string.ascii_letters+string.digits only.
        char_space = string.ascii_letters+string.digits
        for char in token:
            if char not in char_space:
                logger.error("getToken() :: ERROR, invalid token decrypted, token is '{}'".format(token))
                return None
        logger.debug("getToken returns token: {}".format(token))
        return token

    def saveToken(self, token, persist=True, username=None):
        """
        When saving token, it is probably only sane also to be able to persist the username.
        From what I can tell, it is not easy to retrieve a username based on a token...
        Note that AES encryption of tokens are different from e.g. saving a password or password hash.
        If saving a password or password hash, you should use a slow encrypting or hashing algorithm,
        e.g. bcrypt or similar for making password hashes.
        """
        crypt_key = self.Confighandler.get('crypt_key', '6xytURQ4JITKMhgN') # crypt key should generally be stored in the system config; different from the one where crypt_iv is stored...
        # Note: I'm pretty sure the initiation vector needs to be randomly generated on each encryption,
        # but not sure how to do this in practice... should the IV be saved for later decryption?
        # Probably only relevant for multi-message encrypted communication and not my simple use-case...?
        # crypt_iv = self.Confighandler.get('crypt_key', 'Ol6beVHM91ZBh7XP')
        # ok, edit: I'm generating a random IV on every new save; this can be "publically" readable...
        # But, it probably does not make a difference either way; the crypt_key is readable anyways...
        crypt_iv = "".join(crypt_random.sample(string.ascii_letters+string.digits, 16))
        # Not exactly 128-bit worth of bytes since ascii_letters+digits is only 62 in length, but should be ok still; I want to make sure it is realiably persistable with yaml.
        cryptor = AES.new(crypt_key, AES.MODE_CFB, crypt_iv)
        if token is None:
            logger.error("\nAbstractServer.saveToken() :: ERROR, token is None; aborting...")
            return
        token_crypt = cryptor.encrypt(token)
        if persist:
            cfgtypes = set()
            cfgtypes.add(self.Confighandler.setkey('wiki_logintoken_crypt', token_crypt, 'user'))
            cfgtypes.add(self.Confighandler.setkey('crypt_iv', crypt_iv, 'user'))
            if username:
                cfgtypes.add(self.Confighandler.setkey('wiki_username', username, 'user'))
            self.Confighandler.saveConfigs(cfgtypes)
        return (token_crypt, crypt_iv, crypt_key)

    def clearToken(self):
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
                ("PageNotAvailable",        "com\.atlassian\.confluence\.rpc\.RemoteException.* You're not allowed to view that page, or it does not exist"),
                ("IncorrectUserPassword",   "com\.atlassian\.confluence\.rpc\.AuthenticationFailedException.* Attempt to log in user .* failed - incorrect username/password combination"),
                ("TooManyFailedLogins",     "com\.atlassian\.confluence\.rpc\.AuthenticationFailedException.* Attempt to log in user .* failed\. The maximum number of failed login attempts has been reached\. Please log into the web application through the web interface to reset the number of failed login attempts"),
                ("TokenExpired",            "User not authenticated or session expired"),
                ]
        for cause, regexpat in faultRegexs:
            match = re.search(regexpat, e.faultString)
            if match:
                logger.debug("Fault determined to be: %s", cause)
                return cause
        return None



class ConfluenceXmlRpcServer(AbstractServer):
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
    """
    def __init__(self, ui=None, **kwargs):
                 #serverparams=None, username=None, password=None, logintoken=None,
                 #protocol=None, urlpostfix=None, confighandler=None, VERBOSE=0):
        #self._urlformat = "{}:{}/rpc/xmlrpc" if port else "{}/rpc/xmlrpc"
        self.CONFIG_FORMAT = 'wiki_{}'
        #self.ConfigEntries = dict( (key, self.CONFIG_FORMAT.format(key.lower()) ) for key in ['Host', 'Port', 'Protocol', 'Urlpostfix', 'Url', 'Username', 'Password', 'Logintoken'] )
        # configentries are set by parent AbstractServer using self.CONFIG_FORMAT
        super(ConfluenceXmlRpcServer, self).__init__(**kwargs) # Remember, super takes current class as first argument.
        self._defaultparams = dict(port='8090', urlpostfix='/rpc/xmlrpc', protocol='https')
        self.UI = ui
        appurl = self.AppUrl
        logger.info("%s - Making server with url: %s", self.__class__.__name__, appurl)
        if not appurl:
            logger.warning("WARNING: Server's AppUrl is '%s'", appurl)
            return None
        self.RpcServer = xmlrpclib.Server(appurl)
        if self.AutologinEnabled:
            self.autologin()

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
        try:
            #
            if prompt in ('force', ):
                token = self.login(prompt=True) # doset defaults to True
            else:
                if self._logintoken and self.test_token(self._logintoken, doset=True):
                    logger.info('Connected to server using provided login token...')
                    token = self._logintoken
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
                    token = self.login(prompt=True)
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
        if token and self.test_token(token, doset=True):
            return token
        else:
            logger.info("find_and_test_tokens() :: No valid token found in config...")
        # 2) Check a list of files? No, the token should be saved in the config or nowhere at all.


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
            if doset:
                self.Logintoken = logintoken
                self.setok()
            return True
        except xmlrpclib.Fault as err:
            logger.debug("ConfluenceXmlRpcServer.test_token() : tested token '%s' did not work; %s: %s", logintoken, err.faultCode, err.faultString)
            return False

    def login(self, username=None, password=None, logintoken=None, doset=True,
              prompt=False, retry=3, dopersist=True, msg=None):
        """
        Attempt server login.
        If prompt is True, then username and password will be obtained by prompting the user.
        If doset is True, the token will be stored in memory.
        If dopersist is True, self.saveToken will be invoked after successful login.

        This method should NOT attempt to catch socket errors;
        only autologin() and execute() may do that.
        """
        #logger.debug("server.login invoked with args (locals): {}".format(locals()))
        if username is None: username=self.Username
        if password is None: password=self.Password
        if prompt is True:
            #msg = "Please provide your credentials" # Uh, no do not override.
            promptopts = self.Loginpromptoptions
            if self.UI and hasattr(self.UI, 'login_prompt'):
                promptfun = self.UI.login_prompt
            else: # use command line login prompt, defined above.
                promptfun = login_prompt
            username, password = promptfun(username=username, msg=msg, options=promptopts)
            # The prompt method may modify the promptopts dict in-place:
        if not (username and password):
            logger.info( "ConfluenceXmlRpcServer.login() :: Username or password is boolean False; retrying..." )
            newmsg = "Empty username or password; please try again. Use Ctrl+C (or cancel) to cancel."
            token = self.login(username, doset=doset, prompt=prompt, retry=retry-1, msg=newmsg)
            return token
        try:
            logger.debug("Attempting server login with username: {}".format(username))
            token = self._login(username,password)
            if doset:
                self.Logintoken = token
                self.setok()
            if dopersist:
                self.saveToken(token, username=username)
            if prompt:
                if promptopts.get('save_username_inmemory', True):
                    self._username = username
                if promptopts.get('save_password_inmemory', True):
                    self._password = password
            logger.info("Logged in as '{}', received token of length {}".format(username, len(token)))
        except xmlrpclib.Fault as err:
            err_msg = "Login error, catched xmlrpclib.Fault. faultCode and -String is:\n{}: {}".format( err.faultCode, err.faultString)
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
                self._password = None
            if prompt and int(retry)>0:
                token = self.login(username, doset=doset, prompt=prompt, retry=retry-1, msg=err_msg)
            else:
                logger.info(err_msg)
                logger.info("server.login failed completely, prompt is '{}' and retry is {}.".format(prompt, retry))
                return None
        # If a succesful login is completed, set serverstatus to ok:
        # This is not done by self._login, which does not use execute.
        return token


    ##############################
    #### Un-managed methods ######
    ##############################

    # Note: These methods should NOT catch any exceptions!
    def _login(self, username,password):
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
        return self.execute(self.RpcServer.confluence2.addUser, newuserinfo, newuserpasswd)

    def getGroups(self):
        # returns a list of all groups. Requires admin priviledges.
        return self.execute(self.RpcServer.confluence2.getGroups)

    def getGroup(self, group):
        # returns a single group. Requires admin priviledges.
        return self.execute(self.RpcServer.confluence2.getSpaces, group)


    def getActiveUsers(self, viewAll):
        # returns a list of all active users.
        return self.execute(self.RpcServer.confluence2.getActiveUsers, viewAll)




    ################################
    #### PAGE-level methods ########
    ################################

    def getPages(self, spaceKey):
        return self.execute(self.RpcServer.confluence2.getPages, spaceKey)

    def getPage(self, pageId=None, spaceKey=None, pageTitle=None):
        """
        Wrapper for xmlrpc getPage method.
        Takes pageId as long (not int but string!).
        Edit: xmlrpc only supports 32-bit long ints and confluence uses 64-bit, all long integers should
        be transmitted as strings, not native ints.
        """
        if pageId:
            pageId = str(pageId) # getPage method takes a long int.
            return self.execute(self.RpcServer.confluence2.getPage, pageId)
        elif spaceKey and pageTitle:
            return self.execute(self.RpcServer.confluence2.getPage, spaceKey, pageTitle)
        else:
            raise("Must specify either pageId or spaceKey/pageTitle.")

    def removePage(self, pageId):
        """
        Removes a page, returns None.
        takes pageId as string.
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

    def getAttachments(self, pageId):
        """
        Returns list of page attachments,
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.getAttachments, pageId)

    def getAncestors(self, pageId):
        """
        # Returns list of page attachments
        takes pageId as string.
        """
        pageId = str(pageId)
        return self.execute(self.RpcServer.confluence2.getAncestors, pageId)

    def getChildren(self, pageId):
        """
        # Returns all the direct children of this page.
        takes pageId as string.
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
        # adds a comment to the page.
        return self.execute(self.RpcServer.confluence2.addComment, comment_struct)

    def editComment(self, comment_struct):
        # Updates an existing comment on the page.
        return self.execute(self.RpcServer.confluence2.editComment, comment_struct)



    ######################################
    #### Attachment-level methods   ######
    ######################################

    def getAttachment(self, pageId, fileName, versionNumber=0):
        # Returns get information about an attachment.
        # versionNumber=0 is the current version.
        return self.execute(self.RpcServer.confluence2.getAttachment, pageId, fileName, versionNumber)

    def getAttachmentData(self, pageId, fileName, versionNumber=0):
        # Returns the contents of an attachment. (bytes)
        return self.execute(self.RpcServer.confluence2.getAttachmentData, pageId, fileName, versionNumber)

    def addAttachment(self, contentId, attachment_struct, attachmentData):
        """
        Add a new attachment to a content entity object.
        Note that this uses a lot of memory - about 4 times the size of the attachment.
        The 'long contentId' is actually a String pageId for XML-RPC.

        Note: The Experiment class' uploadAttachment() method can take a filpath.
        """
        # Uh, how to determine if attachmentData is actually a filename?
        # If attachmentData is read from a text file, it will still be a basestring...
        # Perhaps real attachmentData must be base64 encoded or something?
        #if isinstance(attachmentData, basestring):
        #    try:
        #        data = open(attachmentData, 'rb').read()
        #        attachmentData = data
        #    except IOError:
        #        pass
        return self.execute(self.RpcServer.confluence2.getAttachmentData, contentId, attachment_struct, attachmentData)

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
            logger.info("server.storePage() :: Storing page:\n{}".format(page_struct))
        return self.execute(self.RpcServer.confluence2.storePage, page_struct)

    def updatePage(self, page_struct, pageUpdateOptions):
        """ updates a page.
The Page given should have id, space, title, content and version fields at a minimum.
The parentId field is always optional. All other fields will be ignored.
Note: the return value can be null, if an error that did not throw an exception occurred.
"""
        return self.execute(self.RpcServer.confluence2.updatePage, page_struct, pageUpdateOptions)


    def convertWikiToStorageFormat(self, wikitext):
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
                return self.execute(self.RpcServer.confluence2.renderContent, pageId=pageId, content=content)
            else:
                return self.execute(self.RpcServer.confluence2.renderContent, pageId=pageId)
        elif spaceKey and content:
            return self.execute(self.RpcServer.confluence2.renderContent, spaceKey=pageId, content=content)
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
        return True


# init: (host=None, url=None, port=None, username=None, password=None, logintoken=None, autologin=True, protocol=None, urlpostfix=None)



if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    def test1():
        logger.info("\n>>>>>>>>>>>>>> test_getLocalFilelist() started >>>>>>>>>>>>>")
        username = 'scholer'
        username, password = login_prompt()
        url = 'http://10.14.40.245:8090/rpc/xmlrpc'
        server = ConfluenceXmlRpcServer(url=url, username=username, password=password)


    def test_login():
        username = 'scholer'
        url = 'http://10.14.40.245:8090/rpc/xmlrpc'
        server = ConfluenceXmlRpcServer(url=url, username=username)


    def test_config1():
        paths = [ os.path.join(os.path.dirname(os.path.abspath(__file__)), '../test/config', cfg) for cfg in ('system_config.yml', 'user_config.yml', 'exp_config.yml') ]
        ch = ExpConfigHandler(*paths, VERBOSE=5)
        ch.setdefault('user', 'scholer') # set defaults only sets if not already set.
        #ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc') # setkey overrides.
        print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)
        if server.test_token():
            print "Succesfully connected to server (retrieved serverinfo)!"
        else:
            print "Failed to obtain valid token from server !!"

    def test2():
        confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
        ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
        print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)

    def test_loginAndSetToken(ch=None, persist=False):
        if ch is None:
            ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
        ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
#        ch.setkey('wiki_password', 'http://10.14.40.245:8090/rpc/xmlrpc')
        print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5, autologin=False)
        token = server.Logintoken
        print "\ntoken (before forced login):\t{}".format(token)
        token = server.login(dopersist=persist, prompt=True)
        print "token (after login):\t\t{}".format(token)
        if token:
            token_crypt, crypt_iv, crypt_key = server.saveToken(token, persist=persist)
            print "token_crypt, iv, key:\t{}".format((token_crypt, crypt_iv, crypt_key))
            token_decrypt = server.getToken(token_crypt)
            print "token_decrypt:\t\t\t{}".format(token_decrypt)

    def test_loadToken(ch=None):
        if ch is None:
            ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
        ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
        print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
        # Deactivating autologin...
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5, autologin=False)
        token = server.find_and_test_tokens()
        print "\nFound token: {}".format(token)
        print "server.Logintoken: {}".format(token)
        return server


    def test_getServerInfo(ch=None):
        if ch is None:
            ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
        ch.setkey('wiki_url', 'http://10.14.40.245:8090/rpc/xmlrpc')
        print "confighandler wiki_url: {}".format(ch.get('wiki_url'))
        # Deactivating autologin...
        server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5, autologin=False)
        token = server.find_and_test_tokens()
        print "\nFound token: {}".format(token)
        print "server.Logintoken: {}".format(token)
        if token is None:
            token = server.login(prompt=True)
        ret = server._testConnection()
        print "\n_testConnection returned:\n{}".format(ret)
        serverinfo = server.getServerInfo()
        print "\nServer info:"
        print serverinfo


    def test_getPageById(ch=None, server=None):
        if ch is None:
            ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
        if server is None:
            server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)
        spaceKey = "~scholer"
        pageId = 524310
        pageId_erroneous = '504310'
        page_struct1 = server.getPage(pageId=pageId)
        print "\npage_struct1:"
        print page_struct1
        try:
            page_struct_err = server.getPage(pageId=pageId_erroneous)
            print "\npage_struct_err:"
            print page_struct_err
        except xmlrpclib.Fault as e:
            print "Retrival of on-existing pages by id raises error as expected."

    def test_getPageByName(ch=None, server=None):
        if ch is None:
            ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
        if server is None:
            server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)
        spaceKey = "~scholer"
        title = "RS001 First test page CzkTW"
        title_err = "RS001 First test page CzTW"
        page_struct1 = server.getPage(spaceKey=spaceKey, pageTitle=title)
        print "\npage_struct1:"
        print page_struct1
        try:
            page_struct_err = server.getPage(spaceKey=spaceKey, pageTitle=title_err)
            print "\npage_struct_err:"
            print page_struct_err
        except xmlrpclib.Fault as e:
            print "Retrival of on-existing pages by id raises error as expected."


    def test_movePage1(ch=None, server=None):
        if ch is None:
            ch = confighandler = ExpConfigHandler(pathscheme='default1', VERBOSE=1)
        if server is None:
            server = ConfluenceXmlRpcServer(confighandler=ch, VERBOSE=5)
        spaceKey = "~scholer"
        title = "RS001 First test page CzkTW"
        page = server.getPage(spaceKey=spaceKey, pageTitle=title)
        pageId = page['id']
        #pageId = 524310  # edit, testing getPage as well...
        rootPageTitle = "RS Experiments"
        rootPage = server.getPage(spaceKey=spaceKey, pageTitle=rootPageTitle)
        print "\nrootPage:"
        print rootPage
        targetPageId = rootPage['id'] # Remember, 'id' and not 'pageId' !
        server.movePage(pageId, targetPageId=targetPageId)




    #test_login() # currently does not work; the server needs a confighandler.
    #server = test_config1()
    test_getServerInfo()
    test_loginAndSetToken(persist=True)
    #test_loadToken()
    #test_movePage1()
    #test_getPageById()
    #test_getPageByName()




    print "TEST RUN COMPLETE!"



"""

NOTES ON ENCRYPTION:
- Currently using pycrypto with CFB mode AES.
--- I previously used CBC mode, but that requires plaintext and cipertext lenghts being an integer of 16. CFB does not require this.
--- Although according to litterature, OCB mode would be better. But this is patented and not available in pycrypto as far as I can tell.
- SimpleCrypt module also requires pycrypto.
--- Only uses pycrypto for legacy encryption; uses openssl (via process call) for encryption. Not sure how this ports to e.g. windows?
--- Both new and legacy methods uses CBC MODE with AES.
--- It also currently uses random.randint as entrypy provider which is not as good as the random library provided by pycrypto.
- alo-aes 0.3: Does not seem mature; very little documentation.
- pyOCB, https://github.com/kravietz/pyOCB
--- This seems to be a pure-python OCB mode AES cryptography module.
--- When mature, this is probably the best option for small passwords...
- wheezy.security: simple wrapper for pycrypto.

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
