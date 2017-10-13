"""
EvalData models.py

###
# DESIGN/ARCHITECTURE
#
# EvalData
# - Market
# - Metadata
# - EvalItem
#  + TextSegment
#  + TextPair
#  + TextSet
#
###

"""
# pylint: disable=C0103,C0330
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from json import loads
from traceback import format_exc
from zipfile import ZipFile, is_zipfile
from django.db import models
from django.db.models import Count
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy as f
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _

from Appraise.settings import LOG_LEVEL, LOG_HANDLER, STATIC_URL, BASE_CONTEXT
from Dashboard.models import LANGUAGE_CODES_AND_NAMES

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('EvalData.models')
LOGGER.addHandler(LOG_HANDLER)

MAX_DOMAINNAME_LENGTH = 20
MAX_LANGUAGECODE_LENGTH = 10
MAX_CORPUSNAME_LENGTH = 100
MAX_VERSIONINFO_LENGTH = 20
MAX_SOURCE_LENGTH = 2000
MAX_SEGMENTTEXT_LENGTH = 2000
MAX_SEGMENTID_LENGTH = 1000
MAX_ITEMTYPE_LENGTH = 5
MAX_REQUIREDANNOTATIONS_VALUE = 50
MAX_TYPENAME_LENGTH = 100
MAX_PRIMARYID_LENGTH = 50

SET_ITEMTYPE_CHOICES = (
  ('SRC', 'Source text'),
  ('TGT', 'Target text'),
  ('REF', 'Reference text'),
  ('BAD', 'Bad reference'),
  ('CHK', 'Redundant check')
)

def seconds_to_timedelta(value):
    """
    Converst the given value in secodns to datetime.timedelta.
    """
    _days =  value // 86400
    _hours = (value // 3600) % 24
    _mins = (value // 60) % 60
    _secs = value % 60
    return timedelta(days=_days, hours=_hours, minutes=_mins, seconds=_secs)


class ObjectID(models.Model):
    """
    Encodes an object type and ID for retrieval.
    """
    typeName = models.CharField(
      max_length=MAX_TYPENAME_LENGTH,
      verbose_name=_('Type name'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_TYPENAME_LENGTH))
    )

    primaryID = models.CharField(
       max_length=MAX_PRIMARYID_LENGTH,
      verbose_name=_('Primary ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_PRIMARYID_LENGTH))
    )

    def get_object_instance(self):
        """
        Returns actual object instance for current ObjectID instance.
        """
        instance = None
        try:
            # TODO: add registry of type names to models.py and ensure only
            #   those are used for typeName. Furthermore, verify that the
            #   given primaryID does not contain ')'.

            _code = '{0}.objects.get(id={1})'.format(
              self.typeName, self.primaryID
            )
            instance = eval(_code)

        except:
            _msg = 'ObjectID {0}.{1} invalid'.format(
              self.typeName, self.primaryID
            )
            LOGGER.warn(_msg)
            LOGGER.warn(format_exc())

        finally:
            return instance


# pylint: disable=C0103,R0903
class BaseMetadata(models.Model):
    """
    Abstract base metadata for all object models.
    """
    dateCreated = models.DateTimeField(
      auto_now_add=True,
      editable=False,
      verbose_name=_('Date created')
    )

    dateActivated = models.DateTimeField(
      blank=True,
      null=True,
      verbose_name=_('Date activated')
    )

    dateCompleted = models.DateTimeField(
      blank=True,
      null=True,
      verbose_name=_('Date completed')
    )

    dateRetired = models.DateTimeField(
      blank=True,
      null=True,
      verbose_name=_('Date retired')
    )

    dateModified = models.DateTimeField(
      blank=True,
      null=True,
      verbose_name=_('Date modified')
    )

    activated = models.BooleanField(
      blank=True,
      db_index=True,
      default=False,
      verbose_name=_('Activated?')
    )

    completed = models.BooleanField(
      blank=True,
      db_index=True,
      default=False,
      verbose_name=_('Completed?')
    )

    retired = models.BooleanField(
      blank=True,
      db_index=True,
      default=False,
      verbose_name=_('Retired?')
    )

    createdBy = models.ForeignKey(
      User,
      db_index=True,
      on_delete=models.PROTECT,
      editable=False,
      related_name='%(app_label)s_%(class)s_created_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Created by')
    )

    activatedBy = models.ForeignKey(
      User,
      blank=True,
      db_index=True,
      on_delete=models.PROTECT,
      editable=False,
      null=True,
      related_name='%(app_label)s_%(class)s_activated_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Activated by')
    )

    completedBy = models.ForeignKey(
      User,
      blank=True,
      db_index=True,
      on_delete=models.PROTECT,
      editable=False,
      null=True,
      related_name='%(app_label)s_%(class)s_completed_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Completed by')
    )

    retiredBy = models.ForeignKey(
      User,
      blank=True,
      db_index=True,
      on_delete=models.PROTECT,
      editable=False,
      null=True,
      related_name='%(app_label)s_%(class)s_retired_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Retired by')
    )

    modifiedBy = models.ForeignKey(
      User,
      blank=True,
      db_index=True,
      on_delete=models.PROTECT,
      editable=False,
      null=True,
      related_name='%(app_label)s_%(class)s_modified_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Modified by')
    )

    rawData = models.TextField(
      blank=True,
      editable=False,
      verbose_name=_('Raw data')
    )

    _str_name = models.TextField(
      blank=True,
      default="",
      editable=False
    )

    # pylint: disable=C0111
    class Meta:
        abstract = True

    def _set_boolean_states(self, activated, completed, retired):
        """
        Sets boolean states for current model instance.
        Also sets respective dates for all three states.
        """
        utc_now = datetime.utcnow().replace(tzinfo=utc)
        
        self.activated = activated
        self.dateActivated = utc_now if activated else None

        self.completed = completed
        self.dateCompleted = utc_now if completed else None

        self.retired = retired
        self.dateRetired = utc_now if retired else None

        self.save()

    def activate(self):
        """
        Sets activated=True for current model instance.
        This implies completed=False and retired=False.
        """
        self._set_boolean_states(True, False, False)

    def complete(self):
        """
        Sets completed=True for current model instance.
        This implies activated=False and retired=False.
        """
        self._set_boolean_states(False, True, False)

    def retire(self):
        """
        Sets retired=True for current model instance.

        This implies activated=False and completed=False.
        """
        self._set_boolean_states(False, False, True)

    def is_valid(self):
        """
        Validates the current model instance.
        """
        try:
            self.full_clean()
            return True

        except ValidationError:
            return False

    def _generate_str_name(self):
        """
        Generate human readable name for use with __str__().
        """
        return '{0}[{1}]'.format(
          self.__class__.__name__,
          self.id
        )

    def save(self, *args, **kwargs):
        """
        For object instances with an ID, we precompute the _str_name
        attribute so that future __str__() lookups are efficient.

        Also, we ensure that a matching ObjectID binding is created.
        """
        if self.id:
            _new_name = self._generate_str_name()
            if self._str_name != _new_name:
                self._str_name = _new_name

            qs = ObjectID.objects.filter(
              typeName=self.__class__.__name__,
              primaryID=self.id
            )
            if not qs.exists():
                _serialized = ObjectID.objects.create(
                  typeName=self.__class__.__name__,
                  primaryID=self.id
                )
                _msg = 'Created serialized ObjectID:{0}'.format(_serialized.id)
                LOGGER.info(_msg)

        super(BaseMetadata, self).save(*args, **kwargs)

    # pylint: disable=E1136
    def __str__(self):
        if self._str_name == "":
            # This will populate self._str_name
            self.save()

        return self._str_name


