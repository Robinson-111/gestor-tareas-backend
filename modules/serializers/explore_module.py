from rest_framework import serializers
from modules.models import Module


class ExploreModuleSerializer(serializers.ModelSerializer):
    has_owner = serializers.BooleanField(read_only=True)
    owner_name = serializers.CharField(read_only=True, allow_null=True)
    creator_name = serializers.CharField(
        source='creator.name',
        read_only=True,
        allow_null=True,
    )
    total_tasks = serializers.IntegerField(read_only=True)
    pending_tasks = serializers.IntegerField(read_only=True)
    in_progress_tasks = serializers.IntegerField(read_only=True)
    completed_tasks = serializers.IntegerField(read_only=True)

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
            'has_owner',
            'owner_name',
            'total_tasks',
            'pending_tasks',
            'in_progress_tasks',
            'completed_tasks'
        ]
        read_only_fields = fields
