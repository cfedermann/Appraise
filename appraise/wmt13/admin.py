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

from appraise.wmt13.models import HIT, RankingTask, RankingResult


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


class HITAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for HIT instances.
    """
    list_display = ('hit_id', 'block_id', 'language_pair')
    list_filter = ('language_pair', 'active')
    search_fields = ('hit_id',)
    readonly_fields = ('hit_id',)
    actions = (export_hit_xml,)
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


class RankingResultAdmin(admin.ModelAdmin):
    """
    ModelAdmin class for RankingResult instances.
    """
    list_display = ('item', 'user', 'readable_duration', 'results')
    list_filter = ('item__task', 'user')


admin.site.register(HIT, HITAdmin)
admin.site.register(RankingTask)
admin.site.register(RankingResult, RankingResultAdmin)
