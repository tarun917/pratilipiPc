from django.db import models
from profileDesk.models import CustomUser
import uuid
from rest_framework import serializers

class TermsAndConditions(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.CharField(max_length=10)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Terms v{self.version}"

class Submissions(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    language = models.CharField(max_length=50)
    tags = models.JSONField(default=list)
    description = models.TextField(max_length=400)
    zip_url = models.URLField()
    cover_url = models.URLField()
    status = models.CharField(max_length=50, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    views = models.IntegerField(default=0)
    earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    t_and_c_accepted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Debug print with type checking
        status_value = self.status if isinstance(self.status, str) else str(self.status) if self.status else ''
        print(f"Saving submission: status={status_value}, t_and_c_accepted={self.t_and_c_accepted}, length={len(status_value) if status_value else 0}")
        if not self.t_and_c_accepted:
            raise ValueError("Terms and Conditions must be accepted before submission.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Submission {self.title} by {self.user.username}"

class CreatorComics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission_id = models.ForeignKey(Submissions, on_delete=models.CASCADE)
    comic_id = models.ForeignKey('digitalcomicDesk.ComicModel', on_delete=models.CASCADE)
    publish_date = models.DateTimeField(null=True, blank=True)
    is_visible = models.BooleanField(default=True)

    def __str__(self):
        return f"Creator Comic {self.comic_id.title}"
    

class SubmissionStartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submissions
        fields = ['title', 'genre', 'language', 'tags', 'description', 't_and_c_accepted']
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return Submissions.objects.create(**validated_data)