from django.contrib import admin

from .models import UserInviteToken, TimedKeyValueData

admin.site.register(UserInviteToken)
admin.site.register(TimedKeyValueData)
