# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@gmail.com>
"""
from datetime import date

from django.contrib import admin
from django.http import HttpResponse
from django.template import Context
from django.template.loader import get_template

from appraise.evaluation.models import EvaluationTask, EvaluationItem, \
  EvaluationResult


def export_task_xml(modeladmin, request, queryset):
    """
    Exports the tasks in the given queryset to XML download.
    """
    template = get_template('evaluation/result_export.xml')
    
    tasks = []
    for task in queryset:
        if isinstance(task, EvaluationTask):
            tasks.append(task.export_to_xml())
    
    export_xml = template.render(Context({'tasks': tasks}))
    export_filename = 'exported-tasks-{}-{}'.format(request.user,
      date.today())
    
    # We return it as a "text/xml" file attachment with charset "UTF-8".
    response = HttpResponse(export_xml, mimetype='text/xml; charset=UTF-8')
    response['Content-Disposition'] = 'attachment; filename="{0}.xml"'.format(
      export_filename)
    return response

export_task_xml.short_description = "Export selected tasks to XML"


class EvaluationTaskAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for EvaluationTask objects.
    """
    list_display = ('task_name', 'task_type', 'task_id')
    list_filter = ('task_type', 'active')
    search_fields = ('task_name', 'description')
    readonly_fields = ('task_id',)
    actions = (export_task_xml,)
    filter_horizontal = ('users',)
    
    fieldsets = (
      ('Required Information', {
        'classes': ('wide',),
        'fields': ('task_name', 'task_type', 'task_xml')
      }),
      ('Optional Information', {
        'classes': ('wide',),
        'fields': ('active', 'random_order', 'description', 'users')
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
    list_display = ('item', 'user', 'readable_duration', 'results')
    list_filter = ('item__task', 'user')


admin.site.register(EvaluationTask, EvaluationTaskAdmin)
admin.site.register(EvaluationItem)
admin.site.register(EvaluationResult, EvaluationResultAdmin)