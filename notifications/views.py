from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import CustomPagination
from notifications.serializers import NotificationSerializer
from notifications.services import (
    delete_all_notifications,
    delete_notification,
    get_notifications,
    mark_all_read,
    mark_read,
    unread_count,
)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_param = request.query_params.get('unread')
        unread = None

        if unread_param is not None:
            unread = unread_param.lower() in ('true', '1', 'yes')

        queryset = get_notifications(request.user, unread=unread)

        paginator = CustomPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)
        response.data['unread_count'] = unread_count(request.user)

        return response


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'unread_count': unread_count(request.user)})


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        notification = mark_read(request.user, id)

        return Response({
            'message': 'Notificación marcada como leída.',
            'data': NotificationSerializer(notification).data,
        })


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = mark_all_read(request.user)

        return Response({
            'message': 'Notificaciones marcadas como leídas.',
            'updated': updated,
        })


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        notification = delete_notification(request.user, id)

        return Response({
            'message': 'Notificación eliminada.',
            'id': notification.id,
        })


class NotificationDeleteAllView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted = delete_all_notifications(request.user)

        return Response({
            'message': 'Notificaciones eliminadas.',
            'deleted': deleted,
        })
