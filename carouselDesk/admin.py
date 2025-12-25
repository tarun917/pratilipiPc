from django import forms
from django.contrib import admin
from .models import CarouselItemModel


class CarouselItemForm(forms.ModelForm):
    class Meta:
        model = CarouselItemModel
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        ctype = cleaned.get("type")
        tid = (cleaned.get("target_id") or "").strip()

        # Both digital and motion comics now use simple integer IDs
        if ctype == "digital":
            if not tid:
                raise forms.ValidationError("For digital, target_id (comic ID) is required.")
            if not tid.isdigit():
                raise forms.ValidationError("For digital, target_id must be a valid integer (e.g., 1, 2, 3).")
        elif ctype == "motion":
            if not tid:
                raise forms.ValidationError("For motion, target_id (comic ID) is required.")
            if not tid.isdigit():
                raise forms.ValidationError("For motion, target_id must be a valid integer (e.g., 1, 2, 3).")

        cleaned["target_id"] = tid
        return cleaned


@admin.register(CarouselItemModel)
class CarouselItemAdmin(admin.ModelAdmin):
    form = CarouselItemForm
    list_display = ("type", "order", "target_id", "image_url")
    list_filter = ("type",)
    search_fields = ("target_id",)
    ordering = ("type", "order")