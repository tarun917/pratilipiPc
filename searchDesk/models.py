from django.db import models

class SearchFilterModel(models.Model):
    type = models.CharField(max_length=20, choices=[('digital', 'Digital'), ('motion', 'Motion')])
    filter_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.type} - {self.filter_name}"