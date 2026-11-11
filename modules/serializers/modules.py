from rest_framework import serializers
from modules.models import Module


class ModuleSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(
        source='creator.name',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Module
        fields = [
            'id',
            'name',
            'description',
            'state',
            'creator',
            'creator_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'creator',
            'creator_name',
            'created_at',
            'updated_at',
        ]
