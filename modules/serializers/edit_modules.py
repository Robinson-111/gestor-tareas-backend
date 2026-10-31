from core.serializer import StrictModelSerializer
from modules.models import Module


class EditModuleSerializer(StrictModelSerializer):
    class Meta:
        model = Module
        fields = ['name', 'description', 'state']
