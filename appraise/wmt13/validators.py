# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging

from xml.etree.ElementTree import Element, fromstring, ParseError

from django.core.exceptions import ValidationError

from appraise.settings import LOG_LEVEL, LOG_HANDLER

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.wmt13.validators')
LOGGER.addHandler(LOG_HANDLER)


HIT_REQUIRED_ATTRIBUTES = (
  'block-id', 'source-language', 'target-language'
)


def validate_hits_xml_file(value):
    """
    Validates the given HITs XML source value.
    
    The given value can either be an XML string or an ElementTree.
    
    """
    # First, we try to instantiate an ElementTree from the given value.
    try:
        if isinstance(value, Element):
            _tree = value
        
        else:
            _tree = fromstring(value.encode("utf-8"))
        
        # Then, we check that the top-level tag name is <hits>.
        assert(_tree.tag == 'hits'), 'expected <hits> on top-level'
        
        # Check that all children are valid <hit> elements.
        for _child in _tree:
            validate_hit_xml(_child)
    
    except (AssertionError, ParseError), msg:
        raise ValidationError('Invalid XML: "{0}".'.format(msg))
    
    return value


def validate_hit_xml(value):
    """
    Validates the given single HIT XML source value.
    
    The given value can either be an XML string or an ElementTree.
    
    """
    # First, we try to instantiate an ElementTree from the given value.
    try:
        if isinstance(value, Element):
            _tree = value
        
        else:
            _tree = fromstring(value.encode("utf-8"))
        
        # Then, we check that the top-level tag name is <hits>.
        assert(_tree.tag == 'hit'), 'expected <hit> on top-level'
        
        # Check if there exists a "systems" XML attribute on <hit> level.
        systems_available = 'systems' in _tree.attrib.keys()
        
        # And that required XML attributes are available.
        for _attr in HIT_REQUIRED_ATTRIBUTES:
            assert(_attr in _tree.attrib.keys()), \
              'missing required <hit> attribute {0}'.format(_attr)
        
        # Make sure that block-id is an integer value!
        try:
            _block_id = _tree.attrib['block-id']
            _block_id = int(_block_id)
        
        except ValueError, msg:
            raise ValidationError('Invalid block-id: "{0}", {1}.'.format(
              _block_id, msg))
        
        # Finally, we check that each <hit> contains exactly 3 children
        # which are <seg> containers with <source>, <reference> and a
        # total of 5 <translation> elements. The <reference> is mandatory.
        # The <translation> elements require some text value to be valid.
        _no_of_children = 0
        for _seg in _tree:
            validate_segment_xml(_seg, require_systems=not systems_available)
            _no_of_children += 1
        
        assert(_no_of_children == 3), 'expected 3 <seg> children'
    
    except (AssertionError, ParseError), msg:
        raise ValidationError('Invalid XML: "{0}".'.format(msg))
    
    return value


def validate_segment_xml(value, require_systems=False):
    """
    Checks that the given segment XML value contains all required elements.
    
    These are:
    - one <source> element;
    - one <reference> element; and
    - five <translation> elements.
    
    The given value can either be an XML string or an ElementTree.
    
    """
    try:
        if isinstance(value, Element):
            _tree = value
        
        else:
            _tree = fromstring(value)
        
        if not _tree.tag == 'seg':
            raise ValidationError('Invalid XML: illegal tag: "{0}".'.format(
              _tree.tag))
        
        assert(len(_tree.findall('source')) == 1), \
          'exactly one <source> element expected'
        
        assert(_tree.find('source').text is not None), \
          'missing required <source> text value'
        
        assert(len(_tree.findall('reference')) == 1), \
          'exactly one <reference> element expected'
        
        assert(_tree.find('reference').text is not None), \
          'missing required <reference> text value'
        
        assert(len(_tree.findall('translation')) == 5), \
          'one or more <translation> elements expected'
        
        for _translation in _tree.iterfind('translation'):
            assert(_translation.text is not None), \
              'missing required <translation> text value'
            if require_systems:
                assert('system' in _translation.attrib.keys()), \
                  'missing "system" attribute on <seg> level'
    
    except (AssertionError, ParseError), msg:
        raise ValidationError('Invalid XML: "{0}".'.format(msg))
