# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import logging
import uuid

from xml.etree.ElementTree import Element, fromstring, ParseError, tostring

from django.dispatch import receiver

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.template import Context
from django.template.loader import get_template

from appraise.settings import LOG_LEVEL, LOG_HANDLER
from appraise.utils import datetime_to_seconds

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.evaluation.models')
LOGGER.addHandler(LOG_HANDLER)


APPRAISE_TASK_TYPE_CHOICES = (
  ('1', 'Quality Checking'),
  ('2', 'Ranking'),
  ('3', 'Post-editing'),
  ('4', 'Error classification'),
  ('5', '3-Way Ranking'),
)


def validate_source_xml_file(value):
    """
    Validates the given XML source value.
    """
    value.open()
    
    # First, we try to instantiate an ElementTree from the given value.
    try:
        _tree = fromstring(value.read())
        
        # Then, we check that the top-level tag name is <set>.
        assert(_tree.tag == 'set'), 'expected <set> on top-level'
        
        # And that required XML attributes are available.
        for _attr in ('id', 'source-language', 'target-language'):
            assert(_attr in _tree.attrib.keys()), \
              'missing required <set> attribute {0}'.format(_attr)
        
        # Finally, we check that all children of <set> are <seg> containers
        # and make sure that each <seg> element contains at least a <source>
        # and one <translation> element.  The <translation> elements require
        # at least one XML attribute "system" and some value to be valid.
        for _child in _tree:
            validate_item_xml(_child)
    
    except (AssertionError, ParseError), msg:
        raise ValidationError('Invalid XML: "{0}".'.format(msg))
    
    value.close()
    return value


