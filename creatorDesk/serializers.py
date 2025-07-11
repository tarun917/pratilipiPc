from rest_framework import serializers
from .models import TermsAndConditions, Submissions, CreatorComics
from digitalcomicDesk.models import ComicModel
from django.core.exceptions import ValidationError
import re

class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = ['id', 'version', 'content', 'created_at']

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submissions
        fields = ['id', 'user', 'title', 'genre', 'language', 'tags', 'description', 'zip_url', 'cover_url', 'status', 'submitted_at', 'reviewed_at', 'views', 'earnings', 't_and_c_accepted']
        extra_kwargs = {
            'user': {'read_only': True},
        }

    def validate_description(self, value):
        if len(value) > 400:
            raise ValidationError("Description must not exceed 400 characters.")
        return value

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise ValidationError("Tags must be a list.")
        if not all(re.match(r'^[a-zA-Z0-9]+$', tag) for tag in value):
            raise ValidationError("Tags must contain only letters and numbers.")
        return value

    def validate_status(self, value):
        valid_statuses = ['Pending', 'Approved', 'Rejected']
        if value not in valid_statuses:
            raise ValidationError(f"Status must be one of {valid_statuses}")
        return value

class CreatorComicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorComics
        fields = ['id', 'submission_id', 'comic_id', 'publish_date', 'is_visible']
        extra_kwargs = {
            'submission_id': {'read_only': True},
            'comic_id': {'read_only': True},
        }