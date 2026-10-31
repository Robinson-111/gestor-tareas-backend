from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import CustomPagination
from tasks.permissions import IsModuleMember
from tasks.serializers.task import (
    TaskCreateSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
)
from tasks.services import (
    create_task,
    delete_task,
    get_task,
    get_tasks_list,
    update_task,
)


class TaskListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsModuleMember]

    def get(self, request, id):
        try:
            tasks = get_tasks_list(
                module_id=id,
                user=request.user,
                state=request.query_params.get('estado'),
                search=request.query_params.get('search')
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        paginator = CustomPagination()
        paginated_tasks = paginator.paginate_queryset(tasks, request)
        serializer = TaskSerializer(paginated_tasks, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, id):
        serializer = TaskCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = create_task(
                module_id=id,
                user=request.user,
                validated_data=serializer.validated_data
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)

        response_serializer = TaskSerializer(task)
        return Response({
            "message": "Tarea creada exitosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated, IsModuleMember]

    def get(self, request, id, task_id):
        try:
            task = get_task(module_id=id, task_id=task_id, user=request.user)
        except PermissionError as e:
            return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Http404:
            return Response({
                "message": "La tarea no existe en este módulo."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = TaskSerializer(task)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, id, task_id):
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            task = update_task(
                module_id=id,
                task_id=task_id,
                user=request.user,
                validated_data=serializer.validated_data
            )
        except PermissionError as e:
            return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Http404:
            return Response({
                "message": "La tarea no existe en este módulo."
            }, status=status.HTTP_404_NOT_FOUND)

        response_serializer = TaskSerializer(task)
        return Response({
            "message": "Tarea actualizada exitosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_200_OK)

    def delete(self, request, id, task_id):
        try:
            delete_task(
                module_id=id,
                task_id=task_id,
                user=request.user
            )
        except PermissionError as e:
            return Response({"message": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Http404:
            return Response({
                "message": "La tarea no existe en este módulo."
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": "Tarea eliminada exitosamente."
        }, status=status.HTTP_200_OK)
