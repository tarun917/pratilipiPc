from django.db import models
from profileDesk.models import CustomUser

class SubscriptionModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan = models.CharField(max_length=50, choices=[('3_month', '3-Month'), ('6_month', '6-Month')])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    benefits = models.TextField()
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    def __str__(self):
        return f"{self.user.username} - {self.plan}"