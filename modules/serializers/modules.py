from rest_framework import serializers
from modules.models import Module

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'name', 'description', 'state', 'creator', 'created_at' , 'updated_at']
        read_only_fields = [
            'id',
            'creator',
            'created_at',
            'updated_at'
        ]