from rest_framework import serializers

class StrictModelSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        allowed = set(self.fields.keys())
        extra = set(data.keys()) - allowed
        if extra:
            raise serializers.ValidationError({
                field: "Este campo no está permitido"
                for field in extra
            })
        return super().to_internal_value(data)