from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .services import get_modules_list
from .serializers.modules import ModuleSerializer

class ModuleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modules = get_modules_list()
        serializer = ModuleSerializer(modules)
        return Response(serializer.data, status=status.HTTP_200_OK)


