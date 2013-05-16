# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging
import uuid

from xml.etree.ElementTree import Element, fromstring, ParseError, tostring

from django.dispatch import receiver

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.template import Context
from django.template.loader import get_template

from appraise.settings import LOG_LEVEL, LOG_HANDLER
from appraise.utils import datetime_to_seconds

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.wmt13.models')
LOGGER.addHandler(LOG_HANDLER)


LANGUAGE_PAIR_CHOICES = (
  ('eng2ces', 'English->Czech'),
  ('eng2deu', 'English->German'),
  ('eng2spa', 'English->Spanish'),
  ('eng2fra', 'English->French'),
  ('eng2rus', 'English->Russian'),
  ('ces2eng', 'Czech->English'),
  ('deu2eng', 'German->English'),
  ('spa2eng', 'Spanish->English'),
  ('fra2eng', 'French->English'),
  ('rus2eng', 'Russian->English'),
)

HIT_REQUIRED_ATTRIBUTES = ('block-id', 'source-language', 'target-language',
 'systems')

def validate_hits_xml_file(value):
    """
    Validates the given HITs XML source value.
    """
    value.encode("utf-8")
    
    # First, we try to instantiate an ElementTree from the given value.
    try:
        _tree = fromstring(value.read())
        
        # Then, we check that the top-level tag name is <hits>.
        assert(_tree.tag == 'hits'), 'expected <hits> on top-level'
        
        # Check that all children are valid <hit> elements.
        for _child in _tree:
            validate_hit_xml(tostring(_child))
    
    except (AssertionError, ParseError), msg:
        raise ValidationError('Invalid XML: "{0}".'.format(msg))
    
    return value


def validate_hit_xml(value):
    """
    Validates the given HIT XML source value.
    """
    # First, we try to instantiate an ElementTree from the given value.
    try:
        _tree = fromstring(value.encode("utf-8"))
        
        # Then, we check that the top-level tag name is <hits>.
        assert(_tree.tag == 'hit'), 'expected <hit> on top-level'
        
        # And that required XML attributes are available.
        for _attr in HIT_REQUIRED_ATTRIBUTES:
            assert(_attr in _tree.attrib.keys()), \
              'missing required <hit> attribute {0}'.format(_attr)
        
        # Finally, we check that each <hit> contains exactly 3 children
        # which are <seg> containers with <source>, <reference> and a
        # total of 5 <translation> elements. The <reference> is optional.
        # The <translation> elements require some text value to be valid.
            _no_of_children = 0
            for _seg in _tree:
                validate_item_xml(_seg)
                _no_of_children += 1
            
            assert(_no_of_children == 3), 'required 3 <seg> children'
    
    except (AssertionError, ParseError), msg:
        raise ValidationError('Invalid XML: "{0}".'.format(msg))
    
    return value