class EvaluationTask(models.Model):
    """
    Evaluation Task object model.
    """
    task_id = models.CharField(
      max_length=32,
      db_index=True,
      unique=True,
      editable=False,
      help_text="Unique task identifier for this evaluation task.",
      verbose_name="Task identifier"
    )

    task_name = models.CharField(
      max_length=100,
      db_index=True,
      help_text="Unique, descriptive name for this evaluation task.",
      unique=True,
      verbose_name="Task name"
    )

    task_type = models.CharField(
      max_length=1,
      choices=APPRAISE_TASK_TYPE_CHOICES,
      db_index=True,
      help_text="Type choice for this evaluation task.",
      verbose_name="Task type"
    )

    task_xml = models.FileField(
      upload_to='source-xml',
      help_text="XML source file for this evaluation task.",
      validators=[validate_source_xml_file],
      verbose_name="Task XML source"
    )
    
    # This is derived from task_xml and NOT stored in the database.
    task_attributes = {}

    description = models.TextField(
      blank=True,
      help_text="(Optional) Text describing this evaluation task.",
      verbose_name="Description"
    )

    users = models.ManyToManyField(
      User,
      blank=True,
      null=True,
      help_text="(Optional) Users allowed to work on this evaluation task."
    )

    active = models.BooleanField(
      db_index=True,
      default=True,
      help_text="Indicates that this evaluation task is still in use.",
      verbose_name="Active?"
    )

    class Meta:
        """
        Metadata options for the EvaluationTask object model.
        """
        ordering = ('task_name', 'task_type', 'task_id')
        verbose_name = "EvaluationTask object"
        verbose_name_plural = "EvaluationTask objects"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.task_attributes are available.
        """
        super(EvaluationTask, self).__init__(*args, **kwargs)
        
        if not self.task_id:
            self.task_id = self.__class__._create_task_id()
        
        # If a task_xml file is available, populate self.task_attributes.
        self.reload_dynamic_fields()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this EvaluationTask object.
        """
        return u'<evaluation-task id="{0}">'.format(self.id)
    
    @classmethod
    def _create_task_id(cls):
        """Creates a random UUID-4 32-digit hex number for use as task id."""
        new_id = uuid.uuid4().hex
        while cls.objects.filter(task_id=new_id):
            new_id = uuid.uuid4().hex
        
        return new_id
    
    def save(self, *args, **kwargs):
        """
        Makes sure that validation is run before saving an object instance.
        """
        # Enforce validation before saving EvaluationTask objects.
        if not self.id:
            self.full_clean()
            
            # We have to call save() here to get an id for this task.
            super(EvaluationTask, self).save(*args, **kwargs)
            
            self.task_xml.open()
            _tree = fromstring(self.task_xml.read())
            self.task_xml.close()
            
            for _child in _tree:
                new_item = EvaluationItem(task=self,
                  item_xml=tostring(_child))
                new_item.save()
        
        super(EvaluationTask, self).save(*args, **kwargs)
    
    def reload_dynamic_fields(self):
        """
        Reloads task_attributes from self.task_xml contents.
        """
        # If a task_xml file is available, populate self.task_attributes.
        if self.task_xml:
            try:
                _task_xml = fromstring(self.task_xml.read())
                self.task_attributes = {}
                for key, value in _task_xml.attrib.items():
                    self.task_attributes[key] = value
            
            except ParseError:
                self.task_attributes = {}
    
    def get_status_header(self):
        """
        Returns the header template for this type of EvaluationTask objects.
        """
        # pylint: disable-msg=E1101
        _task_type = self.get_task_type_display()
        _header = ['Overall completion', 'Average duration']
        
        if _task_type == 'Quality Checking':
            pass
        
        elif _task_type == 'Ranking':
            pass
        
        elif _task_type == 'Post-editing':
            pass
        
        elif _task_type == 'Error classification':
            pass
        
        elif _task_type == '3-Way Ranking':
            pass
        
        return _header
    
    def get_status_for_user(self, user=None):
        """
        Returns the status information with respect to the given user.
        """
        # pylint: disable-msg=E1101
        _task_type = self.get_task_type_display()
        _status = []
        
        # Compute completion status for this task and the given user.
        _items = EvaluationItem.objects.filter(task=self).count()
        _done = EvaluationResult.objects.filter(user=user,
          item__task=self).count()
        
        _status.append('{0}/{1}'.format(_done, _items))
        
        # Compute average duration for this task and the given users
        _results = EvaluationResult.objects.filter(user=user, item__task=self)
        _durations = _results.values_list('duration', flat=True)
        
        _durations = [datetime_to_seconds(d) for d in _durations]
        _average_duration = reduce(lambda x, y: (x+y)/2.0, _durations, 0)
        
        _status.append('{:.2f} sec'.format(_average_duration))
        
        # We could add task type specific status information here.
        if _task_type == 'Quality Checking':
            pass
        
        elif _task_type == 'Ranking':
            pass
        
        elif _task_type == 'Post-editing':
            pass
        
        elif _task_type == 'Error classification':
            pass
        
        elif _task_type == '3-Way Ranking':
            pass
        
        return _status
    
    def is_finished_for_user(self, user=None):
        """
        Returns True if this task is finished for the given user.
        """
        _items = EvaluationItem.objects.filter(task=self).count()
        _done = EvaluationResult.objects.filter(user=user,
          item__task=self).count()
        return _items == _done
    
    def get_finished_for_user(self, user=None):
        """
        Returns tuple (finished, total) number of items for the given user.
        """
        _items = EvaluationItem.objects.filter(task=self).count()
        _done = EvaluationResult.objects.filter(user=user,
          item__task=self).count()
        return (_done, _items)

    def export_to_xml(self):
        """
        Renders this EvaluationTask as XML String.
        """
        template = get_template('evaluation/result_task.xml')
        
        # pylint: disable-msg=E1101
        _task_type = self.get_task_type_display().lower().replace(' ', '-')
        
        _attr = self.task_attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        results = []
        for item in EvaluationItem.objects.filter(task=self):
            for _result in item.evaluationresult_set.all():
                results.append(_result.export_to_xml())
        
        context = {'task_type': _task_type, 'attributes': attributes,
          'results': results}
        return template.render(Context(context))


