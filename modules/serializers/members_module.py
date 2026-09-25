from rest_framework import serializers
from modules.models import UserModule
from core.serializer import StrictModelSerializer

class MemberModuleSerializer(StrictModelSerializer):

    name = serializers.CharField(source='user.name', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = UserModule
        fields = ['id', 'user_id', 'name', 'rol']
        read_only_fields = ['id', 'user_id', 'name', 'rol']