class Market(BaseMetadata):
    """
    Models a language/locale market.
    """
    ###
    # Each market has a unique ID composed of source, target language codes
    # and application domain name. This also acts as primary lookup key.
    #
    # By assumption, source language content has been produced natively.
    # For monolingual content, source and target codes are identical.
    ###
    marketID = models.CharField(
        max_length=2 * MAX_LANGUAGECODE_LENGTH + MAX_DOMAINNAME_LENGTH + 2,
        editable=False,
        unique=True
    )

    sourceLanguageCode = models.CharField(
      max_length=MAX_LANGUAGECODE_LENGTH,
      verbose_name=_('Source language'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_LANGUAGECODE_LENGTH))
    )

    targetLanguageCode = models.CharField(
      max_length=MAX_LANGUAGECODE_LENGTH,
      verbose_name=_('Target language'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_LANGUAGECODE_LENGTH))
    )

    domainName = models.CharField(
      max_length=MAX_DOMAINNAME_LENGTH,
      verbose_name=_('Domain name'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_DOMAINNAME_LENGTH))
    )

    def clean_fields(self, exclude=None):
        """
        Verifies that desired marketID is still available.
        """
        _new_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName
        )

        _market_instance = Market.objects.filter(marketID=_new_marketID)
        if _market_instance.exists():
            raise ValidationError(
              _(f('Market with identical marketID ("{mID}") already exists.',
                mID=_new_marketID))
            )

        super(Market, self).clean_fields(exclude)

    def save(self, *args, **kwargs):
        _new_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName
        )
        self.marketID = _new_marketID

        super(Market, self).save(*args, **kwargs)

    # TODO: what is this used for? Candidate for deprecation/removal.
    #
    # pylint: disable=E1101
    def my_is_valid(self):
        """
        Validates the current Market instance, checking marketID uniqueness.
        """
        _expected_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName
        )

        _market_instance = Market.objects.filter(marketID=_expected_marketID)
        if not hasattr(self, "marketID") or self.marketID == '':
            if _market_instance.exists():
                return False

        else:
            _market_instance_obj = _market_instance.get()
            if _market_instance_obj is not None and self.id != _market_instance_obj.id:
                return False

        return super(Market, self).is_valid()

    def _generate_str_name(self):
        return self.marketID


class Metadata(BaseMetadata):
    """
    Models metadata associated to tasks.
    """
    market = models.ForeignKey(
      Market,
      db_index=True,
      on_delete=models.PROTECT
    )

    corpusName = models.CharField(
      max_length=MAX_CORPUSNAME_LENGTH,
      verbose_name=_('Corpus name'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_CORPUSNAME_LENGTH))
    )

    versionInfo = models.CharField(
      max_length=MAX_VERSIONINFO_LENGTH,
      verbose_name=_('Version info'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_VERSIONINFO_LENGTH))
    )

    source = models.CharField(
      max_length=MAX_SOURCE_LENGTH,
      verbose_name=_('Source'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SOURCE_LENGTH))
    )

    class Meta:
        verbose_name = 'Metadata record'

    def _generate_str_name(self):
        return '{0}/{1}["{2}"]'.format(
          str(self.market)[:7].replace('_', '-'),
          self.corpusName,
          self.versionInfo
        )


class EvalItem(BaseMetadata):
    """
    Abstract base class for evaluation data items.

    Models corresponding, 1-based, integer ID and metadata.
    """
    itemID = models.PositiveIntegerField(
      verbose_name=_('Item ID'),
      help_text=_('(1-based)')
    )

    itemType = models.CharField(
      choices=SET_ITEMTYPE_CHOICES,
      db_index=True,
      max_length=MAX_ITEMTYPE_LENGTH,
      verbose_name=_('Item type')
    )

    metadata = models.ForeignKey(
      Metadata,
      db_index=True,
      on_delete=models.PROTECT
    )

    # pylint: disable=C0111,R0903
    class Meta:
        abstract = True

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current evaluation item, checking ID and metadata.
        """
        if not hasattr(self, "metadata") or not self.metadata.is_valid():
            return False

        if not isinstance(self.itemID, int):
            return False

        if self.itemID < 1:
            return False

        return super(EvalItem, self).is_valid()

    def _generate_str_name(self):
        return '{0}.{1}[{2}]'.format(
          self.__class__.__name__,
          self.metadata,
          self.itemID
        )


class TextSegment(EvalItem):
    """
    Models a single text segment.
    """
    segmentID = models.CharField(
      max_length=MAX_SEGMENTID_LENGTH,
      verbose_name=_('Segment ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTID_LENGTH))
    )

    segmentText = models.CharField(
      max_length=MAX_SEGMENTTEXT_LENGTH,
      verbose_name=_('Segment text'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTTEXT_LENGTH))
    )

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current TextSegment instance, checking text.
        """
        if not isinstance(self.segmentText, type('This is a test sentence.')):
            return False

        _len = len(self.segmentText)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        return super(TextSegment, self).is_valid()


