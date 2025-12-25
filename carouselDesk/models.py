from django.db import models


class CarouselItemModel(models.Model):
    TYPE_CHOICES = (('digital', 'Digital'), ('motion', 'Motion'))

    image_url = models.ImageField(upload_to='carousel/', null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    order = models.PositiveIntegerField(default=0)
    # Target comic id to navigate on click:
    # Both Digital and Motion comics now use simple integer IDs
    target_id = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['type', 'order'], name='uniq_carousel_type_order'),
        ]
        indexes = [
            models.Index(fields=['type', 'order']),
        ]
        ordering = ['order']

    def __str__(self):
        return f"{self.type} - Item {self.order}"

    def save(self, *args, **kwargs):
        # Normalize target_id - strip whitespace
        if self.target_id:
            self.target_id = str(self.target_id).strip()
        super().save(*args, **kwargs)