from rest_framework import serializers
from account.models import User
import re

class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=False,
        error_messages={
            'required': "Debe confirmar la contraseña",
            'blank': "La confirmación de la contraseña no puede estar vacia"
        })

    class Meta:
        model = User
        fields = ('name', 'email', 'password', 'confirm_password')
        extra_kwargs = {
            'name': {
                'required': True,
                'allow_blank': False,
                'error_messages': {
                    'required': 'El nombre es obligatorio.',
                    'blank': 'El nombre no puede estar vacío.'
                }
            },
            'email': {
                'validators': [],
                'required': True,
                'allow_blank': False,
                'error_messages': {
                    'required': 'El correo electrónico es obligatorio.',
                    'blank': 'El correo electrónico no puede estar vacío.',
                    'invalid': 'Por favor, ingrese un correo electrónico valido'
                }
            },
            'password': {
                'write_only': True,
                'required': True,
                'allow_blank': False,
                'error_messages': {
                    'required': 'La contraseña es obligatoria.',
                    'blank': 'La contraseña no puede estar vacía.'
                }
            }
        }


    def validate_email(self, value):
        user_exist = User.objects.filter(email=value)

        if user_exist.exists():
            raise serializers.ValidationError("Ya existe un usuario con este email")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return value

    def validate(self, data):
        # 1. Validar que las contraseñas coincidan
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Las contraseñas no coinciden."})

        # 2. Impedir creación pública de roles administrativos
        requested_role = self.initial_data.get('rol')
        if requested_role and requested_role in [User.Roles.ADMIN, User.Roles.SUPER_ADMIN]:
            raise serializers.ValidationError({
                "rol": "No está permitido registrarse con roles administrativos."
            })
            
        return data

    def create(self, validated_data):
        from auth.services import register_user
        return register_user(validated_data)
