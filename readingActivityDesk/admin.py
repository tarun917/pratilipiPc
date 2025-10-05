from django.contrib import admin

# Register your models here.

from .models import ReadingActivity

@admin.register(ReadingActivity)
class ReadingActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "comic_id", "episode_id", "progress_percent", "last_read_at", "finished_at")
    list_filter = ("type", "finished_at")
    search_fields = ("user__username", "comic_title")