# TODO: chrife: source, target should be refactored into item1, item2.
#   For direct assessment, we will use candidate and reference.
class TextPair(EvalItem):
    """
    Models a pair of two text segments.
    """
    sourceID = models.CharField(
      max_length=MAX_SEGMENTID_LENGTH,
      verbose_name=_('Source ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTID_LENGTH))
    )

    sourceText = models.CharField(
      max_length=MAX_SEGMENTTEXT_LENGTH,
      verbose_name=_('Source text'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTTEXT_LENGTH))
    )

    targetID = models.CharField(
      max_length=MAX_SEGMENTID_LENGTH,
      verbose_name=_('Target ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTID_LENGTH))
    )

    targetText = models.CharField(
      max_length=MAX_SEGMENTTEXT_LENGTH,
      verbose_name=_('Target text'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTTEXT_LENGTH))
    )

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current TextPair instance, checking text.
        """
        if isinstance(self.sourceText, type('This is a test sentence.')):
            return False

        _len = len(self.sourceText)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        if isinstance(self.targetText, type('This is a test sentence.')):
            return False

        _len = len(self.targetText)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        return super(TextPair, self).is_valid()

class TextPairWithImage(EvalItem):
    """
    Models a pair of two text segments and an image.
    """
    sourceID = models.CharField(
      max_length=MAX_SEGMENTID_LENGTH,
      verbose_name=_('Source ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTID_LENGTH))
    )

    sourceText = models.CharField(
      max_length=MAX_SEGMENTTEXT_LENGTH,
      verbose_name=_('Source text'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTTEXT_LENGTH))
    )

    targetID = models.CharField(
      max_length=MAX_SEGMENTID_LENGTH,
      verbose_name=_('Target ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTID_LENGTH))
    )

    targetText = models.CharField(
      max_length=MAX_SEGMENTTEXT_LENGTH,
      verbose_name=_('Target text'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTTEXT_LENGTH))
    )

    imageURL = models.URLField(
      verbose_name=_('image URL')
    )

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current TextPair instance, checking text.
        """
        if isinstance(self.sourceText, type('This is a test sentence.')):
            return False

        _len = len(self.sourceText)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        if isinstance(self.targetText, type('This is a test sentence.')):
            return False

        _len = len(self.targetText)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        # This does not implement validation for image URLs yet.

        return super(TextPairWithImage, self).is_valid()


