from django.contrib import admin
from .models import CarouselItemModel

@admin.register(CarouselItemModel)
class CarouselItemAdmin(admin.ModelAdmin):
    list_display = ('type', 'order', 'image_url')