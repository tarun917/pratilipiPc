from django.db import models

class CarouselItemModel(models.Model):
    image_url = models.ImageField(upload_to='carousel/', null=True, blank=True)
    type = models.CharField(max_length=20, choices=[('digital', 'Digital'), ('motion', 'Motion')])
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.type} - Item {self.order}"