@receiver(models.signals.pre_delete, sender=EvaluationTask)
def remove_task_xml_file_on_delete(sender, instance, **kwargs):
    """
    Removes the task_xml file when the EvaluationTask instance is deleted.
    """
    # We have to use save=False as otherwise validation would fail ;)
    if len(instance.task_xml.name):
        instance.task_xml.delete(save=False)


def validate_item_xml(value):
    """
    Checks that item_xml contains source, reference, some translation tags.
    """
    try:
        if isinstance(value, Element):
            _tree = value
        
        else:
            _tree = fromstring(value)
        
        if not _tree.tag == 'seg':
            raise ValidationError('Invalid XML: illegal tag: "{0}".'.format(
              _tree.tag))
        
        for _attr in ('id', 'doc-id'):
            assert(_attr in _tree.attrib.keys()), \
              'missing required <seg> attribute {0}'.format(_attr)
        
        assert(len(_tree.findall('source')) == 1), \
          'exactly one <source> element expected'
        
        assert(_tree.find('source').text is not None), \
          'missing required <source> text value'
        
        if _tree.find('reference') is not None:
            assert(_tree.find('reference').text is not None), \
              'missing required <reference> text value'
        
        assert(len(_tree.findall('translation')) >= 1), \
          'one or more <translation> elements expected'
        
        for _translation in _tree.iterfind('translation'):
            assert('system' in _translation.attrib.keys()), \
              'missing required <translation> attribute "system"'
            
            assert(_translation.text is not None), \
              'missing required <translation> text value'
    
    except (AssertionError, ParseError), msg:
        raise ValidationError('Invalid XML: "{0}".'.format(msg))


class EvaluationItem(models.Model):
    """
    Evaluation Item object model.
    """
    task = models.ForeignKey(EvaluationTask)
    
    item_xml = models.TextField(
      help_text="XML source for this evaluation item.",
      validators=[validate_item_xml],
      verbose_name="Translations XML source"
    )
    
    # These fields are derived from item_xml and NOT stored in the database.
    attributes = None
    source = None
    reference = None
    translations = None
    
    class Meta:
        """
        Metadata options for the EvaluationItem object model.
        """
        ordering = ('id',)
        verbose_name = "EvaluationItem object"
        verbose_name_plural = "EvaluationItem objects"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.translations are available.
        """
        super(EvaluationItem, self).__init__(*args, **kwargs)
        
        # If item_xml is available, populate dynamic fields.
        self.reload_dynamic_fields()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this EvaluationItem object.
        """
        return u'<evaluation-item id="{0}">'.format(self.id)

    def save(self, *args, **kwargs):
        """
        Makes sure that validation is run before saving an object instance.
        """
        # Enforce validation before saving EvaluationItem objects.
        self.full_clean()        
        
        super(EvaluationItem, self).save(*args, **kwargs)
    
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


