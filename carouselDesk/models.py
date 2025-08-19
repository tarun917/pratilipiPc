from django.db import models
import uuid


class CarouselItemModel(models.Model):
    TYPE_CHOICES = (('digital', 'Digital'), ('motion', 'Motion'))

    image_url = models.ImageField(upload_to='carousel/', null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    order = models.PositiveIntegerField(default=0)
    # Target comic id to navigate on click:
    # Digital comics use UUID (string), Motion comics use int -> store as string safely
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

    @staticmethod
    def _normalize_uuid_hyphenated(raw: str) -> str:
        """
        Accepts either hyphenated UUID or 32-hex; returns hyphenated UUID.
        If invalid, returns original.
        """
        try:
            return str(uuid.UUID(str(raw)))
        except Exception:
            return raw

    def save(self, *args, **kwargs):
        # Normalize digital IDs to hyphenated UUID at write-time
        if self.type == 'digital' and self.target_id:
            self.target_id = self._normalize_uuid_hyphenated(self.target_id)
        super().save(*args, **kwargs)