# pylint: disable-msg=E1101
class HIT(models.Model):
    """
    HIT object model for WMT13 ranking evaluation.
    
    Each HIT contains 3 RankingTask instances for 3 consecutive sentences.
    
    """
    hit_id = models.CharField(
      max_length=8,
      db_index=True,
      unique=True,
      editable=False,
      help_text="Unique identifier for this HIT instance.",
      verbose_name="HIT identifier"
    )
    
    block_id = models.IntegerField(
      db_index=True,
      help_text="Block ID for this HIT instance.",
      verbose_name="HIT block identifier"
    )

    hit_xml = models.TextField(
      help_text="XML source for this HIT instance.",
      validators=[validate_hit_xml],
      verbose_name="HIT source XML"
    )

    language_pair = models.CharField(
      max_length=7,
      choices=LANGUAGE_PAIR_CHOICES,
      db_index=True,
      help_text="Language pair choice for this HIT instance.",
      verbose_name="Language pair"
    )

    # This is derived from hit_xml and NOT stored in the database.
    hit_attributes = {}

    users = models.ManyToManyField(
      User,
      blank=True,
      db_index=True,
      null=True,
      help_text="Users who work on this HIT instance."
    )

    active = models.BooleanField(
      db_index=True,
      default=True,
      help_text="Indicates that this HIT instance is still in use.",
      verbose_name="Active?"
    )

    class Meta:
        """
        Metadata options for the HIT object model.
        """
        ordering = ('block_id', 'language_pair', 'hit_id')
        verbose_name = "HIT instance"
        verbose_name_plural = "HIT instances"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.hit_attributes are available.
        """
        super(HIT, self).__init__(*args, **kwargs)
        
        if not self.hit_id:
            self.hit_id = self.__class__._create_hit_id()
        
        # If a hit_xml file is available, populate self.hit_attributes.
        self.reload_dynamic_fields()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this HIT object.
        """
        return u'<HIT id="{0}">'.format(self.id)
    
    @classmethod
    def _create_hit_id(cls):
        """Creates a random UUID-4 8-digit hex number for use as HIT id."""
        new_id = uuid.uuid4().hex[:8]
        while cls.objects.filter(hit_id=new_id):
            new_id = uuid.uuid4().hex[:8]
        
        return new_id
    
    def save(self, *args, **kwargs):
        """
        Makes sure that validation is run before saving an object instance.
        """
        # Enforce validation before saving HIT objects.
        if not self.id:
            self.full_clean()
            
            # We have to call save() here to get an id for this instance.
            super(HIT, self).save(*args, **kwargs)
            
            _tree = fromstring(self.hit_xml.encode("utf-8"))
            
            for _child in _tree:
                new_item = RankingTask(hit=self, item_xml=tostring(_child))
                new_item.save()
        
        super(HIT, self).save(*args, **kwargs)
    
    def get_absolute_url(self):
        """
        Returns the URL for this HIT object instance.
        """
        hit_handler_view = 'appraise.wmt13.views.hit_handler'
        kwargs = {'hit_id': self.hit_id}
        return reverse(hit_handler_view, kwargs=kwargs)
    
    def get_status_url(self):
        """
        Returns the status URL for this HIT object instance.
        """
        status_handler_view = 'appraise.wmt13.views.status_view'
        kwargs = {'hit_id': self.hit_id}
        return reverse(status_handler_view, kwargs=kwargs)
    
    def reload_dynamic_fields(self):
        """
        Reloads hit_attributes from self.hit_xml contents.
        """
        # If a hit_xml file is available, populate self.hit_attributes.
        if self.hit_xml:
            try:
                _hit_xml = fromstring(self.hit_xml.read())
                self.hit_attributes = {}
                for key, value in _hit_xml.attrib.items():
                    self.hit_attributes[key] = value
            
            # For parse errors, set self.hit_attributes s.t. it gives an
            # error message to the user for debugging.
            except (ParseError), msg:
                self.hit_attributes = {
                  'note': msg,
                }
    
    def get_status_header(self):
        """
        Returns the header template for this type of HIT objects.
        """
        # pylint: disable-msg=E1101
        _header = ['Overall completion', 'Average duration']
        return _header
    
    # TODO: check this code.
    def get_status_for_user(self, user=None):
        """
        Returns the status information with respect to the given user.
        """
        _status = []
        
        # Compute completion status for this task and the given user.
        _items = RankingTask.objects.filter(task=self).count()
        _done = RankingResult.objects.filter(user=user,
          item__task=self).count()
        
        _status.append('{0}/{1}'.format(_done, _items))
        _percentage = 100*_done/float(_items or 1)
        _status.append(_percentage)
        if _percentage < 33:
            _status.append(' progress-danger')
        elif _percentage < 66:
            _status.append(' progress-warning')
        else:
            _status.append(' progress-success')
        
        # Compute average duration for this task and the given user.
        _results = RankingResult.objects.filter(user=user, item__task=self)
        _durations = _results.values_list('duration', flat=True)
        
        _durations = [datetime_to_seconds(d) for d in _durations if d]
        _average_duration = sum(_durations) / (float(len(_durations)) or 1)
        
        _status.append('{:.2f} sec'.format(_average_duration))
        
        return _status
    
    # TODO: check this code.
    def get_status_for_users(self):
        """
        Returns the status information with respect to all users.
        """
        _status = []
        
        # Compute completion status for this task and all possible users.
        _items = RankingTask.objects.filter(task=self).count()
        _done = []
        
        for user in self.users.all():
            _done.append(RankingResult.objects.filter(user=user,
              item__task=self).count())
        
        # Minimal number of completed items counts here.
        _status.append('{0}/{1}'.format(min(_done or [0]), _items))
        _percentage = 100*min(_done or [0])/float(_items or 1)
        _status.append(_percentage)
        if _percentage < 33:
            _status.append(' progress-danger')
        elif _percentage < 66:
            _status.append(' progress-warning')
        else:
            _status.append(' progress-success')
        
        # Compute average duration for this task and all possible users.
        _durations = []

        for user in self.users.all():
            _results = RankingResult.objects.filter(user=user,
              item__task=self)
            _durations.extend(_results.values_list('duration', flat=True))
        
        _durations = [datetime_to_seconds(d) for d in _durations if d]
        _average_duration = sum(_durations) / (float(len(_durations)) or 1)
        
        _status.append('{:.2f} sec'.format(_average_duration))
        
        return _status
    
    # TODO: check this code. (delete?)
    def is_finished_for_user(self, user=None):
        """
        Returns True if this task is finished for the given user.
        """
        _items = RankingTask.objects.filter(task=self).count()
        _done = RankingResult.objects.filter(user=user,
          item__task=self).count()
        return _items == _done
    
    # TODO: check this code. (delete?)
    def get_finished_for_user(self, user=None):
        """
        Returns tuple (finished, total) number of items for the given user.
        """
        _items = RankingTask.objects.filter(task=self).count()
        _done = RankingResult.objects.filter(user=user,
          item__task=self).count()
        return (_done, _items)

    # TODO: check this code.
    def export_to_xml(self):
        """
        Renders this HIT as XML String.
        """
        template = get_template('evaluation/result_task.xml')
        
        # If a hit_xml file is available, populate self.hit_attributes.
        self.reload_dynamic_fields()
        
        _attr = self.hit_attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        results = []
        for item in RankingTask.objects.filter(task=self):
            for _result in item.evaluationresult_set.all():
                results.append(_result.export_to_xml())
        
        context = {'task_type': 'ranking', 'attributes': attributes,
          'results': results}
        return template.render(Context(context))


