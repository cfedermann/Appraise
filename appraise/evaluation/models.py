# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
from xml.etree.ElementTree import fromstring, ParseError

import logging
import uuid
from django.db import models
from django.contrib.auth.models import User
from appraise.settings import LOG_LEVEL, LOG_HANDLER

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.evaluation.models')
LOGGER.addHandler(LOG_HANDLER)


def _create_id():
    """Creates a random UUID-4 32-digit hex number for use as task id."""
    new_id = uuid.uuid4().hex
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
    dumdidum
    """
    #raise ValidationError('Thunder in the heavens!')
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

    # TODO: fix upload_to to a good value.
    task_xml = models.FileField(
      upload_to='source-xml',
      help_text="XML source file for this evaluation task.",
      validators=[validate_source_xml_file],
      verbose_name="Task XML source"
    )
    
    # The following is derived from task_xml and NOT stored in the database.
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
        if self.task_xml:
            try:
                _task_xml = fromstring(self.task_xml.read())
                self.task_attributes = {}
                for key, value in _task_xml.attrib.items():
                    self.task_attributes[key] = value
            
            except ParseError:
                self.task_attributes = {}
    
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
        self.full_clean()
        
        # Double check that the given XML source file is valid.
        # if not self.id:
        #     raise ValidationError('Check task_xml contents before saving!')
        
        super(EvaluationTask, self).save(*args, **kwargs)


@receiver(pre_delete, sender=EvaluationTask)
def remove_task_xml_file_on_delete(sender, instance, **kwargs):
    """
    Removes the task_xml file when the EvaluationTask instance is deleted.
    """
    # We have to use save=False as otherwise validation would fail ;)
    instance.task_xml.delete(save=False)


class EvaluationItem(models.Model):
    """
    Evaluation Item object model.
    """
    pass



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