from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'name', 'rol', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('email', 'name')
    ordering = ('email',)

    readonly_fields = ('password', 'last_login', 'created_at', 'updated_at',
                       'is_staff', 'is_superuser')
    fields = ('email', 'name', 'rol', 'is_active', 'is_staff', 'is_superuser',
              'password', 'last_login', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        # Los usuarios se crean por la API o por createsuperuser
        return False