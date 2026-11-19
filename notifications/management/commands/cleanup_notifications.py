from django.core.management.base import BaseCommand

from notifications.services import cleanup_read_notifications


class Command(BaseCommand):
    help = (
        'Elimina notificaciones leídas con más de N días de antigüedad. '
        'Por defecto: 3 días.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help=(
                'Eliminar notificaciones leídas con más de este número de '
                'días. Por defecto: 3.'
            ),
        )

    def handle(self, *args, **options):
        days = options.get('days', 3)
        deleted = cleanup_read_notifications(days=days)
        self.stdout.write(
            self.style.SUCCESS(
                f'Notificaciones leídas con más de {days} días eliminadas: {deleted}'
            )
        )
