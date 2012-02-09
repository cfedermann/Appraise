# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
"""
from django.contrib import admin
from django.forms import Textarea
from django.db.models import TextField
from appraise.evaluation.models import RankingTask, RankingItem, \
  RankingResult, ClassificationResult, EditingTask, EditingItem, \
  EditingResult, LucyTask, LucyItem, LucyResult, QualityTask, QualityItem, \
  QualityResult

from appraise.evaluation.models import EvaluationTask, EvaluationItem, \
  EvaluationResult


class EvaluationTaskAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for EvaluationTask objects.
    """
    list_display = ('task_name', 'task_type', 'task_id')
    list_filter = ('task_type', 'active')
    search_fields = ('task_name', 'description')
    readonly_fields = ('task_id',)
    
    fieldsets = (
      ('Required Information', {
        'classes': ('wide',),
        'fields': ('task_name', 'task_type', 'task_xml')
      }),
      ('Optional Information', {
        'classes': ('wide',),
        'fields': ('active', 'description', 'users')
      })
    )
    
    def get_readonly_fields(self, request, obj=None):
        """
        We only allow changing task_xml and task_type on object creation.
        
        - http://stackoverflow.com/questions/2639654/django-read-only-field
        """
        if obj is not None:
            return self.readonly_fields + ('task_xml', 'task_type')
        
        return self.readonly_fields


class EvaluationResultAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for EvaluationResult objects.
    """
    list_display = ('item', 'user', 'duration', 'results')
    list_filter = ('item', 'user')


class QualityTaskAdmin(admin.ModelAdmin):
    """Admin class for QualityTask instances."""
    list_display = ('shortname', 'task_id', 'completed')
    search_fields = ('shortname', 'description')
    readonly_fields = ('task_id',)
    
    fieldsets = (
      (None, {
        'fields': ('shortname', 'description', 'users')
      }),
      ('Advanced Options', {
        'classes': ('collapse',),
        'fields': ('task_id',)
      })
    )

class QualityItemAdmin(admin.ModelAdmin):
    """Admin class for QualityItem instances."""
    list_display = ('source', 'translation')
    list_filter = ('edited',)
    search_fields = ('source', 'translation', 'context')
    
    fieldsets = (
      (None, {
        'fields': ('source', 'translation', 'context')
      }),
      ('Advanced Options', {
        'classes': ('collapse',),
        'fields': ('edited', 'task')
      })
    )
    
    formfield_overrides = {
      TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
    }

class QualityResultAdmin(admin.ModelAdmin):
    """Admin class for QualityResult instances."""
    list_display = ('quality', 'item', 'user', 'duration_in_seconds')
    list_filter = ('quality', 'user')
    exclude = ('duration',)

    fieldsets = (
      (None, {
        'fields': ('quality', 'item', 'user',)
      }),
    )

admin.site.register(RankingTask)
admin.site.register(RankingItem)
admin.site.register(RankingResult)
admin.site.register(ClassificationResult)
admin.site.register(EditingTask)
admin.site.register(EditingItem)
admin.site.register(EditingResult)
admin.site.register(LucyTask)
admin.site.register(LucyItem)
admin.site.register(LucyResult)
admin.site.register(QualityTask, QualityTaskAdmin)
admin.site.register(QualityItem, QualityItemAdmin)
admin.site.register(QualityResult, QualityResultAdmin)

admin.site.register(EvaluationTask, EvaluationTaskAdmin)
admin.site.register(EvaluationItem)
admin.site.register(EvaluationResult, EvaluationResultAdmin)