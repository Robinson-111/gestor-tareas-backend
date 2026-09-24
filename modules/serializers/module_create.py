from rest_framework import serializers
from modules.models import Module
from core.serializer import StrictModelSerializer

class ModuleCreateSerializer(StrictModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'name', 'description']
        read_only_fields = [
            'id'
        ]
