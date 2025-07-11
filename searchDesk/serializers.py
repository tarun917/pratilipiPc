from rest_framework import serializers
from .models import SearchFilterModel

class SearchFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchFilterModel
        fields = ['id', 'type', 'filter_name']