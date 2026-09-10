# auth/serializers/login.py
from rest_framework import serializers
from django.contrib.auth import authenticate

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'blank': 'El correo electrónico no puede estar vacío.',
            'invalid': 'Por favor, ingrese un correo electrónico válido.'
        }
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.'
        }
    )

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        user = authenticate(username=email, password=password)

        if not user:
            raise serializers.ValidationError("Correo o contraseña incorrectos.")

        data['user'] = user  # Guardamos el usuario autenticado
        return data
