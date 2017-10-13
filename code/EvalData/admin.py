"""
EvalData admin.py
"""
# pylint: disable=C0330
from datetime import datetime
from django.contrib import admin
from django.utils.timezone import utc
from .models import Market, Metadata, TextSegment, TextPair, TextPairWithImage
from .models import DirectAssessmentTask, DirectAssessmentResult
from .models import MultiModalAssessmentTask, MultiModalAssessmentResult
from .models import WorkAgenda, TaskAgenda

# TODO:chrife: find a way to use SELECT-based filtering widgets
class BaseMetadataAdmin(admin.ModelAdmin):
    """
    Model admin for abstract base metadata object model.
    """
    list_display = [
      'modifiedBy', 'dateModified'
    ]
    list_filter = [
      'activated', 'completed', 'retired'
    ]
    search_fields = [
      'createdBy__username', 'activatedBy__username', 'completedBy__username',
      'retiredBy__username', 'modifiedBy__username', '_str_name'
    ]

    # pylint: disable=C0111,R0903
    class Meta:
        abstract = True

    fieldsets = (
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('activated', 'completed', 'retired')
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        utc_now = datetime.utcnow().replace(tzinfo=utc)
        
        if not hasattr(obj, 'createdBy') or obj.createdBy is None:
            obj.createdBy = request.user
            obj.dateCreated = utc_now
            obj.save()

        if obj.activated:
            if not hasattr(obj, 'activatedBy') or obj.activatedBy is None:
                obj.activatedBy = request.user
                obj.dateActivated = utc_now
                obj.save()

        if obj.completed:
            if not hasattr(obj, 'completedBy') or obj.completedBy is None:
                obj.completedBy = request.user
                obj.dateCompleted = utc_now
                obj.save()

        if obj.retired:
            if not hasattr(obj, 'retiredBy') or obj.retiredBy is None:
                obj.retiredBy = request.user
                obj.dateRetired = utc_now
                obj.save()

        obj.modifiedBy = request.user
        obj.dateModified = utc_now
        obj.save()

        super(BaseMetadataAdmin, self).save_model(request, obj, form, change)


class MarketAdmin(BaseMetadataAdmin):
    """
    Model admin for Market instances.
    """
    list_display = [
      '__str__', 'sourceLanguageCode', 'targetLanguageCode', 'domainName'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'sourceLanguageCode', 'targetLanguageCode', 'domainName'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      'marketID'
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': (['sourceLanguageCode', 'targetLanguageCode',
          'domainName'])
      }),
    ) + BaseMetadataAdmin.fieldsets


class MetadataAdmin(BaseMetadataAdmin):
    """
    Model admin for Metadata instances.
    """
    list_display = [
      'market', 'corpusName', 'versionInfo', 'source'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'market__marketID', 'corpusName', 'versionInfo'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      'market__marketID', 'corpusName', 'versionInfo', 'source'
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': (['market', 'corpusName', 'versionInfo', 'source'])
      }),
    ) + BaseMetadataAdmin.fieldsets


class TextSegmentAdmin(BaseMetadataAdmin):
    """
    Model admin for TextSegment instances.
    """
    list_display = [
      'metadata', 'itemID', 'itemType', 'segmentID', 'segmentText'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'metadata__corpusName', 'metadata__versionInfo',
      'metadata__market__sourceLanguageCode',
      'metadata__market__targetLanguageCode',
      'metadata__market__domainName',
      'itemType'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      'segmentID', 'segmentText'
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': (['metadata', 'itemID', 'itemType', 'segmentID',
          'segmentText'])
      }),
    ) + BaseMetadataAdmin.fieldsets


class TextPairAdmin(BaseMetadataAdmin):
    """
    Model admin for TextPair instances.
    """
    list_display = [
      '__str__', 'itemID', 'itemType', 'sourceID', 'sourceText', 'targetID',
      'targetText'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'metadata__corpusName', 'metadata__versionInfo',
      'metadata__market__sourceLanguageCode',
      'metadata__market__targetLanguageCode',
      'metadata__market__domainName',
      'itemType'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      'sourceID', 'sourceText', 'targetID', 'targetText'
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': (['metadata', 'itemID', 'itemType', 'sourceID',
          'sourceText', 'targetID', 'targetText'])
      }),
    ) + BaseMetadataAdmin.fieldsets


