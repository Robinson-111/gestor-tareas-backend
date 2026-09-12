from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            'required': 'El token de actualización (refresh) es obligatorio.',
            'blank': 'El token de actualización no puede estar vacío.'
        }
    )

    def validate(self, attrs):
        refresh_token = attrs.get('refresh')
        try:
            self.token_instance = RefreshToken(refresh_token)
        except TokenError:
            raise serializers.ValidationError({
                'refresh': 'El token es inválido o ha expirado.'
            })
        return attrs

    def save(self, **kwargs):
        try:
            self.token_instance.blacklist()
        except TokenError:
            raise serializers.ValidationError({
                'refresh': 'El token es inválido o ha expirado.'
            })
