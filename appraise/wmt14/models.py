# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
import logging
import uuid

from xml.etree.ElementTree import fromstring, ParseError, tostring

from django.dispatch import receiver

from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.db import models
from django.template import Context
from django.template.loader import get_template

from appraise.wmt14.validators import validate_hit_xml, validate_segment_xml
from appraise.settings import LOG_LEVEL, LOG_HANDLER
from appraise.utils import datetime_to_seconds, AnnotationTask

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('appraise.wmt14.models')
LOGGER.addHandler(LOG_HANDLER)


LANGUAGE_PAIR_CHOICES = (
  ('eng2ces', 'English → Czech'),
  ('eng2deu', 'English → German'),
  ('eng2fra', 'English → French'),
  ('eng2hin', 'English → Hindi'),
  ('eng2rus', 'English → Russian'),
  ('ces2eng', 'Czech → English'),
  ('deu2eng', 'German → English'),
  ('fra2eng', 'French → English'),
  ('hin2eng', 'Hindi → English'),
  ('rus2eng', 'Russian → English'),
)


# pylint: disable-msg=E1101
class HIT(models.Model):
    """
    HIT object model for WMT14 ranking evaluation.
    
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

    mturk_only = models.BooleanField(
      db_index=True,
      default=False,
      help_text="Indicates that this HIT instance is ONLY usable via MTurk.",
      verbose_name="MTurk only?"
    )

    completed = models.BooleanField(
      db_index=True,
      default=False,
      help_text="Indicates that this HIT instance is completed.",
      verbose_name="Completed?"
    )

    class Meta:
        """
        Metadata options for the HIT object model.
        """
        ordering = ('id', 'hit_id', 'language_pair', 'block_id')
        verbose_name = "HIT instance"
        verbose_name_plural = "HIT instances"
    
    # pylint: disable-msg=E1002
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
        return u'<HIT id="{0}" hit="{1}" block="{2}" language-pair="{3}">' \
          .format(self.id, self.hit_id, self.block_id, self.language_pair)
    
    @classmethod
    def _create_hit_id(cls):
        """Creates a random UUID-4 8-digit hex number for use as HIT id."""
        new_id = uuid.uuid4().hex[:8]
        while cls.objects.filter(hit_id=new_id):
            new_id = uuid.uuid4().hex[:8]
        
        return new_id
    
    @classmethod
    def compute_remaining_hits(cls, language_pair=None):
        """
        Computes the number of remaining HITs in the database.
        
        If language_pair is given, it constraints on the HITs' language pair.
        
        """
        hits_qs = cls.objects.filter(active=True, mturk_only=False, completed=False)
        if language_pair:
            hits_qs = hits_qs.filter(language_pair=language_pair)
        
        available = 0
        for hit in hits_qs:
            # Before we checked if `hit.users.count() < 3`.
            if hit.users.count() < 1:
                available = available + 1
            
            # Set active HITs to completed if there exists at least one result.
            else:
                hit.completed = True
                hit.save()
        
        return available
    
    @classmethod
    def compute_status_for_user(cls, user, language_pair=None):
        """
        Computes the HIT completion status for the given user.
        
        If language_pair is given, it constraints on the HITs' language pair.
        
        Returns a list containing:
        
        - number of completed HITs;
        - average duration per HIT in seconds;
        - total duration in seconds.
        
        """
        hits_qs = cls.objects.filter(users=user)
        if language_pair:
            hits_qs = hits_qs.filter(language_pair=language_pair)
        
        _completed_hits = hits_qs.count()
        
        _durations = []
        for hit in hits_qs:
            _results = RankingResult.objects.filter(user=user, item__hit=hit)
            _durations.extend(_results.values_list('duration', flat=True))
        
        _durations = [datetime_to_seconds(d) for d in _durations if d]
        _total_duration = sum(_durations)
        _average_duration = _total_duration / float(_completed_hits or 1)
        
        current_status = []
        current_status.append(_completed_hits)
        current_status.append(_average_duration)
        current_status.append(_total_duration)
        
        return current_status
    
    @classmethod
    def compute_status_for_group(cls, group, language_pair=None):
        """
        Computes the HIT completion status for users of the given group.
        """
        combined = [0, 0, 0]
        for user in group.user_set.all():
            _user_status = cls.compute_status_for_user(user, language_pair)
            combined[0] = combined[0] + _user_status[0]
            combined[1] = combined[1] + _user_status[1]
            combined[2] = combined[2] + _user_status[2]
        
        combined[1] = combined[2] / float(combined[0] or 1)
        return combined
    
    # pylint: disable-msg=E1002
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
        hit_handler_view = 'appraise.wmt14.views.hit_handler'
        kwargs = {'hit_id': self.hit_id}
        return reverse(hit_handler_view, kwargs=kwargs)
    
    def get_status_url(self):
        """
        Returns the status URL for this HIT object instance.
        """
        status_handler_view = 'appraise.wmt14.views.status_view'
        kwargs = {'hit_id': self.hit_id}
        return reverse(status_handler_view, kwargs=kwargs)
    
    def reload_dynamic_fields(self):
        """
        Reloads hit_attributes from self.hit_xml contents.
        """
        # If a hit_xml file is available, populate self.hit_attributes.
        if self.hit_xml:
            try:
                _hit_xml = fromstring(self.hit_xml.encode("utf-8"))
                self.hit_attributes = {}
                for key, value in _hit_xml.attrib.items():
                    self.hit_attributes[key] = value
            
            # For parse errors, set self.hit_attributes s.t. it gives an
            # error message to the user for debugging.
            except (ParseError), msg:
                self.hit_attributes = {'note': msg}
    
    def export_to_xml(self):
        """
        Renders this HIT as XML String.
        """
        template = get_template('wmt14/task_result.xml')
        
        # If a hit_xml file is available, populate self.hit_attributes.
        self.reload_dynamic_fields()
        
        _attr = self.hit_attributes.items()
        attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in _attr])
        
        results = []
        for item in RankingTask.objects.filter(hit=self):
            _results = []
            for _result in item.rankingresult_set.all():
                _results.append(_result.export_to_xml())
            results.append(_results)
        
        context = {'hit_id': self.hit_id, 'attributes': attributes,
          'results': list(enumerate(results))}
        return template.render(Context(context))
    
    def export_to_apf(self):
        """
        Exports this HIT's results to Artstein and Poesio (2007) format.
        """
        results = []
        for item in RankingTask.objects.filter(hit=self):
            for _result in item.rankingresult_set.all():
                _apf_output = _result.export_to_apf()
                if _apf_output:
                    results.append(_apf_output)
        return u"\n".join(results)
    
    
    def compute_agreement_scores(self):
        """
        Computes alpha, kappa, pi and Bennett's S agreement scores using NLTK.
        """
        _raw = self.export_to_apf().split('\n')
        if not len(_raw):
            return None
        
        # Convert raw results data into data triples and create a new
        # AnnotationTask object for computation of agreement scores.
        _data = [_line.split(',') for _line in _raw]
        try:
            _data = [(x[0], x[1], x[2]) for x in _data]
        
        except IndexError:
            return None
        
        # Compute alpha, kappa, pi, and S scores.
        _task = AnnotationTask(data=_data)
        try:
            _alpha = _task.alpha()
            _kappa = _task.kappa()
            _pi = _task.pi()
            # pylint: disable-msg=C0103
            _S = _task.S()
        
        except ZeroDivisionError, msg:
            LOGGER.debug(msg)
            return None
        
        return (_alpha, _kappa, _pi, _S)


class RankingTask(models.Model):
    """
    RankingTask object model for WMT14 ranking evaluation.
    """
    hit = models.ForeignKey(
      HIT,
      db_index=True
    )
    
    item_xml = models.TextField(
      help_text="XML source for this RankingTask instance.",
      validators=[validate_segment_xml],
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
    
    # pylint: disable-msg=E1002
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
    
    # pylint: disable-msg=E1002
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
    
    # pylint: disable-msg=E1002
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
        template = get_template('wmt14/ranking_result.xml')
        
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
    
    def export_to_csv(self):
        """
        Exports this RankingResult in CSV format.
        """
        item = self.item
        hit = self.item.hit
        values = []
        
        iso639_3_to_name_mapping = {'ces': 'Czech', 'cze': 'Czech',
          'deu': 'German', 'ger': 'German', 'eng': 'English',
          'spa': 'Spanish', 'fra': 'French', 'fre': 'French',
          'hin': 'Hindi', 'rus': 'Russian'}
        
        _src_lang = hit.hit_attributes['source-language']
        _trg_lang = hit.hit_attributes['target-language']
        
        # System ids can be retrieved from HIT or segment level.
        if 'systems' in hit.hit_attributes.keys():
            _systems = hit.hit_attributes['systems'].split(',')
        
        # On segment level, we have to extract the individual "system" values
        # from the <translation> attributes which are stored in the second
        # position of the translation tuple: (text, attrib).
        else:
            _systems = []
            for translation in item.translations:
                _systems.append(translation[1]['system'])
        
        # Note that srcIndex and segmentId are 1-indexed for compatibility
        # with evaluation scripts from previous editions of the WMT.
        values.append(iso639_3_to_name_mapping[_src_lang]) # srclang
        values.append(iso639_3_to_name_mapping[_trg_lang]) # trglang
        values.append(item.source[1]['id'])                # srcIndex
        values.append('-1')                                # documentId
        values.append(item.source[1]['id'])                # segmentId (= srcIndex)
        values.append(self.user.username)                  # judgeId
        values.append('-1')                                # system1Number
        values.append(str(_systems[0]))                    # system1Id
        values.append('-1')                                # system2Number
        values.append(str(_systems[1]))                    # system2Id
        values.append('-1')                                # system3Number
        values.append(str(_systems[2]))                    # system3Id
        values.append('-1')                                # system4Number
        values.append(str(_systems[3]))                    # system4Id
        values.append('-1')                                # system5Number
        values.append(str(_systems[4]))                    # system5Id
        
        # system1rank,system2rank,system3rank,system4rank,system5rank
        if self.results:
            values.extend([str(x) for x in self.results])
        else:
            values.extend(['-1'] * 5)
        
        return u",".join(values)
    
    
    # pylint: disable-msg=C0103
    def export_to_apf(self):
        """
        Exports this RankingResult to Artstein and Poesio (2007) format.
        """
        item = self.item
        hit = self.item.hit
        
        # System ids can be retrieved from HIT or segment level.
        if 'systems' in hit.hit_attributes.keys():
            _systems = hit.hit_attributes['systems'].split(',')
        
        # On segment level, we have to extract the individual "system" values
        # from the <translation> attributes which are stored in the second
        # position of the translation tuple: (text, attrib).
        else:
            _systems = []
            for translation in item.translations:
                _systems.append(translation[1]['system'])
        
        from itertools import combinations
        results = []
        
        # Note that srcIndex is 1-indexed for compatibility with evaluation
        # scripts from previous editions of the WMT.
        for a, b in combinations(range(5), 2):
            _c = self.user.username
            _i = '{0}.{1}.{2}'.format(item.source[1]['id'], a+1, b+1)
            
            if not self.results:
                _v = '{0}?{1}'.format(str(_systems[a]), str(_systems[b]))
            elif self.results[a] > self.results[b]:
                _v = '{0}>{1}'.format(str(_systems[a]), str(_systems[b]))
            elif self.results[a] < self.results[b]:
                _v = '{0}<{1}'.format(str(_systems[a]), str(_systems[b]))
            else:
                _v = '{0}={1}'.format(str(_systems[a]), str(_systems[b]))
            
            results.append('{0},{1},{2}'.format(_c, _i, _v))
        return u'\n'.join(results)


@receiver(models.signals.post_save, sender=RankingResult)
def update_user_hit_mappings(sender, instance, created, **kwargs):
    """
    Updates the User/HIT mappings.
    """
    hit = instance.item.hit
    user = instance.user
    results = RankingResult.objects.filter(user=user, item__hit=hit)
    
    if len(results) > 2:
        LOGGER.debug('Deleting stale User/HIT mapping {0}->{1}'.format(
          user, hit))
        hit.users.add(user)
        UserHITMapping.objects.filter(user=user, hit=hit).delete()
        
        from appraise.wmt14.views import _compute_next_task_for_user
        _compute_next_task_for_user(user, hit.language_pair)

@receiver(models.signals.post_delete, sender=RankingResult)
def remove_user_from_hit(sender, instance, **kwargs):
    """
    Removes user from list of users who have completed corresponding HIT.
    """
    hit = instance.item.hit
    user = instance.user
    
    LOGGER.debug('Removing user "{0}" from HIT {1}'.format(user, hit))
    hit.users.remove(user)
    
    from appraise.wmt14.views import _compute_next_task_for_user
    _compute_next_task_for_user(user, hit.language_pair)


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
    
    def __unicode__(self):
        """
        Returns a Unicode String for this UserHITMapping object.
        """
        return u'<hitmap id="{0}" user="{1}" hit="{2}">'.format(self.id,
          self.user.username, self.hit.hit_id)


# pylint: disable-msg=E1101
class UserInviteToken(models.Model):
    """
    User invite tokens allowing to register an account.
    """
    group = models.ForeignKey(
      Group,
      db_index=True
    )

    token = models.CharField(
      max_length=8,
      db_index=True,
      default=lambda: UserInviteToken._create_token(),
      unique=True,
      help_text="Unique invite token",
      verbose_name="Invite token"
    )

    active = models.BooleanField(
      db_index=True,
      default=True,
      help_text="Indicates that this invite can still be used.",
      verbose_name="Active?"
    )

    class Meta:
        """
        Metadata options for the UserInviteToken object model.
        """
        verbose_name = "User invite token"
        verbose_name_plural = "User invite tokens"

    # pylint: disable-msg=E1002
    def __init__(self, *args, **kwargs):
        """
        Makes sure that self.token is properly set up.
        """
        super(UserInviteToken, self).__init__(*args, **kwargs)
        
        if not self.token:
            self.token = self.__class__._create_token()

    def __unicode__(self):
        """
        Returns a Unicode String for this UserInviteToken object.
        """
        return u'<user-invite id="{0}" token="{1}" active="{2}">'.format(
          self.id, self.token, self.active)

    @classmethod
    def _create_token(cls):
        """Creates a random UUID-4 8-digit hex number for use as a token."""
        new_token = uuid.uuid4().hex[:8]
        while cls.objects.filter(token=new_token):
            new_token = uuid.uuid4().hex[:8]
        
        return new_token
