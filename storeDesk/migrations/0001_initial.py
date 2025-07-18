# Generated by Django 5.2.3 on 2025-07-05 19:08

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Comic',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='comics/covers/')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('description', models.TextField()),
                ('pages', models.PositiveIntegerField()),
                ('rating', models.DecimalField(decimal_places=1, default=0.0, max_digits=3)),
                ('rating_count', models.PositiveIntegerField(default=0)),
                ('buyer_count', models.PositiveIntegerField(default=0)),
                ('stock_quantity', models.PositiveIntegerField(default=0)),
                ('preview_file', models.FileField(blank=True, null=True, upload_to='comics/previews/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('genres', models.ManyToManyField(to='storeDesk.genre')),
            ],
        ),
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('promotion_notifications', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('purchase_date', models.DateTimeField(auto_now_add=True)),
                ('buyer_name', models.CharField(max_length=255)),
                ('email', models.EmailField(max_length=254)),
                ('mobile', models.CharField(max_length=15)),
                ('address', models.TextField()),
                ('pin_code', models.CharField(max_length=10)),
                ('comic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storeDesk.comic')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Promotion',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('discount_percentage', models.PositiveSmallIntegerField(default=0)),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_date', models.DateTimeField()),
                ('genre', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='storeDesk.genre')),
            ],
        ),
        migrations.CreateModel(
            name='RestockNotification',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('notified', models.BooleanField(default=False)),
                ('comic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storeDesk.comic')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)])),
                ('comment', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storeDesk.comic')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Wishlist',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('comic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storeDesk.comic')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'comic')},
            },
        ),
    ]
