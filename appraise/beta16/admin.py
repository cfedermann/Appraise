from django.contrib import admin

from appraise.beta16.models import AbsoluteScoringTask, AbsoluteScoringData
from appraise.beta16.models import MetaData

admin.site.register(AbsoluteScoringTask)
admin.site.register(AbsoluteScoringData)
admin.site.register(MetaData)
