# digitalcomicDesk/admin.py
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.utils.html import format_html

from .models import (
    ComicModel,
    EpisodeModel,
    CommentModel,
    SliceModel,
    EpisodeAccess,
)
from .forms import EpisodeZipUploadForm
    # Expects a single FileField named 'zip_file'
from .services import import_episode_slices_zip
    # Expects import_episode_slices_zip(episode, zip_file) -> report with .errors, .created_slices, .replaced_existing, .accepted_images, .total_in_zip


@admin.register(ComicModel)
class ComicAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'rating', 'view_count', 'favourite_count')
    search_fields = ('title', 'genre')
    list_filter = ('genre',)
    readonly_fields = ()


class SliceInline(admin.TabularInline):
    model = SliceModel
    extra = 0
    fields = ('order', 'file', 'width', 'height')
    ordering = ('order',)
    show_change_link = True


class CommentInline(admin.TabularInline):
    model = CommentModel
    extra = 0
    fields = ('user', 'parent', 'comment_text', 'likes_count', 'timestamp')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    show_change_link = True


@admin.register(EpisodeModel)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = (
        'comic',
        'episode_number',
        'is_free',
        'is_locked',
        'coin_cost',
        'likes_count',
        'shares_count',
        'comments_count',
    )
    list_filter = ('is_free', 'is_locked', 'comic')
    search_fields = ('comic__title',)
    ordering = ('comic', 'episode_number')
    inlines = [SliceInline, CommentInline]
    readonly_fields = ('upload_zip_action',)
    fields = (
        'comic',
        'episode_number',
        'thumbnail',
        'content_url',   # legacy optional
        'content_file',  # legacy optional
        'is_free',
        'coin_cost',
        'is_locked',
        'likes_count',
        'shares_count',
        'comments_count',
        'upload_zip_action',
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'upload-zip/<path:object_id>/',
                self.admin_site.admin_view(self.upload_zip_view),
                name='digitalcomicDesk_episodemodel_upload_zip',
            ),
        ]
        return custom + urls

    def upload_zip_action(self, obj):
        """
        Readonly field showing a button/link on the Episode change page to upload a ZIP.
        """
        if not obj or not obj.pk:
            return "Save this episode first to enable ZIP upload."
        url = reverse('admin:digitalcomicDesk_episodemodel_upload_zip', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" '
            'style="display:inline-block;padding:6px 10px;background:#0b5ed7;'
            'color:#fff;border-radius:4px;text-decoration:none;">'
            'Upload Slices ZIP (Replace All)</a>',
            url
        )
    upload_zip_action.short_description = "Slices Import"

    def upload_zip_view(self, request, object_id, *args, **kwargs):
        """
        Custom admin view to upload a ZIP of slices for a given Episode.
        """
        episode = get_object_or_404(EpisodeModel, pk=object_id)

        if request.method == 'POST':
            form = EpisodeZipUploadForm(request.POST, request.FILES)
            if form.is_valid():
                zip_file = form.cleaned_data['zip_file']
                report = import_episode_slices_zip(episode, zip_file)

                if getattr(report, 'errors', None):
                    for err in report.errors:
                        messages.error(request, err)

                created = getattr(report, 'created_slices', 0)
                replaced = getattr(report, 'replaced_existing', 0)
                accepted = getattr(report, 'accepted_images', 0)
                total = getattr(report, 'total_in_zip', 0)

                messages.info(
                    request,
                    f"ZIP processed: total={total}, accepted_images={accepted}, "
                    f"replaced_existing={replaced}, created_slices={created}"
                )

                change_url = reverse('admin:digitalcomicDesk_episodemodel_change', args=[episode.pk])
                return redirect(change_url)
        else:
            form = EpisodeZipUploadForm()

        context = dict(
            self.admin_site.each_context(request),
            title=f"Upload slices ZIP for Episode #{episode.episode_number}",
            form=form,
            episode=episode,
            opts=self.model._meta,
        )

        # Renders a simple admin page with the form.
        # Template path expected: templates/admin/digitalcomicDesk/episode_upload_zip.html
        return TemplateResponse(
            request,
            'admin/digitalcomicDesk/episode_upload_zip.html',
            context
        )


@admin.register(CommentModel)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('episode', 'user', 'parent', 'comment_text', 'likes_count', 'timestamp')
    list_filter = ('episode', 'user')
    search_fields = ('comment_text', 'user__username', 'episode__comic__title')
    ordering = ('-timestamp',)
    readonly_fields = ()


@admin.register(SliceModel)
class SliceAdmin(admin.ModelAdmin):
    list_display = ('episode', 'order', 'file', 'width', 'height')
    list_filter = ('episode',)
    search_fields = ('episode__comic__title',)
    ordering = ('episode', 'order')


@admin.register(EpisodeAccess)
class EpisodeAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'episode', 'source', 'unlocked_at')
    list_filter = ('source', 'episode__comic')
    search_fields = ('user__username', 'episode__comic__title')
    ordering = ('-unlocked_at',)