from rest_framework import serializers
from modules.models import Module

class EditModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'name', 'description', 'state']
        read_only_fields = [
            'id'
        ]