class EvaluationResult(models.Model):
    """
    Evaluation Result object model.
    """
    item = models.ForeignKey(EvaluationItem)
    user = models.ForeignKey(User)
    
    duration = models.TimeField(blank=True, null=True, editable=False)
    
    # TODO: this is a hack to render datetime.datetime information properly...
    #
    # Should be replaced by code within the corresponding ModelAdmin!
    def _duration(self):
        return '{}'.format(self.duration)
    
    raw_result = models.TextField(editable=False, blank=False)
    
    results = None
    
    class Meta:
        """
        Metadata options for the EvaluationResult object model.
        """
        ordering = ('id',)
        verbose_name = "EvaluationResult object"
        verbose_name_plural = "EvaluationResult objects"
    
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.results are available.
        """
        super(EvaluationResult, self).__init__(*args, **kwargs)
        
        # If raw_result is available, populate dynamic field.
        self.reload_dynamic_fields()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this EvaluationResult object.
        """
        return u'<evaluation-result id="{0}">'.format(self.id)
    
    def reload_dynamic_fields(self):
        """
        Reloads source, reference, and translations from self.item_xml.
        """
        if self.raw_result and self.raw_result != 'SKIPPED':
            _task_type = self.item.task.get_task_type_display()
            try:
                if _task_type == 'Quality Checking':
                    self.results = self.raw_result
                
                elif _task_type == 'Ranking':
                    self.results = self.raw_result.split(',')
                    self.results = [int(x) for x in self.results]
                
                elif _task_type == 'Post-editing':
                    self.results = self.raw_result.split('\n')
                
                elif _task_type == 'Error classification':
                    self.results = self.raw_result.split('\n')
                    self.results = [x.split('=') for x in self.results]
                
                elif _task_type == '3-Way Ranking':
                    self.results = self.raw_result
            
            # pylint: disable-msg=W0703
            except Exception, msg:
                self.results = msg
    
    def export_to_xml(self):
        """
        Renders this EvaluationResult as XML String.
        """
        _task_type = self.item.task.get_task_type_display()
        if _task_type == 'Quality Checking':
            return self.export_to_quality_checking_xml()
        
        elif _task_type == 'Ranking':
            return self.export_to_ranking_xml()
        
        elif _task_type == 'Post-editing':
            return self.export_to_postediting_xml()
        
        elif _task_type == 'Error classification':
            return self.export_to_error_classification_xml()
        
        elif _task_type == '3-Way Ranking':
            return self.export_to_three_way_ranking_xml()
    
    def export_to_quality_checking_xml(self):
        """
        Renders this EvaluationResult as Quality Checking XML String.
        """
        pass
    
    def export_to_ranking_xml(self):
        """
        Renders this EvaluationResult as Ranking XML String.
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
        
        context = {'attributes': attributes, 'user': self.user,
          'duration': '{}'.format(self.duration), 'skipped': skipped,
          'translations': translations}
        return template.render(Context(context))
    
    def export_to_postediting_xml(self):
        """
        Renders this EvaluationResult as Post-editing XML String.
        """
        template = get_template('evaluation/result_postediting.xml')
        
        _attr = self.item.attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        if self.results:
            from_scratch = self.results[0] == 'FROM_SCRATCH'
            if from_scratch:
                edit_id = self.results[1]
            else:
                edit_id = self.results[0]
            
            postedited = self.results[-1]
        
        skipped = self.results is None
        
        _attr = self.item.translations[int(edit_id)][1].items()
        _export_attr = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        context = {'attributes': attributes, 'user': self.user,
          'duration': '{}'.format(self.duration), 'skipped': skipped,
          'from_scratch': from_scratch, 'edit_id': edit_id,
          'translation_attributes': _export_attr,
          'postedited': postedited.encode('utf-8')}
        return template.render(Context(context))
    
    def export_to_error_classification_xml(self):
        """
        Renders this EvaluationResult as Error Classification XML String.
        """
        template = get_template('evaluation/result_error_classification.xml')
        
        _attr = self.item.attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        errors = []
        too_many_errors = False
        missing_words = False
        
        if self.results:
            for error in self.results:
                if len(error) == 2:
                    word_id = int(error[0])
                    for details in error[1].split(','):
                        error_class, severity = details.split(':')
                        errors.append((word_id, error_class, severity))
                
                elif error[0] == 'MISSING_WORDS':
                    missing_words = True
                
                elif error[0] == 'TOO_MANY_ERRORS':
                    too_many_errors = True
        
        # Sort by increasing word id.
        errors.sort()
        
        skipped = self.results is None
        
        context = {'attributes': attributes, 'user': self.user,
          'duration': '{}'.format(self.duration), 'skipped': skipped,
          'too_many_errors': too_many_errors, 'missing_words': missing_words,
          'errors': errors}
        return template.render(Context(context))
    
    def export_to_three_way_ranking_xml(self):
        """
        Renders this EvaluationResult as 3-Way Ranking XML String.
        """
        pass
    
