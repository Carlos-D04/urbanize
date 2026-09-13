from rest_framework import serializers
from .models import User

# this is just to be used on responses on the api
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]