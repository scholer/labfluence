import os
import yaml
import re
from datetime import datetime
from collections import OrderedDict
import xmlrpclib
#import hashlib
#import fnmatch
import logging
logger = logging.getLogger(__name__)

# Labfluence modules and classes:
from page import WikiPage, WikiPageFactory
from journalassistant import JournalAssistant
from filemanager import Filemanager
from utils import increment_idx, idx_generator, asciize
from decorators.cache_decorator import cached_property
#from decorators.deprecated_decorator import deprecated


class Experiment(object):
    """
    This class is the main model for a somewhat abstract "Experiment".
    See module docstring for further info.
    """

    def __init__(self, localdir, confighandler):
        """
        Arguments:
        - localdir: path string
        """
        self.VERBOSE = 0
        self.Confighandler = confighandler
        # Attaching of wiki pages is done lazily on first call. _autoattachwikipage is not really used.
        self.ConfigFn = '.labfluence.yml'
        # For use without a confighandler:
        self._props = dict()
        self._expid = None
        self._cache = dict() # cached_property cache
        self._allowmanualpropssavetofile = False # Set to true if you want to let this experiment handle Props file persisting without a confighandler.
        self._doserversearch = False
        localdir = localdir or props.get('localdir')
        if makelocaldir:
            logger.debug("makelocaldir is boolean True, invoking self.makeLocaldir(props=%s, localdir=%s)", props, localdir)
            localdir = self.makeLocaldir(props) # only props currently supported...
            logger.debug("localdir after makeLocaldir: %s", localdir)
        if localdir:
            self.setLocaldirpathAndFoldername(localdir)
        else:
            logger.debug("localdir is: %s (and makelocaldir was: %s), setting Localdirpath, Foldername and Parentdirpath to None.", localdir, makelocaldir)
            logger.info( "NOTICE: No localdir provided for this experiment (are you in test mode?)\
functionality of this object will be greatly reduced and may break at any time.\
props=%s, regex_match=%s, wikipage='%s'", props, regex_match, wikipage)
            self.Localdirpath, self.Foldername, self.Parentdirpath = None, None, None

        ### Experiment properties/config related
        ### Manual handling is deprecated; Props are now a property that deals soly with confighandler.
        if props:
            self.Props.update(props)
            logger.debug("Experiment %s updated with props argument, is now %s", self, self.Props)
        if regex_match:
            gd = regex_match.groupdict()
            # In case the groupdict has multiple date fields, find out which one to use and discart the other keys:
            gd['date'] = next( ( date for date in [gd.pop(k, None) for k in ('date1', 'date2', 'date')] if date ), None )
            ## regex is often_like "(?P<expid>RS[0-9]{3}) (?P<exp_title_desc>.*)"
            self.Props.update(gd)
        elif not 'expid' in self.Props:
            logger.debug("self.Props is still too empty (no expid field). Attempting to populate it using 1) the localdirpath and 2) the wikipage.")
            if self.Foldername:
                regex_match = self.updatePropsByFoldername()
            if not regex_match and wikipage: # equivalent to 'if wikipage and not regex_match', but better to check first:
                regex_match = self.updatePropsByWikipage()

        ### Subentries related - Subentries are stored as an element in self.Props ###
        # self.Subentries = self.Props.setdefault('exp_subentries', OrderedDict()) # Is now a property
        if doparseLocaldirSubentries and self.Localdirpath:
            self.parseLocaldirSubentries()

        if makewikipage and not self.WikiPage: # will attempt auto-attaching
            # page attaching should only be done if you are semi-sure that a page does not already exist.
            # trying to attach a wiki page will see if a page already exist.
            self.makeWikiPage()

    @property
    def Props(self):
        """
        If localdirpath is provided, use that to get props from the confighandler.
        """
        if self.Localdirpath:
            props = self.Confighandler.getExpConfig(self.Localdirpath)
        else:
            props_cache = self.Confighandler.get('expprops_by_id_cache')
            _expid = getattr(self, '_expid', None)
            if props_cache and _expid:
                props = props_cache.setdefault(_expid, dict())
            else:
                if not hasattr(self, '_props'):
                    logger.debug("Setting self._props = dict()")
                    self._props = dict()
                props = self._props
                logger.debug("(test mode?) self.Localdirpath is '%s', props_cache type: %s, self._expid is: %s, returning props: %s",
                               getattr(self, 'Localdirpath', '<not set>'), type(props_cache), _expid, props)
        try:
            wikipage = self._wikipage # Do NOT try to use self.WikiPage. self.WikiPage calls self.attachWikiPage which calls self.Props -- circular loop.
            if not props.get('wiki_pagetitle') and wikipage and wikipage.Struct \
                        and props.get('wiki_pagetitle') != wikipage.Struct['title']:
                logger.info("Updating experiment props['wiki_pagetitle'] to '%s'", wikipage.Struct['title'])
                props['wiki_pagetitle'] = wikipage.Struct['title']
        except AttributeError as e:
            logger.debug("AttributeError: %s", e)
        return props
    @property
    def Subentries(self):
        """Should always be located one place and one place only: self.Props."""
        return self.Props.setdefault('exp_subentries', OrderedDict())
    @Subentries.setter
    def Subentries(self, subentries):
        """property setter"""
        self.Props['exp_subentries'] = subentries

