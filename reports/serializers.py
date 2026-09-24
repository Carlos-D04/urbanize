from .models import Request, RequestHistory
from accounts.models import User
from accounts.serializers import UserSerializer
from categories.models import Category
from rest_framework import serializers


UPDATE_METHODS = ('PATCH', "PUT")


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ['id', 'title', 'description', 'location', 'category', 'author', 'department', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'department', 'status', 'created_at', 'updated_at']

    # checking the brute data first 
    def validate(self, attrs):
        if self.context["request"].user.role == User.Role.CITIZEN and self.context["request"].method in UPDATE_METHODS and "category" in self.initial_data:
            raise serializers.ValidationError("Validation Error")
        return attrs 

    def create(self, validated_data):
        category = validated_data["category"]

        return Request.objects.create(department=category.department, **validated_data)

class RequestStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Request.Status.choices)

class RequestCategorySerializer(serializers.Serializer):
    category = serializers.PrimaryKeyRelatedField(queryset = Category.objects.all())


class RequestHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only = True )

    class Meta:
        model = RequestHistory
        fields = ["request", "changed_by", "old_status", "new_status", "created_at"]
        read_only_fields = ["request", "changed_by", "old_status", "new_status", "created_at"]