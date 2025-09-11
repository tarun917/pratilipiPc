from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
import uuid


class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15, unique=True)
    unique_id = models.CharField(max_length=36, unique=True, default=uuid.uuid4)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    about = models.TextField(null=True, blank=True)

    # Note: coin_count is a denormalized balance. We will migrate to WalletLedger later and keep this in-sync.
    coin_count = models.IntegerField(default=0)

    terms_accepted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    badge = models.CharField(
        max_length=50,
        choices=[('Copper', 'Copper'), ('Gold', 'Gold')],
        default='Copper'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name', 'mobile_number']

    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['mobile_number']),
        ]

    def __str__(self):
        return self.username


class Address(models.Model):
    HOME = 'home'
    WORK = 'work'
    OTHER = 'other'
    TYPE_CHOICES = [
        (HOME, 'Home'),
        (WORK, 'Work'),
        (OTHER, 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    name = models.CharField(max_length=100, help_text="Recipient name")
    mobile_number = models.CharField(max_length=15)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20)
    country = models.CharField(max_length=64, default='India')
    address_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=HOME)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['city']),
            models.Index(fields=['pincode']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(id=self.id).update(is_default=False)