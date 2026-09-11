from .models import Request, RequestHistory
from rest_framework import serializers

class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['id', 'title', 'description', 'location', 'category', 'author', 'department', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'department', 'status', 'created_at', 'updated_at']

    def create(self, validated_data):
        category = validated_data["category"]

        return Request.objects.create(department=category.department, **validated_data)

class RequestStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Request.Status.choices)


class RequestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestHistory
        fields = ["request", "changed_by", "old_status", "new_status", "created_at"]
        read_only_fields = ["request", "changed_by", "old_status", "new_status", "created_at"]