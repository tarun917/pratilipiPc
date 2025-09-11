from django import forms
from django.contrib import admin
from .models import CarouselItemModel
import uuid

class CarouselItemForm(forms.ModelForm):
    class Meta:
        model = CarouselItemModel
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        ctype = cleaned.get("type")
        tid = (cleaned.get("target_id") or "").strip()

        if ctype == "digital":
            if not tid:
                raise forms.ValidationError("For digital, target_id (UUID) is required.")
            # Accept 32-hex or hyphenated; normalize to hyphenated
            try:
                cleaned["target_id"] = str(uuid.UUID(tid))
            except Exception:
                raise forms.ValidationError("For digital, target_id must be a valid UUID (32-hex or hyphenated).")
        elif ctype == "motion":
            if not tid:
                raise forms.ValidationError("For motion, target_id (integer as string) is required.")
            if not tid.isdigit():
                raise forms.ValidationError("For motion, target_id must be digits only (e.g., 12).")
        return cleaned


@admin.register(CarouselItemModel)
class CarouselItemAdmin(admin.ModelAdmin):
    form = CarouselItemForm
    list_display = ("type", "order", "target_id", "image_url")
    list_filter = ("type",)
    search_fields = ("target_id",)
    ordering = ("type", "order")