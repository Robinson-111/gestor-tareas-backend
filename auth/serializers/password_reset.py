from rest_framework import serializers


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'blank': 'El correo electrónico no puede estar vacío.',
            'invalid': 'Por favor, ingrese un correo electrónico válido.',
        },
    )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El identificador de recuperación es obligatorio.',
            'blank': 'El identificador de recuperación no puede estar vacío.',
        },
    )
    token = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El token de recuperación es obligatorio.',
            'blank': 'El token de recuperación no puede estar vacío.',
        },
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'La nueva contraseña es obligatoria.',
            'blank': 'La nueva contraseña no puede estar vacía.',
        },
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'Debe confirmar la nueva contraseña.',
            'blank': 'La confirmación de la contraseña no puede estar vacía.',
        },
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': ['Las contraseñas no coinciden.'],
            })
        return attrs
