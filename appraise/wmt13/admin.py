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

from appraise.wmt13.models import HIT, RankingTask, RankingResult, \
  UserHITMapping


# TODO: check this code.
def export_hit_xml(modeladmin, request, queryset):
    """
    Exports the tasks in the given queryset to XML download.
    """
    template = get_template('evaluation/result_export.xml')
    
    tasks = []
    for task in queryset:
        if isinstance(task, HIT):
            tasks.append(task.export_to_xml())
    
    export_xml = template.render(Context({'tasks': tasks}))
    export_filename = 'exported-tasks-{}-{}'.format(request.user,
      date.today())
    
    # We return it as a "text/xml" file attachment with charset "UTF-8".
    response = HttpResponse(export_xml, mimetype='text/xml; charset=UTF-8')
    response['Content-Disposition'] = 'attachment; filename="{0}.xml"'.format(
      export_filename)
    return response

export_hit_xml.short_description = "Export selected tasks to XML"


def export_hit_ids_to_csv(modeladmin, request, queryset):
    """
    Exports the HIT ids for the given queryset to CSV download.
    """
    results = [u'HITId,trglang']
    for result in queryset:
        if isinstance(result, HIT):
            _hit_id = result.hit_id
            _target_language = result.hit_attributes['target-language']
            results.append(u",".join((_hit_id, _target_language)))
    
    export_csv = u"\n".join(results)
    return HttpResponse(export_csv)

export_hit_ids_to_csv.short_description = "Export selected HIT ids to CSV"

class HITAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for HIT instances.
    """
    list_display = ('hit_id', 'block_id', 'language_pair')
    list_filter = ('language_pair', 'active')
    search_fields = ('hit_id',)
    readonly_fields = ('hit_id',)
    actions = (export_hit_ids_to_csv,)
    filter_horizontal = ('users',)
    
    fieldsets = (
      ('Overview', {
        'classes': ('wide',),
        'fields': ('active', 'hit_id', 'block_id', 'language_pair')
      }),
      ('Details', {
        'classes': ('wide', 'collapse'),
        'fields': ('users', 'hit_xml')
      })
    )
    
    def get_readonly_fields(self, request, obj=None):
        """
        Only modify block_id, hit_xml, language_pair on object creation.
        
        - http://stackoverflow.com/questions/2639654/django-read-only-field
        """
        if obj is not None:
            return self.readonly_fields + ('block_id', 'hit_xml',
              'language_pair')
        
        return self.readonly_fields


def export_results_to_csv(modeladmin, request, queryset):
    """
    Exports the results in the given queryset to CSV download.
    """
    results = [u'srclang,trglang,srcIndex,documentId,segmentId,judgeId,system1Number,system1Id,system2Number,system2Id,system3Number,system3Id,system4Number,system4Id,system']
    for result in queryset:
        if isinstance(result, RankingResult):
            results.append(result.export_to_csv())
    
    export_csv = u"\n".join(results)
    return HttpResponse(export_csv)
    
    # Later, we will make this a downloadable attachment instead.
    export_filename = ""
    
    # We return it as a "text/xml" file attachment with charset "UTF-8".
    response = HttpResponse(export_csv, mimetype='text/plain; charset=UTF-8')
    response['Content-Disposition'] = 'attachment; filename="{0}.csv"'.format(
      export_filename)
    return response

export_results_to_csv.short_description = "Export selected results to CSV"

class RankingResultAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for RankingResult instances.
    """
    list_display = ('item', 'user', 'readable_duration', 'results')
    list_filter = ('item__hit__language_pair', 'user')
    actions = (export_results_to_csv,)


admin.site.register(HIT, HITAdmin)
admin.site.register(RankingTask)
admin.site.register(RankingResult, RankingResultAdmin)
admin.site.register(UserHITMapping)
