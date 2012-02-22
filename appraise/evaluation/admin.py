# -*- coding: utf-8 -*-
"""
Project: Appraise evaluation system
 Author: Christian Federmann <cfedermann@dfki.de>
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
    
    # We return it as a "text/plain" file attachment with charset "UTF-8".
    response = HttpResponse(export_xml, mimetype='text/xml; charset=UTF-8')
    response['Content-Disposition'] = 'attachment; filename="{0}.xml"'.format(
      export_filename)
    return response

export_task_xml.short_description = "Export selected tasks to XML"


def export_feature_vectors(modeladmin, request, queryset):
    """
    Exports feature vectors for the tasks in the given query to download.
    """
    feature_vectors = []
    
    results = []
    for task in queryset:
        if isinstance(task, EvaluationTask) and task.task_type == '5':
            for item in EvaluationItem.objects.filter(task=task):
                for _result in item.evaluationresult_set.all():
                    results.append(_result.id)
    
    for result_id in results:
        result = EvaluationResult.objects.get(pk=result_id)
        if not result:
            continue
        
        _classes = ('YES', 'YES')
        if result.raw_result == 'SKIPPED':
            _classes = ('NO', 'NO')
        elif result.raw_result == 'A>B':
            _classes = ('YES', 'NO')
        elif result.raw_result == 'A<B':
            _classes = ('NO', 'YES')
        
        translationA_attr = result.item.translations[0][1]
        translationB_attr = result.item.translations[1][1]
        
        featuresA = []
        featuresB = []
        for index in range(12):
            _feature = 'feat{}'.format(index)
            featuresA.append(str(getattr(translationA_attr, _feature, 0)))
            featuresB.append(str(getattr(translationB_attr, _feature, 0)))
        
        featuresA.append(_classes[0])
        featuresB.append(_classes[1])
                
        feature_vectors.append('\t'.join(tuple(featuresA)))
        feature_vectors.append('\t'.join(tuple(featuresB)))
    
    features_filename = 'exported-features-{}-{}'.format(request.user,
      date.today())
    response = HttpResponse('\n'.join(feature_vectors), mimetype='text/plain')
    response['Content-Disposition'] = 'attachment; filename="{}.data"'.format(
      features_filename)
    return response

export_feature_vectors.short_description = 'Export feature vectors for ' \
  'selected tasks'


class EvaluationTaskAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for EvaluationTask objects.
    """
    list_display = ('task_name', 'task_type', 'task_id')
    list_filter = ('task_type', 'active')
    search_fields = ('task_name', 'description')
    readonly_fields = ('task_id',)
    actions = (export_task_xml, export_feature_vectors)
    
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
    list_display = ('item', 'user', 'readable_duration', 'results')
    list_filter = ('item__task', 'user')


admin.site.register(EvaluationTask, EvaluationTaskAdmin)
admin.site.register(EvaluationItem)
admin.site.register(EvaluationResult, EvaluationResultAdmin)