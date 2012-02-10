# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
from xml.etree.ElementTree import Element, fromstring, ParseError, tostring

import logging
import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.template import Context
from django.template.loader import get_template
from appraise.settings import LOG_LEVEL, LOG_HANDLER

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.evaluation.models')
LOGGER.addHandler(LOG_HANDLER)


def _create_id():
    """Creates a random UUID-4 32-digit hex number for use as task id."""
    new_id = uuid.UUID(bytes=os.urandom(16), version=4).hex
    #new_id = uuid.uuid4().hex
    ###while EvaluationTask.objects.filter(task_id=new_id):
    ###    new_id = uuid.uuid4().hex

    #while (RankingTask.objects.filter(task_id=new_id) or
    #  EditingTask.objects.filter(task_id=new_id)):
    #    new_id = uuid.uuid4().hex

    return new_id


from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.db.models.signals import pre_delete

APPRAISE_TASK_TYPE_CHOICES = (
  ('1', 'Quality Checking'),
  ('2', 'Ranking'),
  ('3', 'Post-editing'),
  ('4', 'Error classification'),
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

# TODO: decide on status information such as creation_date, modification_date,
#   and owner/creator.
#
# Static method to perform the import process; this will roll-back any changes
#   in case of errors to avoid polluting the database.  Also, existing objects
#   with identical information will be re-used to avoid duplication.
class EvaluationTask(models.Model):
    """
    Evaluation Task object model.
    """
    task_id = models.CharField(
      max_length=32,
      db_index=True,
      default=_create_id(),
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
        
        # If a task_xml file is available, populate self.task_attributes.
        self.reload_dynamic_fields()
    
    def __unicode__(self):
        """
        Returns a Unicode String for this EvaluationTask object.
        """
        return u'<evaluation-task id="{0}">'.format(self.id)
    
    def save(self, *args, **kwargs):
        """
        Makes sure that validation is run before saving an object instance.
        """
        # Enforce validation before saving EvaluationTask objects.
        if not self.id:
            self.full_clean()
            
            # TODO: decide on validation of task type -- do we want to do this
            # or do we just validate the "general" XML format; raising an
            # error in view/edit mode only?
            
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
        
        return _header
    
    def get_status_for_user(self, user=None):
        """
        Returns the status information with respect to the given user.
        """
        # pylint: disable-msg=E1101
        _task_type = self.get_task_type_display()
        _status = []
        
        _items = EvaluationItem.objects.filter(task=self).count()
        _done = EvaluationResult.objects.filter(user=user, item__task=self).count()
        
        _status.append('{0}/{1}'.format(_done, _items))
        
        _results = EvaluationResult.objects.filter(item__task=self)
        _durations = _results.values_list('duration', flat=True)
        _average_duration = 0
        for duration in _durations:
            _duration = duration.hour * 3600 + duration.minute * 60 \
              + duration.second + (duration.microsecond / 1000000.0)

            _average_duration += _duration
        
        if len(_durations):
            _average_duration /= float(len(_durations))
        
        else:
            _average_duration = 0
        
        _status.append('{:.2f} sec'.format(_average_duration))
        
        if _task_type == 'Quality Checking':
            pass
        
        elif _task_type == 'Ranking':
            pass
        
        elif _task_type == 'Post-editing':
            pass
        
        elif _task_type == 'Error classification':
            pass
        
        return _status
    
    def is_finished_for_user(self, user=None):
        """
        Returns True if this task is finished for the given user.
        """
        _items = EvaluationItem.objects.filter(task=self).count()
        _done = EvaluationResult.objects.filter(user=user, item__task=self).count()
        return _items == _done

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


@receiver(pre_delete, sender=EvaluationTask)
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
                if _task_type == 'Ranking':
                    self.results = [int(x) for x in self.raw_result.split(',')]
                
                elif _task_type == 'Error classification':
                    self.results = [x.split('=') for x in self.raw_result.split('\n')]
                
                elif _task_type == 'Post-editing':
                    self.results = self.raw_result.split('\n')
            
            # pylint: disable-msg=W0703
            except Exception, msg:
                self.results = msg
    
    def export_to_xml(self):
        """
        Renders this EvaluationResult as XML String.
        """
        _task_type = self.item.task.get_task_type_display()
        if _task_type == 'Ranking':
            return self.export_to_ranking_xml()
        
        elif _task_type == 'Error classification':
            return self.export_to_error_classification_xml()
        
        elif _task_type == 'Post-editing':
            return self.export_to_postediting_xml()
    
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
        
        skipped = self.results is None
        
        context = {'attributes': attributes, 'user': self.user,
          'duration': '{}'.format(self.duration), 'skipped': skipped,
          'too_many_errors': too_many_errors, 'missing_words': missing_words,
          'errors': errors}
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
        translation_attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        context = {'attributes': attributes, 'user': self.user,
          'duration': '{}'.format(self.duration), 'skipped': skipped,
          'from_scratch': from_scratch, 'edit_id': edit_id,
          'translation_attributes': translation_attributes,
          'postedited': postedited.encode('utf-8')}
        return template.render(Context(context))

class RankingTask(models.Model):
    """An RankingTask represents a set of ranking/classification tasks."""
    shortname = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    users = models.ManyToManyField(
      User,
      blank=True,
      help_text="Users allowed to work on this ranking/classification task."
    )
    task_id = models.CharField(max_length=32, default=_create_id())

    def __unicode__(self):
        """Returns a Unicode String representation of the ranking task."""
        return u'<ranking-task id="{0}" name="{1}">'.format(self.id,
          self.shortname)

    def get_status(self):
        """Returns a tuple containing (edited, total) sentences."""
        total = RankingItem.objects.filter(task=self).count()
        edited = RankingItem.objects.filter(task=self, edited=True).count()
        return (edited, total)

    def get_rankA(self):
        """Returns the average rank of system A."""
        edited = RankingItem.objects.filter(task=self, edited=True).count()

        rank = 0
        for k in range(4):
            rank += (k+1) * RankingResult.objects.filter(item__task=self,
            item__edited=True, rankA=str(k+1)).count()

        if edited:
            return rank/float(edited)

        return None

    def get_rankB(self):
        """Returns the average rank of system B."""
        edited = RankingItem.objects.filter(task=self, edited=True).count()

        rank = 0
        for k in range(4):
            rank += (k+1) * RankingResult.objects.filter(item__task=self,
            item__edited=True, rankB=str(k+1)).count()

        if edited:
            return rank/float(edited)

        return None

    def get_rankC(self):
        """Returns the average rank of system C."""
        edited = RankingItem.objects.filter(task=self, edited=True).count()

        rank = 0
        for k in range(4):
            rank += (k+1) * RankingResult.objects.filter(item__task=self,
            item__edited=True, rankC=str(k+1)).count()

        if edited:
            return rank/float(edited)

        return None

    def get_rankD(self):
        """Returns the average rank of system D."""
        edited = RankingItem.objects.filter(task=self, edited=True).count()

        rank = 0
        for k in range(4):
            rank += (k+1) * RankingResult.objects.filter(item__task=self,
            item__edited=True, rankD=str(k+1)).count()

        if edited:
            return rank/float(edited)

        return None


class RankingItem(models.Model):
    """An RankingItem comprises a source text and 4 translations."""
    task = models.ForeignKey(RankingTask)
    source = models.TextField()
    systemA = models.TextField()
    systemB = models.TextField()
    systemC = models.TextField()
    systemD = models.TextField()
    edited = models.BooleanField(default=False)

    def __unicode__(self):
        """Returns a Unicode String representation of the editing item."""
        return u'<ranking-item id="{0}" task="{1}">'.format(self.id,
          self.task.shortname)


class RankingResult(models.Model):
    """An RankingResult stores a ranking of translations."""
    item = models.ForeignKey(RankingItem)
    user = models.ForeignKey(User)
    rankA = models.IntegerField()
    rankB = models.IntegerField()
    rankC = models.IntegerField()
    rankD = models.IntegerField()

    def __unicode__(self):
        """Returns a Unicode String representation of the editing result."""
        return u'<ranking-result id="{0}" item="{1}" user="{2}">'.format(
          self.id, self.item, self.user.username)


class ClassificationResult(models.Model):
    """An ClassificationResult stores error classification for a sentence."""
    item = models.ForeignKey(RankingItem)
    user = models.ForeignKey(User)
    system = models.CharField(max_length=1)
    missing_content_words = models.BooleanField(default=False)
    content_words_wrong = models.BooleanField(default=False)
    wrong_functional_words = models.BooleanField(default=False)
    incorrect_word_forms = models.BooleanField(default=False)
    incorrect_word_order = models.BooleanField(default=False)
    incorrect_punctuation = models.BooleanField(default=False)
    other_error = models.BooleanField(default=False)
    comments = models.TextField(blank=True)


    def __unicode__(self):
        """Returns a Unicode String representation of the editing result."""
        return u'<ranking-result id="{0}" item="{1}" user="{2}">'.format(
          self.id, self.item, self.user.username)



class EditingTask(models.Model):
    """An EditingTask represents a set of post-editing tasks."""
    shortname = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    users = models.ManyToManyField(
      User,
      blank=True,
      help_text="Users allowed to work on this editing task."
    )
    task_id = models.CharField(max_length=32, default=_create_id())

    def __unicode__(self):
        """Returns a Unicode String representation of the editing task."""
        return u'<editing-task id="{0}" name="{1}">'.format(self.id,
          self.shortname)

    def get_status(self):
        """Returns a tuple containing (edited, total) sentences."""
        total = EditingItem.objects.filter(task=self).count()
        edited = EditingItem.objects.filter(task=self, edited=True).count()
        return (edited, total)


class EditingItem(models.Model):
    """An EditingItem comprises a source text and 3 translations."""
    task = models.ForeignKey(EditingTask)
    source = models.TextField()
    systemA = models.TextField()
    systemB = models.TextField()
    systemC = models.TextField()
    edited = models.BooleanField(default=False)

    def __unicode__(self):
        """Returns a Unicode String representation of the editing item."""
        return u'<editing-item id="{0}" task="{1}">'.format(self.id,
          self.task.shortname)


class EditingResult(models.Model):
    """An EditingResult stores a post-edited translation."""
    item = models.ForeignKey(EditingItem)
    user = models.ForeignKey(User)
    system = models.CharField(max_length=1)
    postedited = models.TextField()

    def __unicode__(self):
        """Returns a Unicode String representation of the editing result."""
        return u'<editing-result id="{0}" item="{1}" user="{2}">'.format(
          self.id, self.item, self.user.username)


class LucyTask(models.Model):
    """An LucyTask represents a set of Lucy ranking tasks."""
    shortname = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    users = models.ManyToManyField(
      User,
      blank=True,
      help_text="Users allowed to work on this Lucy ranking task."
    )
    task_id = models.CharField(max_length=32, default=_create_id())

    def __unicode__(self):
        """Returns a Unicode String representation of the Lucy task."""
        return u'<lucy-task id="{0}" name="{1}">'.format(self.id,
          self.shortname)

    def get_status(self):
        """Returns a tuple containing (edited, total) sentences."""
        total = LucyItem.objects.filter(task=self).count()
        edited = LucyResult.objects.filter(item__task__id=self.id).count()
        return (edited, total)

    def get_results(self):
        """Returns a list of tuples containing the results for this task."""
        results = LucyResult.objects.filter(item__task__id=self.id)
        rankings = {'B++': 0, 'B+': 0, '==': 0, 'W+': 0, 'W++': 0}
        sigma = 0
        for result in results:
            rankings[result.ranking] += 1
            sigma += 1

        return (rankings['W++'], rankings['W+'], rankings['=='],
          rankings['B+'], rankings['B++'], sigma)


class LucyItem(models.Model):
    """An LucyItem comprises a source, reference and two Lucy variants."""
    task = models.ForeignKey(LucyTask)
    source = models.TextField()
    reference = models.TextField()
    systemA = models.TextField()
    systemB = models.TextField()
    edited = models.BooleanField(default=False)

    def __unicode__(self):
        """Returns a Unicode String representation of the Lucy item."""
        return u'<lucy-item id="{0}" task="{1}">'.format(self.id,
          self.task.shortname)


class LucyResult(models.Model):
    """An LucyResult stores a users ranking for a Lucy item."""
    item = models.ForeignKey(LucyItem)
    user = models.ForeignKey(User)
    ranking = models.CharField(max_length=3)

    def __unicode__(self):
        """Returns a Unicode String representation of the editing result."""
        return u'<lucy-result id="{0}" item="{1}" user="{2}">'.format(
          self.id, self.item, self.user.username)


QUALITY_CHOICES = (
  ('A', 'Acceptable'),
  ('C', 'Can easily be fixed'),
  ('N', "None of both")
)

class QualityTask(models.Model):
    """An QualityTask represents a set of 'Quality acceptable?' tasks."""
    shortname = models.CharField(max_length=50, help_text="Short name for " \
      "this 'Quality acceptable?' task.")
    description = models.TextField(blank=True, help_text="(Optional) Brief " \
      "description for this 'Quality acceptable?' task.")
    users = models.ManyToManyField(User, blank=True,
      help_text="Users allowed to work on this 'Quality acceptable?' task."
    )
    task_id = models.CharField(max_length=32, default=_create_id(),
      verbose_name="Identifier")

    class Meta:
        """Meta information for the QualityTask class."""
        verbose_name = "'Quality acceptable?' Task"

    def __unicode__(self):
        """Returns a Unicode String representation of this task."""
        return u'<quality-task id="{0}">'.format(self.id)

    def get_status(self):
        """Returns a tuple containing (edited, total) sentences."""
        total = QualityItem.objects.filter(task=self).count()
        edited = QualityItem.objects.filter(task=self, edited=True).count()
        return (edited, total)

    def get_acceptable(self):
        """Returns a tuple containing (acceptable, percentage) information."""
        edited = QualityItem.objects.filter(task=self, edited=True).count()
        acceptable = QualityResult.objects.filter(item__task=self,
          item__edited=True, quality="A").count()

        if not edited:
            return (0, 0)

        return (acceptable, 100 * acceptable/float(edited))

    def get_canbefixed(self):
        """Returns a tuple containing (canbefixed, percentage) information."""
        edited = QualityItem.objects.filter(task=self, edited=True).count()
        canbefixed = QualityResult.objects.filter(item__task=self,
          item__edited=True, quality="C").count()

        if not edited:
            return (0, 0)

        return (canbefixed, 100 * canbefixed/float(edited))

    def get_noneofboth(self):
        """Returns a tuple containing (noneofboth, percentage) information."""
        edited = QualityItem.objects.filter(task=self, edited=True).count()
        noneofboth = QualityResult.objects.filter(item__task=self,
          item__edited=True, quality="N").count()

        if not edited:
            return (0, 0)

        return (noneofboth, 100 * noneofboth/float(edited))

    def get_duration(self):
        """Returns the average duration time as String."""
        edited = QualityItem.objects.filter(task=self, edited=True).count()
        durations = QualityResult.objects.filter(item__task=self,
          item__edited=True).values_list('duration', flat=True)

        if not edited:
            return None

        average = 0
        for duration in durations:
            _duration = duration.hour * 3600 + duration.minute * 60 \
              + duration.second + (duration.microsecond / 1000000.0)

            average += _duration

        average /= float(edited)

        return average

    def completed(self):
        """Checks if this task is completed."""
        total = QualityItem.objects.filter(task=self).count()
        edited = QualityItem.objects.filter(task=self, edited=True).count()
        return edited == total


class QualityItem(models.Model):
    """An QualityItem comprises a source text, a translation and optionally
    some context information."""
    task = models.ForeignKey(QualityTask,
      help_text="The task this item belongs to.")
    source = models.TextField(help_text="The source sentence from which " \
      "the following translation has been generated.")
    translation = models.TextField(help_text="The translation that " \
      "corresponds to the previous source sentence.")
    context = models.TextField(blank=True, help_text="(Optional) Any " \
      "context information available to the translation system.")
    edited = models.BooleanField(default=False, help_text="Has this item " \
      "been processed?")

    class Meta:
        """Meta information for the QualityItem class."""
        verbose_name = "'Quality acceptable?' Item"

    def __unicode__(self):
        """Returns a Unicode String for the 'Quality acceptable?' item."""
        return u'<quality-item id="{0}">'.format(self.id)


class QualityResult(models.Model):
    """An QualityResult stores a 'Quality acceptable?' assessment."""
    item = models.ForeignKey(QualityItem)
    user = models.ForeignKey(User)
    quality = models.CharField(max_length=1, choices=QUALITY_CHOICES)
    duration = models.TimeField(blank=True, null=True)

    class Meta:
        """Meta information for the QualityResult class."""
        verbose_name = "'Quality acceptable?' Result"

    def __unicode__(self):
        """Returns a Unicode String for the 'Quality acceptable?' result."""
        return u'<quality-result id="{0}">'.format(self.id)

    def duration_in_seconds(self):
        """Returns the duration required to produce this result in seconds."""
        return self.duration