from django.db import models
from profileDesk.models import CustomUser
from django.utils import timezone
import uuid

class Genre(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Comic(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    cover_image = models.ImageField(upload_to='comics/covers/', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    pages = models.PositiveIntegerField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    rating_count = models.PositiveIntegerField(default=0)
    buyer_count = models.PositiveIntegerField(default=0)
    stock_quantity = models.PositiveIntegerField(default=0)
    preview_file = models.FileField(upload_to='comics/previews/', null=True, blank=True)
    genres = models.ManyToManyField(Genre)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)
    buyer_name = models.CharField(max_length=255)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    pin_code = models.CharField(max_length=10)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

class Review(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} on {self.comic.title}"

class Wishlist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comic')

    def __str__(self):
        return f"{self.user.username}'s wishlist item {self.comic.title}"

class Promotion(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True)
    discount_percentage = models.PositiveSmallIntegerField(default=0)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    def __str__(self):
        return self.title

class NotificationPreference(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    promotion_notifications = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s notification preference"

class RestockNotification(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    requested_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s restock request for {self.comic.title}"