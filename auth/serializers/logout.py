from rest_framework import serializers


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El token de actualización (refresh) es obligatorio.',
            'blank': 'El token de actualización no puede estar vacío.'
        }
    )

