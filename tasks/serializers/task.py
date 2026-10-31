from rest_framework import serializers

from account.models import User
from core.serializer import StrictModelSerializer
from tasks.models import Tasks


class TaskSerializer(serializers.ModelSerializer):
    assignee_id = serializers.IntegerField(
        read_only=True,
        allow_null=True
    )
    assignee_name = serializers.CharField(
        source='assignee.name',
        read_only=True,
        allow_null=True
    )
    module_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tasks
        fields = [
            'id',
            'title',
            'description',
            'priority',
            'state',
            'assignee_id',
            'assignee_name',
            'module_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class TaskCreateSerializer(StrictModelSerializer):
    assignee_id = serializers.PrimaryKeyRelatedField(
        source='assignee',
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            'does_not_exist': 'El usuario especificado no existe.',
            'incorrect_type': 'El ID del usuario debe ser un número entero.'
        }
    )

    class Meta:
        model = Tasks
        fields = ['title', 'description', 'priority', 'assignee_id']
        extra_kwargs = {
            'title': {
                'required': True,
                'allow_blank': False,
                'error_messages': {
                    'required': 'El título es obligatorio.',
                    'blank': 'El título no puede estar vacío.'
                }
            },
            'priority': {
                'required': False
            }
        }


class TaskUpdateSerializer(StrictModelSerializer):
    assignee_id = serializers.PrimaryKeyRelatedField(
        source='assignee',
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            'does_not_exist': 'El usuario especificado no existe.',
            'incorrect_type': 'El ID del usuario debe ser un número entero.'
        }
    )

    class Meta:
        model = Tasks
        fields = ['title', 'description', 'priority', 'state', 'assignee_id']
        extra_kwargs = {
            'title': {
                'required': False,
                'allow_blank': False,
                'error_messages': {
                    'blank': 'El título no puede estar vacío.'
                }
            }
        }
