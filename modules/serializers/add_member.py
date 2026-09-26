from rest_framework import serializers
from account.models import User
from modules.models import UserModule
from core.serializer import StrictModelSerializer


class AddMemberModuleSerializer(StrictModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        required=True,
        error_messages={
            'does_not_exist': 'El usuario especificado no existe.',
            'incorrect_type': 'El ID del usuario debe ser un número entero.'
        }
    )
    rol = serializers.ChoiceField(
        choices=UserModule.Roles.choices,
        default=UserModule.Roles.MEMBER,
        required=False
    )

    class Meta:
        model = UserModule
        fields = ['user_id', 'rol']

    def to_internal_value(self, data):
        # Permite aceptar tanto 'user_id' como 'user' en el payload JSON
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        if 'user' in data and 'user_id' not in data:
            data['user_id'] = data.pop('user')
        elif 'user' in data and 'user_id' in data:
            data.pop('user')
        return super().to_internal_value(data)
