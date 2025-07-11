from datetime import timezone
from django.contrib import admin
from django.utils.html import format_html
from .models import TermsAndConditions, Submissions, CreatorComics
from django.urls import reverse
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

class SubmissionsAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'submitted_at', 'zip_url_link')
    list_filter = ('status', 'user', 'submitted_at')
    actions = ['approve_submission', 'reject_submission']

    def zip_url_link(self, obj):
        if obj.zip_url:
            return format_html('<a href="{}" target="_blank">View ZIP</a>', obj.zip_url)
        return "Not uploaded"
    zip_url_link.short_description = 'ZIP URL'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('user')

    def approve_submission(self, request, queryset):
        for submission in queryset:
            submission.status = 'Approved'
            submission.reviewed_at = timezone.now()
            submission.save()
        self.message_user(request, "Selected submissions approved.")
    approve_submission.short_description = "Approve selected submissions"

    def reject_submission(self, request, queryset):
        for submission in queryset:
            submission.status = 'Rejected'
            submission.reviewed_at = timezone.now()
            submission.save()
        self.message_user(request, "Selected submissions rejected.")
    reject_submission.short_description = "Reject selected submissions"

class TermsAndConditionsAdmin(admin.ModelAdmin):
    list_display = ('version', 'created_at')

class CreatorComicsAdmin(admin.ModelAdmin):
    list_display = ('submission_id', 'comic_id', 'publish_date', 'is_visible')

admin.site.register(TermsAndConditions, TermsAndConditionsAdmin)
admin.site.register(Submissions, SubmissionsAdmin)
admin.site.register(CreatorComics, CreatorComicsAdmin)