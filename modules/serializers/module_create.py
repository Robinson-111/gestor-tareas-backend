from rest_framework import serializers
from modules.models import Module
from account.models import User
from core.serializer import StrictModelSerializer

class ModuleCreateSerializer(StrictModelSerializer):

    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset = User.objects.all(),
        write_only=True,
        required=False

    )

    class Meta:
        model = Module
        fields = ['id', 'name', 'description', 'members']
        read_only_fields = [
            'id'
        ]
