from rest_framework import serializers
from core.serializer import StrictModelSerializer
from modules.models import UserModule

class EditMemberModuleSerializer(StrictModelSerializer):
    class Meta:
        model = UserModule
        fields = ['user_id', 'rol']