class DirectAssessmentTask(BaseMetadata):
    """
    Models a direct assessment evaluation task.
    """
    campaign = models.ForeignKey(
      'Campaign.Campaign',
      db_index=True,
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_campaign',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Campaign')
    )

    items = models.ManyToManyField(
      TextPair,
      related_name='%(app_label)s_%(class)s_items',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Items')
    )

    requiredAnnotations = models.PositiveSmallIntegerField(
      verbose_name=_('Required annotations'),
      help_text=_(f('(value in range=[1,{value}])',
        value=MAX_REQUIREDANNOTATIONS_VALUE))
    )

    assignedTo = models.ManyToManyField(
      User,
      blank=True,
      db_index=True,
      related_name='%(app_label)s_%(class)s_assignedTo',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Assigned to'),
      help_text=_('(users working on this task)')
    )

    batchNo = models.PositiveIntegerField(
      verbose_name=_('Batch number'),
      help_text=_('(1-based)')
    )

    batchData = models.ForeignKey(
      'Campaign.CampaignData',
      on_delete=models.PROTECT,
      blank=True,
      db_index=True,
      null=True,
      related_name='%(app_label)s_%(class)s_batchData',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Batch data')
    )

    def dataName(self):
        return str(self.batchData)

    def marketName(self):
        return str(self.items.first().metadata.market)

    def marketSourceLanguage(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[0] in LANGUAGE_CODES_AND_NAMES.keys():
            return LANGUAGE_CODES_AND_NAMES[tokens[0]]
        return None

    def marketSourceLanguageCode(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[0] in LANGUAGE_CODES_AND_NAMES.keys():
            return tokens[0]
        return None

    def marketTargetLanguage(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[1] in LANGUAGE_CODES_AND_NAMES.keys():
            return LANGUAGE_CODES_AND_NAMES[tokens[1]]
        return None

    def marketTargetLanguageCode(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[1] in LANGUAGE_CODES_AND_NAMES.keys():
            return tokens[1]
        return None

    def completed_items_for_user(self, user):
        results = DirectAssessmentResult.objects.filter(
          task=self,
          activated=False,
          completed=True,
          createdBy=user
        ).values_list('item_id', flat=True)

        return len(set(results))

    def is_trusted_user(self, user):
        # Appen crowd users are never trusted!
        if user.groups.filter(name='Appen').exists():
            return False

        from Campaign.models import TrustedUser
        trusted_user = TrustedUser.objects.filter(\
          user=user, campaign=self.campaign
        )
        return trusted_user.exists()

    def next_item_for_user(self, user, return_completed_items=False):
        trusted_user = self.is_trusted_user(user)

        next_item = None
        completed_items = 0
        for item in self.items.all():
            result = DirectAssessmentResult.objects.filter(
              item=item,
              activated=False,
              completed=True,
              createdBy=user
            )

            if not result.exists():
                print('identified next item: {0}/{1} for trusted={2}'.format(
                  item.id, item.itemType, trusted_user
                ))
                if not trusted_user or item.itemType == 'TGT':
                    next_item = item
                    break

            completed_items += 1

        if not next_item:
            LOGGER.info('No next item found for task {0}'.format(self.id))
            annotations = DirectAssessmentResult.objects.filter(
              task=self,
              activated=False,
              completed=True
            ).values_list('item_id', flat=True)
            uniqueAnnotations = len(set(annotations))

            required_user_results = 100
            if trusted_user:
                required_user_results = 70

            LOGGER.info(
              'Unique annotations={0}/{1}'.format(
                uniqueAnnotations, self.requiredAnnotations * required_user_results
              )
            )
            if uniqueAnnotations >= self.requiredAnnotations * required_user_results:
                LOGGER.info('Completing task {0}'.format(self.id))
                self.complete()
                self.save()

                # Not sure why I would complete the batch here?
                # self.batchData.complete()
                # self.batchData.save()

        if return_completed_items:
            return (next_item, completed_items)

        return next_item

    @classmethod
    def get_task_for_user(cls, user):
        for active_task in cls.objects.filter(
          assignedTo=user,
          activated=True,
          completed=False
        ).order_by('-id'):
            next_item = active_task.next_item_for_user(user)
            if next_item is not None:
                return active_task

        return None

    @classmethod
    def get_next_free_task_for_language(cls, code, campaign=None, user=None):
        active_tasks = cls.objects.filter(
          activated=True,
          completed=False,
          items__metadata__market__targetLanguageCode=code
        )

        if campaign:
            active_tasks = active_tasks.filter(
              campaign=campaign
            )

            # Appen crowd users may only contribute three HITs per campaign.
            if user.groups.filter(name='Appen').exists():
                completed_items = DirectAssessmentResult.objects.filter(
                  activated=False,
                  completed=True,
                  createdBy=user,
                  task__campaign=campaign,
                ).values_list('item_id', 'task_id')

                completed_tasks = defaultdict(list)
                for item in completed_items:
                    completed_tasks[item[1]].append(item[0])

                validated_tasks = 0
                for task_id in completed_tasks:
                    if len(completed_tasks[task_id]) >= 100:
                        validated_tasks += 1

                if validated_tasks >= 3:
                    _msg = 'User {0} has already completed {1} tasks and ' \
                      'created {2} results for campaign {3}'.format(
                      user.username,
                      validated_tasks,
                      len(completed_items),
                      campaign.campaignName
                    )
                    LOGGER.info(_msg)
                    return None

        for active_task in active_tasks.order_by('id'):
            active_users = active_task.assignedTo.count()
            if active_users < active_task.requiredAnnotations:
                if user and not user in active_task.assignedTo.all():
                    return active_task

        return None

        # It seems that assignedTo is converted to an integer count.
        active_tasks = active_tasks.order_by('id') \
         .values_list('id', 'requiredAnnotations', 'assignedTo')

        for active_task in active_tasks:
            print(active_task)
            active_users = active_task[2] or 0
            if active_users < active_task[1]:
                return cls.objects.get(pk=active_task[0])

        return None

        # TODO: this needs to be removed.
        for active_task in active_tasks:
            market = active_task.items.first().metadata.market
            if not market.targetLanguageCode == code:
                continue

            active_users = active_task.assignedTo.count()
            if active_users < active_task.requiredAnnotations:
                return active_task

        return None

    @classmethod
    def get_next_free_task_for_language_and_campaign(cls, code, campaign):
        return cls.get_next_free_task_for_language(code, campaign)

    @classmethod
    def import_from_json(cls, campaign, batch_user, batch_data, max_count):
        """
        Creates new DirectAssessmentTask instances based on JSON input.
        """
        batch_meta = batch_data.metadata
        batch_name = batch_data.dataFile.name
        batch_file = batch_data.dataFile
        batch_json = None

        if batch_name.endswith('.zip'):
            if not is_zipfile(batch_file):
                _msg = 'Batch {0} not a valid ZIP archive'.format(batch_name)
                LOGGER.warn(_msg)
                return

            batch_zip = ZipFile(batch_file)
            batch_json_files = [x for x in batch_zip.namelist() if x.endswith('.json')]
            # TODO: implement proper support for multiple json files in archive.
            for batch_json_file in batch_json_files:
                batch_content = batch_zip.read(batch_json_file).decode('utf-8')
                batch_json = loads(batch_content, encoding='utf-8')

        else:
            batch_json = loads(str(batch_file.read(), encoding="utf-8"))

        from datetime import datetime
        t1 = datetime.now()

        current_count = 0
        max_length_id = 0
        max_length_text = 0
        for batch_task in batch_json:
            if max_count > 0 and current_count >= max_count:
                _msg = 'Stopping after max_count={0} iterations'.format(
                  max_count
                )
                LOGGER.info(_msg)

                t2 = datetime.now()
                print(t2-t1)
                return

            print(batch_name, batch_task['task']['batchNo'])

            new_items = []
            for item in batch_task['items']:
                current_length_id = len(item['targetID'])
                current_length_text = len(item['targetText'])

                if current_length_id > max_length_id:
                    print(current_length_id, item['targetID'])
                    max_length_id = current_length_id

                if current_length_text > max_length_text:
                    print(current_length_text, item['targetText'].encode('utf-8'))
                    max_length_text = current_length_text

                new_item = TextPair(
                    sourceID=item['sourceID'],
                    sourceText=item['sourceText'],
                    targetID=item['targetID'],
                    targetText=item['targetText'],
                    createdBy=batch_user,
                    itemID=item['itemID'],
                    itemType=item['itemType']
                )
                new_items.append(new_item)

            if not len(new_items) == 100:
                _msg = 'Expected 100 items for task but found {0}'.format(
                    len(new_items)
                )
                LOGGER.warn(_msg)
                continue

            current_count += 1


            #for new_item in new_items:
            #    new_item.metadata = batch_meta
            #    new_item.save()
            batch_meta.textpair_set.add(*new_items, bulk=False)
            batch_meta.save()

            new_task = DirectAssessmentTask(
                campaign=campaign,
                requiredAnnotations=batch_task['task']['requiredAnnotations'],
                batchNo=batch_task['task']['batchNo'],
                batchData=batch_data,
                createdBy=batch_user,
            )
            new_task.save()

            #for new_item in new_items:
            #    new_task.items.add(new_item)
            new_task.items.add(*new_items)
            new_task.save()

            _msg = 'Success processing batch {0}, task {1}'.format(
                str(batch_data), batch_task['task']['batchNo']
            )
            LOGGER.info(_msg)

        _msg = 'Max length ID={0}, text={1}'.format(
          max_length_id, max_length_text
        )
        LOGGER.info(_msg)

        t2 = datetime.now()
        print(t2-t1)

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current DA task, checking campaign and items exist.
        """
        if not hasattr(self, 'campaign') or not self.campaign.is_valid():
            return False

        if not hasattr(self, 'items'):
            return False

        for item in self.items:
            if not item.is_valid():
                return False

        return True

    def _generate_str_name(self):
        return '{0}.{1}[{2}]'.format(
          self.__class__.__name__,
          self.campaign,
          self.id
        )


class DirectAssessmentResult(BaseMetadata):
    """
    Models a direct assessment evaluation result.
    """
    score = models.PositiveSmallIntegerField(
      verbose_name=_('Score'),
      help_text=_('(value in range=[1,100])')
    )

    start_time = models.FloatField(
      verbose_name=_('Start time'),
      help_text=_('(in seconds)')
    )

    end_time = models.FloatField(
      verbose_name=_('End time'),
      help_text=_('(in seconds)')
    )

    item = models.ForeignKey(
      TextPair,
      db_index=True,
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_item',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Item')
    )

    task = models.ForeignKey(
      DirectAssessmentTask,
      blank=True,
      db_index=True,
      null=True,
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_task',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Task')
    )

    # pylint: disable=E1136
    def _generate_str_name(self):
        return '{0}.{1}={2}'.format(
          self.__class__.__name__,
          self.item,
          self.score
        )

    def duration(self):
        d = self.end_time-self.start_time
        return round(d, 1)

    def item_type(self):
        return self.item.itemType

    @classmethod
    def get_completed_for_user(cls, user):
        return cls.objects.filter(
          createdBy=user,
          activated=False,
          completed=True
        ).count()

    @classmethod
    def get_hit_status_for_user(cls, user):
        user_data = defaultdict(int)
        
        for user_item in cls.objects.filter(
          createdBy=user,
          activated=False,
          completed=True
        ).values_list('task__id', 'item__itemType'):
            if user_item[1].lower() != 'tgt':
                continue

            user_data[user_item[0]] += 1

        total_hits = len(user_data.keys())
        completed_hits = len([x for x in user_data.values() if x >= 70])

        return (completed_hits, total_hits)

    @classmethod
    def get_time_for_user(cls, user):
        results = cls.objects.filter(
          createdBy=user,
          activated=False,
          completed=True
        )

        durations = []
        for result in results:
            duration = result.end_time - result.start_time
            durations.append(duration)

        return seconds_to_timedelta(sum(durations))

    @classmethod
    def get_system_annotations(cls):
        system_scores = defaultdict(list)
        qs = cls.objects.filter(completed=True, item__itemType__in=('TGT', 'CHK'))
        for result in qs.values_list('item__targetID', 'score', 'createdBy', 'item__itemID', 'item__metadata__market__sourceLanguageCode', 'item__metadata__market__targetLanguageCode'):
            systemID = result[0]
            score = result[1]
            annotatorID = result[2]
            segmentID = result[3]
            marketID = '{0}-{1}'.format(result[4], result[5])
            system_scores[marketID].append((systemID, annotatorID, segmentID, score))

        return system_scores

    @classmethod
    def compute_accurate_group_status(cls):
        from Dashboard.models import LANGUAGE_CODES_AND_NAMES
        user_status = defaultdict(list)
        qs = cls.objects.filter(completed=True)
        for result in qs.values_list('createdBy', 'item__itemType', 'task__id'):
            if result[1].lower() != 'tgt':
                continue

            annotatorID = result[0]
            taskID = result[2]
            user_status[annotatorID].append(taskID)

        group_status = defaultdict(list)
        for annotatorID in user_status:
            user = User.objects.get(pk=annotatorID)
            usergroups = ';'.join([x.name for x in user.groups.all() if not x.name in LANGUAGE_CODES_AND_NAMES.keys()])
            if not usergroups:
                usergroups = 'NoGroupInfo'

            group_status[usergroups].extend(user_status[annotatorID])

        group_hits = {}
        for group_name in group_status:
            task_ids = set(group_status[group_name])
            completed_tasks = 0
            for task_id in task_ids:
                if group_status[group_name].count(task_id) >= 70:
                    completed_tasks += 1

            group_hits[group_name] = (completed_tasks, len(task_ids))

        return group_hits


    @classmethod
    def dump_all_results_to_csv_file(cls, csv_file):
        from Dashboard.models import LANGUAGE_CODES_AND_NAMES
        system_scores = defaultdict(list)
        user_data = {}
        qs = cls.objects.filter(completed=True)
        for result in qs.values_list('item__targetID', 'score', 'start_time', 'end_time', 'createdBy', 'item__itemID', 'item__metadata__market__sourceLanguageCode', 'item__metadata__market__targetLanguageCode', 'item__metadata__market__domainName', 'item__itemType', 'task__id', 'task__campaign__campaignName'):

            systemID = result[0]
            score = result[1]
            start_time = result[2]
            end_time = result[3]
            duration = round(float(end_time)-float(start_time), 1)
            annotatorID = result[4]
            segmentID = result[5]
            marketID = '{0}-{1}'.format(result[6], result[7])
            domainName = result[8]
            itemType = result[9]
            taskID = result[10]
            campaignName = result[11]

            if annotatorID in user_data:
                username = user_data[annotatorID][0]
                useremail = user_data[annotatorID][1]
                usergroups = user_data[annotatorID][2]
            
            else:
                user = User.objects.get(pk=annotatorID)
                username = user.username
                useremail = user.email
                usergroups = ';'.join([x.name for x in user.groups.all() if not x.name in LANGUAGE_CODES_AND_NAMES.keys()])
                if not usergroups:
                    usergroups = 'NoGroupInfo'
                
                user_data[annotatorID] = (
                  username, useremail, usergroups
                )

            system_scores[marketID+'-'+domainName].append((taskID,systemID, username, useremail, usergroups, segmentID, score, start_time, end_time, duration, itemType, campaignName))

        x = system_scores
        s=['taskID,systemID,username,email,groups,segmentID,score,startTime,endTime,durationInSeconds,itemType,campaignName']
        for l in x:
            for i in x[l]:
                s.append(','.join([str(a) for a in i]))

        from os.path import join
        from Appraise.settings import BASE_DIR
        media_file_path = join(BASE_DIR, 'media', csv_file)
        with open(media_file_path, 'w') as outfile:
            for c in s:
                outfile.write(c)
                outfile.write('\n')

    @classmethod
    def get_csv(cls, srcCode, tgtCode, domain):
        system_scores = defaultdict(list)
        qs = cls.objects.filter(completed=True)
        for result in qs.values_list('item__targetID', 'score', 'start_time', 'end_time', 'createdBy', 'item__itemID', 'item__metadata__market__sourceLanguageCode', 'item__metadata__market__targetLanguageCode', 'item__metadata__market__domainName', 'item__itemType'):

            if not domain == result[8] or not srcCode == result[6] or not tgtCode == result[7]:
                continue

            systemID = result[0]
            score = result[1]
            start_time = result[2]
            end_time = result[3]
            duration = round(float(end_time)-float(start_time), 1)
            annotatorID = result[4]
            segmentID = result[5]
            marketID = '{0}-{1}'.format(result[6], result[7])
            domainName = result[8]
            itemType = result[9]
            user = User.objects.get(pk=annotatorID)
            username = user.username
            useremail = user.email
            system_scores[marketID+'-'+domainName].append((systemID, username, useremail, segmentID, score, duration, itemType))

        return system_scores

    @classmethod
    def write_csv(cls, srcCode, tgtCode, domain, csvFile, allData=False):
        x = cls.get_csv(srcCode, tgtCode, domain)
        s=['username,email,segmentID,score,durationInSeconds,itemType']
        if allData:
            s[0]='systemID,'+s[0]

        for l in x:
            for i in x[l]:
                e = i[1:] if not allData else i
                s.append(','.join([str(a) for a in e]))

        from os.path import join
        from Appraise.settings import BASE_DIR
        media_file_path = join(BASE_DIR, 'media', csvFile)
        with open(media_file_path, 'w') as outfile:
            for c in s:
                outfile.write(c)
                outfile.write('\n')

    @classmethod
    def get_system_scores(cls, campaign_id):
        system_scores = defaultdict(list)
        qs = cls.objects.filter(completed=True, item__itemType__in=('TGT', 'CHK'))

        # If campaign ID is given, only return results for this campaign.
        if campaign_id:
            qs = qs.filter(task__campaign__id=campaign_id)

        for result in qs.values_list('item__targetID', 'score'):
            #if not result.completed or result.item.itemType not in ('TGT', 'CHK'):
            #    continue

            system_ids = result[0].split('+') #result.item.targetID.split('+')
            score = result[1] #.score

            for system_id in system_ids:
                system_scores[system_id].append(score)

        return system_scores

    @classmethod
    def get_system_status(cls, campaign_id=None, sort_index=3):
        system_scores = cls.get_system_scores(campaign_id=None)
        non_english_codes = ('cs', 'de', 'fi', 'lv', 'tr', 'tr', 'ru', 'zh')

        codes = ['en-{0}'.format(x) for x in non_english_codes] \
          + ['{0}-en'.format(x) for x in non_english_codes]

        data = {}
        for code in codes:
            data[code] = {}
            for key in [x for x in system_scores if code in x]:
                data[code][key] = system_scores[key]

        output_data = {}
        for code in codes:
            total_annotations = sum([len(x) for x in data[code].values()])
            output_local = []
            for key in data[code]:
                x = data[code][key]
                z = sum(x)/total_annotations
                output_local.append((key, len(x), sum(x)/len(x), z))

            output_data[code] = list(sorted(output_local, key=lambda x: x[sort_index], reverse=True))

        return output_data

    @classmethod
    def completed_results_for_user_and_campaign(cls, user, campaign):
        results = cls.objects.filter(
          activated=False,
          completed=True,
          createdBy=user,
          task__campaign=campaign
        ).values_list('item_id', flat=True)

        return len(set(results))


class MultiModalAssessmentTask(BaseMetadata):
    """
    Models a multimodal assessment evaluation task.
    """
    campaign = models.ForeignKey(
      'Campaign.Campaign',
      db_index=True,
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_campaign',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Campaign')
    )

    items = models.ManyToManyField(
      TextPairWithImage,
      related_name='%(app_label)s_%(class)s_items',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Items')
    )

    requiredAnnotations = models.PositiveSmallIntegerField(
      verbose_name=_('Required annotations'),
      help_text=_(f('(value in range=[1,{value}])',
        value=MAX_REQUIREDANNOTATIONS_VALUE))
    )

    assignedTo = models.ManyToManyField(
      User,
      blank=True,
      db_index=True,
      related_name='%(app_label)s_%(class)s_assignedTo',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Assigned to'),
      help_text=_('(users working on this task)')
    )

    batchNo = models.PositiveIntegerField(
      verbose_name=_('Batch number'),
      help_text=_('(1-based)')
    )

    batchData = models.ForeignKey(
      'Campaign.CampaignData',
      on_delete=models.PROTECT,
      blank=True,
      db_index=True,
      null=True,
      related_name='%(app_label)s_%(class)s_batchData',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Batch data')
    )

    def dataName(self):
        return str(self.batchData)

    def marketName(self):
        return str(self.items.first().metadata.market)

    def marketSourceLanguage(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[0] in LANGUAGE_CODES_AND_NAMES.keys():
            return LANGUAGE_CODES_AND_NAMES[tokens[0]]
        return None

    def marketSourceLanguageCode(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[0] in LANGUAGE_CODES_AND_NAMES.keys():
            return tokens[0]
        return None

    def marketTargetLanguage(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[1] in LANGUAGE_CODES_AND_NAMES.keys():
            return LANGUAGE_CODES_AND_NAMES[tokens[1]]
        return None

    def marketTargetLanguageCode(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[1] in LANGUAGE_CODES_AND_NAMES.keys():
            return tokens[1]
        return None

    def completed_items_for_user(self, user):
        results = MultiModalAssessmentResult.objects.filter(
          task=self,
          activated=False,
          completed=True,
          createdBy=user
        ).values_list('item_id', flat=True)

        return len(set(results))

    def is_trusted_user(self, user):
        # Appen crowd users are never trusted!
        if user.groups.filter(name='Appen').exists():
            return False

        from Campaign.models import TrustedUser
        trusted_user = TrustedUser.objects.filter(\
          user=user, campaign=self.campaign
        )
        return trusted_user.exists()

    def next_item_for_user(self, user, return_completed_items=False):
        trusted_user = self.is_trusted_user(user)

        next_item = None
        completed_items = 0
        for item in self.items.all():
            result = MultiModalAssessmentResult.objects.filter(
              item=item,
              activated=False,
              completed=True,
              createdBy=user
            )

            if not result.exists():
                print('identified next item: {0}/{1} for trusted={2}'.format(
                  item.id, item.itemType, trusted_user
                ))
                if not trusted_user or item.itemType == 'TGT':
                    next_item = item
                    break

            completed_items += 1

        if not next_item:
            LOGGER.info('No next item found for task {0}'.format(self.id))
            annotations = MultiModalAssessmentResult.objects.filter(
              task=self,
              activated=False,
              completed=True
            ).values_list('item_id', flat=True)
            uniqueAnnotations = len(set(annotations))

            required_user_results = 100
            if trusted_user:
                required_user_results = 70

            LOGGER.info(
              'Unique annotations={0}/{1}'.format(
                uniqueAnnotations, self.requiredAnnotations * required_user_results
              )
            )
            if uniqueAnnotations >= self.requiredAnnotations * required_user_results:
                LOGGER.info('Completing task {0}'.format(self.id))
                self.complete()
                self.save()

                # Not sure why I would complete the batch here?
                # self.batchData.complete()
                # self.batchData.save()

        if return_completed_items:
            return (next_item, completed_items)

        return next_item

    @classmethod
    def get_task_for_user(cls, user):
        for active_task in cls.objects.filter(
          assignedTo=user,
          activated=True,
          completed=False
        ).order_by('-id'):
            next_item = active_task.next_item_for_user(user)
            if next_item is not None:
                return active_task

        return None

    @classmethod
    def get_next_free_task_for_language(cls, code, campaign=None, user=None):
        active_tasks = cls.objects.filter(
          activated=True,
          completed=False,
          items__metadata__market__targetLanguageCode=code
        )

        if campaign:
            active_tasks = active_tasks.filter(
              campaign=campaign
            )

            # Appen crowd users may only contribute three HITs per campaign.
            if user.groups.filter(name='Appen').exists():
                completed_items = DirectAssessmentResult.objects.filter(
                  activated=False,
                  completed=True,
                  createdBy=user,
                  task__campaign=campaign,
                ).values_list('item_id', 'task_id')

                completed_tasks = defaultdict(list)
                for item in completed_items:
                    completed_tasks[item[1]].append(item[0])

                validated_tasks = 0
                for task_id in completed_tasks:
                    if len(completed_tasks[task_id]) >= 100:
                        validated_tasks += 1

                if validated_tasks >= 3:
                    _msg = 'User {0} has already completed {1} tasks and ' \
                      'created {2} results for campaign {3}'.format(
                      user.username,
                      validated_tasks,
                      len(completed_items),
                      campaign.campaignName
                    )
                    LOGGER.info(_msg)
                    return None

        for active_task in active_tasks.order_by('id'):
            active_users = active_task.assignedTo.count()
            print(active_users, active_task.requiredAnnotations)
            if active_users < active_task.requiredAnnotations:
                if user and not user in active_task.assignedTo.all():
                    return active_task

        return None

    @classmethod
    def get_next_free_task_for_language_and_campaign(cls, code, campaign):
        return cls.get_next_free_task_for_language(code, campaign)

    @classmethod
    def import_from_json(cls, campaign, batch_user, batch_data, max_count):
        """
        Creates new MultiModalAssessmentTask instances based on JSON input.
        """
        batch_meta = batch_data.metadata
        batch_name = batch_data.dataFile.name
        batch_file = batch_data.dataFile
        batch_json = None

        if batch_name.endswith('.zip'):
            if not is_zipfile(batch_file):
                _msg = 'Batch {0} not a valid ZIP archive'.format(batch_name)
                LOGGER.warn(_msg)
                return

            batch_zip = ZipFile(batch_file)
            batch_json_files = [x for x in batch_zip.namelist() if x.endswith('.json')]
            # TODO: implement proper support for multiple json files in archive.
            for batch_json_file in batch_json_files:
                batch_content = batch_zip.read(batch_json_file).decode('utf-8')
                batch_json = loads(batch_content, encoding='utf-8')

        else:
            batch_json = loads(str(batch_file.read(), encoding="utf-8"))

        from datetime import datetime
        t1 = datetime.now()

        current_count = 0
        max_length_id = 0
        max_length_text = 0
        for batch_task in batch_json:
            if max_count > 0 and current_count >= max_count:
                _msg = 'Stopping after max_count={0} iterations'.format(
                  max_count
                )
                LOGGER.info(_msg)

                t2 = datetime.now()
                print(t2-t1)
                return

            print(batch_name, batch_task['task']['batchNo'])

            new_items = []
            for item in batch_task['items']:
                current_length_id = len(item['targetID'])
                current_length_text = len(item['targetText'])

                if current_length_id > max_length_id:
                    print(current_length_id, item['targetID'])
                    max_length_id = current_length_id

                if current_length_text > max_length_text:
                    print(current_length_text, item['targetText'].encode('utf-8'))
                    max_length_text = current_length_text

                new_item = TextPairWithImage(
                    sourceID=item['sourceID'],
                    sourceText=item['sourceText'],
                    targetID=item['targetID'],
                    targetText=item['targetText'],
                    imageURL=item['imageURL'],
                    createdBy=batch_user,
                    itemID=item['itemID'],
                    itemType=item['itemType']
                )
                new_items.append(new_item)

            if not len(new_items) == 100:
                _msg = 'Expected 100 items for task but found {0}'.format(
                    len(new_items)
                )
                LOGGER.warn(_msg)
                continue

            current_count += 1


            #for new_item in new_items:
            #    new_item.metadata = batch_meta
            #    new_item.save()
            batch_meta.textpairwithimage_set.add(*new_items, bulk=False)
            batch_meta.save()

            new_task = MultiModalAssessmentTask(
                campaign=campaign,
                requiredAnnotations=batch_task['task']['requiredAnnotations'],
                batchNo=batch_task['task']['batchNo'],
                batchData=batch_data,
                createdBy=batch_user,
            )
            new_task.save()

            #for new_item in new_items:
            #    new_task.items.add(new_item)
            new_task.items.add(*new_items)
            new_task.save()

            _msg = 'Success processing batch {0}, task {1}'.format(
                str(batch_data), batch_task['task']['batchNo']
            )
            LOGGER.info(_msg)

        _msg = 'Max length ID={0}, text={1}'.format(
          max_length_id, max_length_text
        )
        LOGGER.info(_msg)

        t2 = datetime.now()
        print(t2-t1)

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current DA task, checking campaign and items exist.
        """
        if not hasattr(self, 'campaign') or not self.campaign.is_valid():
            return False

        if not hasattr(self, 'items'):
            return False

        for item in self.items:
            if not item.is_valid():
                return False

        return True

    # pylint: disable=E1136
    def _generate_str_name(self):
        return '{0}.{1}[1..{2}]'.format(
          self.__class__.__name__,
          self.campaign,
          self.items.count()
        )


class MultiModalAssessmentResult(BaseMetadata):
    """
    Models a multimodal assessment evaluation result.
    """
    score = models.PositiveSmallIntegerField(
      verbose_name=_('Score'),
      help_text=_('(value in range=[1,100])')
    )

    start_time = models.FloatField(
      verbose_name=_('Start time'),
      help_text=_('(in seconds)')
    )

    end_time = models.FloatField(
      verbose_name=_('End time'),
      help_text=_('(in seconds)')
    )

    item = models.ForeignKey(
      TextPairWithImage,
      db_index=True,
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_item',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Item')
    )

    task = models.ForeignKey(
      MultiModalAssessmentTask,
      blank=True,
      db_index=True,
      null=True,
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_task',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Task')
    )

    # pylint: disable=E1136
    def _generate_str_name(self):
        return '{0}.{1}={2}'.format(
          self.__class__.__name__,
          self.item,
          self.score
        )

    def duration(self):
        d = self.end_time-self.start_time
        return round(d, 1)

    def item_type(self):
        return self.item.itemType

    @classmethod
    def get_completed_for_user(cls, user):
        return cls.objects.filter(
          createdBy=user,
          activated=False,
          completed=True
        ).count()

    @classmethod
    def get_time_for_user(cls, user):
        results = cls.objects.filter(
          createdBy=user,
          activated=False,
          completed=True
        )

        durations = []
        for result in results:
            duration = result.end_time - result.start_time
            durations.append(duration)

        return seconds_to_timedelta(sum(durations))

    @classmethod
    def compute_accurate_group_status(cls):
        from Dashboard.models import LANGUAGE_CODES_AND_NAMES
        user_status = defaultdict(list)
        qs = cls.objects.filter(completed=True)
        for result in qs.values_list('createdBy', 'item__itemType', 'task__id'):
            if result[1].lower() != 'tgt':
                continue

            annotatorID = result[0]
            taskID = result[2]
            user_status[annotatorID].append(taskID)

        group_status = defaultdict(list)
        for annotatorID in user_status:
            user = User.objects.get(pk=annotatorID)
            usergroups = ';'.join([x.name for x in user.groups.all() if not x.name in LANGUAGE_CODES_AND_NAMES.keys()])
            if not usergroups:
                usergroups = 'NoGroupInfo'

            group_status[usergroups].extend(user_status[annotatorID])

        group_hits = {}
        for group_name in group_status:
            task_ids = set(group_status[group_name])
            completed_tasks = 0
            for task_id in task_ids:
                if group_status[group_name].count(task_id) >= 70:
                    completed_tasks += 1

            group_hits[group_name] = (completed_tasks, len(task_ids))

        return group_hits

    @classmethod
    def dump_all_results_to_csv_file(cls, csv_file):
        from Dashboard.models import LANGUAGE_CODES_AND_NAMES
        system_scores = defaultdict(list)
        user_data = {}
        qs = cls.objects.filter(completed=True)
        for result in qs.values_list('item__targetID', 'score', 'start_time', 'end_time', 'createdBy', 'item__itemID', 'item__metadata__market__sourceLanguageCode', 'item__metadata__market__targetLanguageCode', 'item__metadata__market__domainName', 'item__itemType', 'task__id', 'task__campaign__campaignName'):

            systemID = result[0]
            score = result[1]
            start_time = result[2]
            end_time = result[3]
            duration = round(float(end_time)-float(start_time), 1)
            annotatorID = result[4]
            segmentID = result[5]
            marketID = '{0}-{1}'.format(result[6], result[7])
            domainName = result[8]
            itemType = result[9]
            taskID = result[10]
            campaignName = result[11]

            if annotatorID in user_data:
                username = user_data[annotatorID][0]
                useremail = user_data[annotatorID][1]
                usergroups = user_data[annotatorID][2]
            
            else:
                user = User.objects.get(pk=annotatorID)
                username = user.username
                useremail = user.email
                usergroups = ';'.join([x.name for x in user.groups.all() if not x.name in LANGUAGE_CODES_AND_NAMES.keys()])
                if not usergroups:
                    usergroups = 'NoGroupInfo'
                
                user_data[annotatorID] = (
                  username, useremail, usergroups
                )

            system_scores[marketID+'-'+domainName].append((taskID,systemID, username, useremail, usergroups, segmentID, score, start_time, end_time, duration, itemType, campaignName))

        x = system_scores
        s=['taskID,systemID,username,email,groups,segmentID,score,startTime,endTime,durationInSeconds,itemType,campaignName']
        for l in x:
            for i in x[l]:
                s.append(','.join([str(a) for a in i]))

        from os.path import join
        from Appraise.settings import BASE_DIR
        media_file_path = join(BASE_DIR, 'media', csv_file)
        with open(media_file_path, 'w') as outfile:
            for c in s:
                outfile.write(c)
                outfile.write('\n')

    @classmethod
    def get_system_annotations(cls):
        system_scores = defaultdict(list)
        qs = cls.objects.filter(completed=True, item__itemType__in=('TGT', 'CHK'))
        for result in qs.values_list('item__targetID', 'score', 'createdBy', 'item__itemID', 'item__metadata__market__sourceLanguageCode', 'item__metadata__market__targetLanguageCode'):
            systemID = result[0]
            score = result[1]
            annotatorID = result[2]
            segmentID = result[3]
            marketID = '{0}-{1}'.format(result[4], result[5])
            system_scores[marketID].append((systemID, annotatorID, segmentID, score))

        return system_scores

    @classmethod
    def get_system_scores(cls):
        system_scores = defaultdict(list)
        qs = cls.objects.filter(completed=True, item__itemType__in=('TGT', 'CHK'))
        for result in qs.values_list('item__targetID', 'score'):
            #if not result.completed or result.item.itemType not in ('TGT', 'CHK'):
            #    continue

            system_ids = result[0].split('+') #result.item.targetID.split('+')
            score = result[1] #.score

            for system_id in system_ids:
                system_scores[system_id].append(score)

        return system_scores

    @classmethod
    def get_system_status(cls, sort_index=3):
        system_scores = cls.get_system_scores()
        non_english_codes = ('de', 'fr')

        codes = ['en-{0}'.format(x) for x in non_english_codes]

        data = {}
        for code in codes:
            data[code] = {}
            for key in [x for x in system_scores if code in x]:
                data[code][key] = system_scores[key]

        output_data = {}
        for code in codes:
            total_annotations = sum([len(x) for x in data[code].values()])
            output_local = []
            for key in data[code]:
                x = data[code][key]
                z = sum(x)/total_annotations
                output_local.append((key, len(x), sum(x)/len(x), z))

            output_data[code] = list(sorted(output_local, key=lambda x: x[sort_index], reverse=True))

        return output_data

    @classmethod
    def completed_results_for_user_and_campaign(cls, user, campaign):
        results = cls.objects.filter(
          activated=False,
          completed=True,
          createdBy=user,
          task__campaign=campaign
        ).values_list('item_id', flat=True)

        return len(set(results))

class WorkAgenda(models.Model):
    user = models.ForeignKey(
      User,
      verbose_name=_('User')
    )

    campaign = models.ForeignKey(
      'Campaign.Campaign',
      verbose_name=_('Campaign')
    )

    openTasks = models.ManyToManyField(
      DirectAssessmentTask,
      blank=True,
      related_name='%(app_label)s_%(class)s_opentasks',
      related_query_name="%(app_label)s_%(class)ss_open",
      verbose_name=_('Open tasks')
    )

    completedTasks = models.ManyToManyField(
      DirectAssessmentTask,
      blank=True,
      related_name='%(app_label)s_%(class)s_completedtasks',
      related_query_name="%(app_label)s_%(class)ss_completed",
      verbose_name=_('Completed tasks')
    )

    def completed(self):
        return self.openTasks.count() == 0

    # TODO: decide whether this needs to be optimized.
    def __str__(self):
        return '{0}/{1}[{2}:{3}]'.format(
          self.user.username,
          self.campaign.campaignName,
          self.openTasks.count(),
          self.completedTasks.count()
        )


class TaskAgenda(models.Model):
    user = models.ForeignKey(
      User,
      verbose_name=_('User')
    )

    campaign = models.ForeignKey(
      'Campaign.Campaign',
      verbose_name=_('Campaign')
    )

    _open_tasks = models.ManyToManyField(
      ObjectID,
      blank=True,
      related_name='%(app_label)s_%(class)s_opentasks',
      related_query_name="%(app_label)s_%(class)ss_open",
      verbose_name=_('Open tasks')
    )

    _completed_tasks = models.ManyToManyField(
      ObjectID,
      blank=True,
      related_name='%(app_label)s_%(class)s_completedtasks',
      related_query_name="%(app_label)s_%(class)ss_completed",
      verbose_name=_('Completed tasks')
    )

    def completed(self):
        return self._open_tasks.count() == 0

    def open_tasks(self):
        return (x.get_object_instance() for x in self._open_tasks.all())

    def completed_tasks(self):
        return (x.get_object_instance() for x in self._completed_tasks.all())

    # TODO: decide whether this needs to be optimized.
    def __str__(self):
        return '{0}/{1}[{2}:{3}]'.format(
          self.user.username,
          self.campaign.campaignName,
          self._open_tasks.count(),
          self._completed_tasks.count()
        )
