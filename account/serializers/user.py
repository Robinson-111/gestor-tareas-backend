from rest_framework import serializers
from account.models import User


class UserSerializer(serializers.ModelSerializer):
    modules_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'name',
            'email',
            'rol',
            'created_at',
            'modules_count',
            'tasks_count',
        )
        read_only_fields = ('id', 'rol', 'created_at', 'modules_count', 'tasks_count')

    def get_modules_count(self, obj):
        value = getattr(obj, 'modules_count', None)
        if value is not None:
            return value
        return obj.user_modules.count()

    def get_tasks_count(self, obj):
        value = getattr(obj, 'tasks_count', None)
        if value is not None:
            return value
        return obj.tasks.count()
