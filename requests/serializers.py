from .models import Request
from rest_framework import serializers

class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['title', 'description', 'location', 'category', 'author', 'department', 'status', 'created_at', 'updated_at']
        read_only_fields = ['author', 'department', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        category = validated_data["category"]

        return Request.objects.create(department=category.department, **validated_data)