class TextPairWithImageAdmin(BaseMetadataAdmin):
    """
    Model admin for TextPairWithImage instances.
    """
    list_display = [
      '__str__', 'itemID', 'itemType', 'sourceID', 'sourceText', 'targetID',
      'targetText', 'imageURL'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'metadata__corpusName', 'metadata__versionInfo',
      'metadata__market__sourceLanguageCode',
      'metadata__market__targetLanguageCode',
      'metadata__market__domainName',
      'itemType'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      'sourceID', 'sourceText', 'targetID', 'targetText'
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': (['metadata', 'itemID', 'itemType', 'sourceID',
          'sourceText', 'targetID', 'targetText', 'imageURL'])
      }),
    ) + BaseMetadataAdmin.fieldsets


class DirectAssessmentTaskAdmin(BaseMetadataAdmin):
    """
    Model admin for DirectAssessmentTask instances.
    """
    list_display = [
      'dataName', 'batchNo', 'campaign', 'requiredAnnotations'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'campaign__campaignName', 'campaign__batches__market__targetLanguageCode', 'campaign__batches__market__sourceLanguageCode', 'batchData'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      'campaign__campaignName', 'assignedTo'
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': (['batchData', 'batchNo', 'campaign', 'items', 'requiredAnnotations', 'assignedTo'])
      }),
    ) + BaseMetadataAdmin.fieldsets


class DirectAssessmentResultAdmin(BaseMetadataAdmin):
    """
    Model admin for DirectAssessmentResult instances.
    """
    list_display = [
      '__str__', 'score', 'start_time', 'end_time', 'duration', 'item_type'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'item__itemType', 'task__completed'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      # nothing model specific
    ] + BaseMetadataAdmin.search_fields

    readonly_fields = ('item', 'task')

    fieldsets = (
      (None, {
        'fields': (['score', 'start_time', 'end_time'])
      }),
      ('Related', {
        'fields': (['item', 'task'])
      })
    ) + BaseMetadataAdmin.fieldsets

class MultiModalAssessmentTaskAdmin(BaseMetadataAdmin):
    """
    Model admin for MultiModalAssessmentTask instances.
    """
    list_display = [
      'dataName', 'batchNo', 'campaign', 'requiredAnnotations'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'campaign__campaignName', 'campaign__batches__market__targetLanguageCode', 'campaign__batches__market__sourceLanguageCode', 'batchData'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      'campaign__campaignName', 'assignedTo'
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': (['batchData', 'batchNo', 'campaign', 'items', 'requiredAnnotations', 'assignedTo'])
      }),
    ) + BaseMetadataAdmin.fieldsets


class MultiModalAssessmentResultAdmin(BaseMetadataAdmin):
    """
    Model admin for MultiModalAssessmentResult instances.
    """
    list_display = [
      '__str__', 'score', 'start_time', 'end_time', 'duration', 'item_type'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'item__itemType', 'task__completed'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      # nothing model specific
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': (['score', 'start_time', 'end_time', 'item', 'task'])
      }),
    ) + BaseMetadataAdmin.fieldsets


class WorkAgendaAdmin(admin.ModelAdmin):
    """
    Model admin for WorkAgenda object model.
    """
    list_display = [
      'user', 'campaign', 'is_agenda_completed'
    ]
    list_filter = [
      'campaign'
    ]
    search_fields = [
      'user__username', 'campaign__campaignName'
    ]

    def is_agenda_completed(self, obj):
        return obj.completed()
    is_agenda_completed.short_description = 'Completed?'


class TaskAgendaAdmin(admin.ModelAdmin):
    """
    Model admin for TaskAgenda object model.
    """
    list_display = [
      'user', 'campaign', 'is_agenda_completed'
    ]
    list_filter = [
      'campaign'
    ]
    search_fields = [
      'user__username', 'campaign__campaignName'
    ]

    def is_agenda_completed(self, obj):
        return obj.completed()
    is_agenda_completed.short_description = 'Completed?'


admin.site.register(Market, MarketAdmin)
admin.site.register(Metadata, MetadataAdmin)
admin.site.register(TextSegment, TextSegmentAdmin)
admin.site.register(TextPair, TextPairAdmin)
admin.site.register(TextPairWithImage, TextPairWithImageAdmin)
admin.site.register(DirectAssessmentTask, DirectAssessmentTaskAdmin)
admin.site.register(DirectAssessmentResult, DirectAssessmentResultAdmin)
admin.site.register(MultiModalAssessmentTask, MultiModalAssessmentTaskAdmin)
admin.site.register(MultiModalAssessmentResult, MultiModalAssessmentResultAdmin)
admin.site.register(WorkAgenda, WorkAgendaAdmin)
admin.site.register(TaskAgenda, TaskAgendaAdmin)