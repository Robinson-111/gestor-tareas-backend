from django.core.management.base import BaseCommand
from account.models import User


class Command(BaseCommand):
    help = 'Crea un usuario SUPER_ADMIN'

    def handle(self, *args, **options):

        name = input('Nombre: ')
        email = input('Email: ')
        password = input('Contraseña: ')

        user = User.objects.create_superuser(
            email=email,
            name=name,
            password=password
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'SUPER_ADMIN creado correctamente: {user.email}'
            )
        )