def validate_item_xml(value):
    """
    Checks that item_xml contains source, reference, and 5 translation tags.
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
        
        if _tree.find('reference') is not None:
            assert(_tree.find('reference').text is not None), \
              'missing required <reference> text value'
        
        assert(len(_tree.findall('translation')) == 5), \
          'one or more <translation> elements expected'
        
        for _translation in _tree.iterfind('translation'):
            assert(_translation.text is not None), \
              'missing required <translation> text value'
    
    except (AssertionError, ParseError), msg:
        raise ValidationError('Invalid XML: "{0}".'.format(msg))


class RankingTask(models.Model):
    """
    RankingTask object model for WMT13 ranking evaluation.
    """
    task = models.ForeignKey(
      HIT,
      db_index=True
    )
    
    item_xml = models.TextField(
      help_text="XML source for this RankingTask instance.",
      validators=[validate_item_xml],
      verbose_name="RankingTask source XML"
    )
    
    # These fields are derived from item_xml and NOT stored in the database.
    attributes = None
    source = None
    reference = None
    translations = None
    
    class Meta:
        """
        Metadata options for the RankingTask object model.
        """
        ordering = ('id',)
        verbose_name = "RankingTask instance"
        verbose_name_plural = "RankingTask instances"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.translations are available.
        """
        super(RankingTask, self).__init__(*args, **kwargs)
        
        # If item_xml is available, populate dynamic fields.
        self.reload_dynamic_fields()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this RankingTask object.
        """
        return u'<ranking-task id="{0}">'.format(self.id)

    def save(self, *args, **kwargs):
        """
        Makes sure that validation is run before saving an object instance.
        """
        # Enforce validation before saving RankingTask objects.
        self.full_clean()        
        
        super(RankingTask, self).save(*args, **kwargs)
    
    def reload_dynamic_fields(self):
        """
        Reloads source, reference, and translations from self.item_xml.
        """
        if self.item_xml:
            try:
                _item_xml = fromstring(self.item_xml)
                
                self.attributes = _item_xml.attrib
                
                _source = _item_xml.find('source')
                if _source is not None:
                    self.source = (_source.text, _source.attrib)

                _reference = _item_xml.find('reference')
                if _reference is not None:
                    self.reference = (_reference.text, _reference.attrib)
                
                self.translations = []
                for _translation in _item_xml.iterfind('translation'):
                    self.translations.append((_translation.text,
                      _translation.attrib))
            
            except ParseError:
                self.source = None
                self.reference = None
                self.translations = None


class RankingResult(models.Model):
    """
    Evaluation Result object model.
    """
    item = models.ForeignKey(
      RankingTask,
      db_index=True
    )
    
    user = models.ForeignKey(
      User,
      db_index=True
    )
    
    duration = models.TimeField(blank=True, null=True, editable=False)
    
    def readable_duration(self):
        """
        Returns a readable version of the this RankingResult's duration.
        """
        return '{}'.format(self.duration)
    
    raw_result = models.TextField(editable=False, blank=False)
    
    results = None
    
    class Meta:
        """
        Metadata options for the RankingResult object model.
        """
        ordering = ('id',)
        verbose_name = "RankingResult object"
        verbose_name_plural = "RankingResult objects"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.results are available.
        """
        super(RankingResult, self).__init__(*args, **kwargs)
        
        # If raw_result is available, populate dynamic field.
        self.reload_dynamic_fields()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this RankingResult object.
        """
        return u'<ranking-result id="{0}">'.format(self.id)
    
    def reload_dynamic_fields(self):
        """
        Reloads source, reference, and translations from self.item_xml.
        """
        if self.raw_result and self.raw_result != 'SKIPPED':
            try:
                self.results = self.raw_result.split(',')
                self.results = [int(x) for x in self.results]
            
            # pylint: disable-msg=W0703
            except Exception, msg:
                self.results = msg
    
    def export_to_xml(self):
        """
        Renders this RankingResult as XML String.
        """
        return self.export_to_ranking_xml()
    
    def export_to_ranking_xml(self):
        """
        Renders this RankingResult as Ranking XML String.
        """
        template = get_template('evaluation/result_ranking.xml')
        
        _attr = self.item.attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        skipped = self.results is None
        
        translations = []
        if not skipped:
            for index, translation in enumerate(self.item.translations):
                _items = translation[1].items()
                _attr = ' '.join(['{}="{}"'.format(k, v) for k, v in _items])
                _rank = self.results[index]
                translations.append((_attr, _rank))
        
        context = {
          'attributes': attributes,
          'duration': '{}'.format(self.duration),
          'skipped': skipped,
          'translations': translations,
          'user': self.user,
        }
        
        return template.render(Context(context))


# pylint: disable-msg=E1101
class UserHITMapping(models.Model):
    """
    Object model mapping users to their current HIT instances.
    """
    user = models.ForeignKey(
      User,
      db_index=True
    )
    hit = models.ForeignKey(
      HIT,
      db_index=True
    )

    class Meta:
        """
        Metadata options for the UserHITMapping object model.
        """
        verbose_name = "User/HIT mapping instance"
        verbose_name_plural = "User/HIT mapping instances"
