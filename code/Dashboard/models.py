# -*- coding: utf-8 -*-
from uuid import uuid4
from django.contrib.auth.models import Group, User
from django.db import models
from django.db.utils import OperationalError, ProgrammingError

LANGUAGE_CODES_AND_NAMES = {
  'ces': 'Czech (čeština)',
  'zho': 'Chinese (中文)',
  'eng': 'English',
  'fin': 'Finnish (suomi)',
  'deu': 'German (deutsch)',
  'lav': 'Latvian (latviešu)',
  'rus': 'Russian (русский)',
  'trk': 'Turkish (Türkçe)',
  'fra': 'French (français)',
  'hun': 'Hungarian (magyar)',
  'plk': 'Polish (polski)',
  'por': 'Portuguese (português)',
  'ron': 'Romanian (română)',
  'spa': 'Spanish (español)',
  'swe': 'Swedish (svenska)',
  'ara': 'Arabic (العربية)',
  'ita': 'Italian (italiano)',
  'jpn': 'Japanese (日本語)',
  'kor': 'Korean (한국어)',
  'nob': 'Norwegian (Bokmål)',
  'nld': 'Dutch (Nederlands)',
  'cat': 'Catalan (català)',
  'dan': 'Danish (dansk)',
}

# Ensure that all languages have a corresponding group.
try:
    for code in LANGUAGE_CODES_AND_NAMES.keys():
        if not Group.objects.filter(name=code).exists():
            new_language_group = Group(name=code)
            new_language_group.save()

except (OperationalError, ProgrammingError):
    pass

def create_uuid4_token():
    """
    Creates a new UUID4-based token.
    """
    return uuid4().hex[:8]

# pylint: disable=C0330,E1101
class UserInviteToken(models.Model):
    """
    User invite tokens allowing to register an account.
    """
    group = models.ForeignKey(
      Group,
      db_index=True
    )
  
    user = models.ForeignKey(
      User,
      db_index=True,
      blank=True,
      null=True
    )

    token = models.CharField(
      max_length=8,
      db_index=True,
      default=create_uuid4_token,
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

    def __str__(self):
        """
        Returns a Unicode String for this UserInviteToken object.
        """
        return u'<user-invite id="{0}" token="{1}" active="{2}" group="{3}" />'.format(
          self.id, self.token, self.active, self.group.name
        )


class TimedKeyValueData(models.Model):
    """
    Stores a simple (key, value) pair.
    """
    key = models.CharField(
      max_length=100,
      blank=False,
      null=False
    )
    value = models.TextField(
      blank=False,
      null=False
    )
    date_and_time = models.DateTimeField(
      blank=False,
      null=False,
      editable=False,
      auto_now_add=True
    )

    @classmethod
    def update_status_if_changed(cls, key, new_value):
        """
        Stores a new TimedKeyValueData instance if value for key has changed
        """
        _latest_values = cls.objects.filter(key=key)
        _latest_values = _latest_values.order_by('date_and_time').reverse()
        _latest_values = _latest_values.values_list('value', flat=True)
        if not _latest_values or _latest_values[0] != new_value:
            new_data = cls(key=key, value=new_value)
            new_data.save()
