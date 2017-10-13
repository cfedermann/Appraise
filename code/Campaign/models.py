"""
Campaign models.py
"""
# pylint: disable=C0330
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy as f
from django.utils.translation import ugettext_lazy as _

from EvalData.models import BaseMetadata, Market, Metadata

MAX_TEAMNAME_LENGTH = 250
MAX_SMALLINTEGER_VALUE = 32767
MAX_FILEFILED_SIZE = 10 # TODO: this does not get enforced currently; remove?
MAX_CAMPAIGNNAME_LENGTH = 250


class CampaignTeam(BaseMetadata):
    """
    Models a campaign team.
    """
    teamName = models.CharField(
      max_length=MAX_TEAMNAME_LENGTH,
      verbose_name=_('Team name'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_TEAMNAME_LENGTH))
    )

    owner = models.ForeignKey(
      User,
      limit_choices_to={'is_staff': True},
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_owner',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Team owner'),
      help_text=_('(must be staff member)')
    )

    members = models.ManyToManyField(
      User,
      related_name='%(app_label)s_%(class)s_members',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Team members')
    )

    requiredAnnotations = models.PositiveSmallIntegerField(
      verbose_name=_('Required annotations'),
      help_text=_(f('(value in range=[1,{value}])',
        value=MAX_SMALLINTEGER_VALUE))
    )

    requiredHours = models.PositiveSmallIntegerField(
      verbose_name=_('Required hours'),
      help_text=_(f('(value in range=[1,{value}])',
        value=MAX_SMALLINTEGER_VALUE))
    )

    class Meta:
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'

    def _generate_str_name(self):
        return '{0} ({1})'.format(
          self.teamName, self.owner
        )

    def is_valid(self):
        """
        Validates the current CampaignTeam instance.
        """
        try:
            self.full_clean()
            return True

        except ValidationError:
            return False

    # pylint: disable=C0103,E1101
    def teamMembers(self):
        """
        Proxy method returning members count.
        """
        return self.members.count()
    teamMembers.short_description = '# of team members'

    # TODO: Connect to actual data, producing correct completion status.
    def completionStatus(self):
        """
        Proxy method return completion status in percent.

        This is defined to be the minimum of:
        - # of completed annotations / # required annotations; and
        - # of completed hours / # required hours.
        """
        return '0%'
    completionStatus.short_description = 'Completion status'


class CampaignData(BaseMetadata):
    """
    Models a batch of campaign data.
    """
    dataFile = models.FileField(
      verbose_name=_('Data file'),
      upload_to='Batches'
    )

    market = models.ForeignKey(
      Market,
      on_delete=models.PROTECT,
      verbose_name=_('Market')
    )

    metadata = models.ForeignKey(
      Metadata,
      on_delete=models.PROTECT,
      verbose_name=_('Metadata')
    )

    dataValid = models.BooleanField(
      blank=True,
      default=False,
      editable=False,
      verbose_name=_('Data valid?')
    )

    dataReady = models.BooleanField(
      blank=True,
      default=False,
      editable=False,
      verbose_name=_('Data ready?')
    )

    # pylint: disable=C0111,R0903
    class Meta:
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'

    def _generate_str_name(self):
        return self.dataFile.name

    # pylint: disable=C0103
    def dataName(self):
        return self.dataFile.name

    def activate(self):
        """
        Only activate current campaign data instance if both valid and ready.
        """
        if self.dataValid and self.dataReady:
            super(CampaignData, self).activate()

    def clean_fields(self, exclude=None):
        if self.activated:
            if not self.dataValid or not self.dataReady:
                raise ValidationError(
                  _('Cannot activate campaign data as it is either not valid or not ready yet.')
                )

        super(CampaignData, self).clean_fields(exclude)


class Campaign(BaseMetadata):
    """
    Models an evaluation campaign.
    """
    campaignName = models.CharField(
      max_length=MAX_CAMPAIGNNAME_LENGTH,
      verbose_name=_('Campaign name'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_CAMPAIGNNAME_LENGTH))
    )

    teams = models.ManyToManyField(
      CampaignTeam,
      related_name='%(app_label)s_%(class)s_teams',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Teams')
    )

    batches = models.ManyToManyField(
      CampaignData,
      related_name='%(app_label)s_%(class)s_batches',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Batches')
    )

    def _generate_str_name(self):
        return self.campaignName


class TrustedUser(models.Model):
    user = models.ForeignKey(
      User,
      verbose_name=_('User')
    )

    campaign = models.ForeignKey(
      Campaign,
      verbose_name=_('Campaign')
    )

    # TODO: decide whether this needs to be optimized.
    def __str__(self):
        return 'trusted:{0}/{1}'.format(
          self.user.username,
          self.campaign.campaignName
        )
