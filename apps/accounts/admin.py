from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    Habilidad,
    Interes,
    Perfil,
    Tecnologia,
    Usuario,
    UsuarioHabilidad,
    UsuarioInteres,
    UsuarioTecnologia,
)


@admin.register(Usuario)
class UsuarioAdmin(DjangoUserAdmin):
    # No heredamos los fieldsets de DjangoUserAdmin tal cual porque referencian
    # campos que no existen aquí (is_active, is_staff como campos reales).
    model = Usuario
    ordering = ("email",)
    list_display = (
        "email",
        "username",
        "es_admin",
        "es_activo",
        "esta_bloqueado",
        "creado_en",
    )
    list_filter = ("es_admin", "es_activo", "esta_bloqueado")
    search_fields = ("email", "username", "first_name", "last_name")
    readonly_fields = ("creado_en", "actualizado_en", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name")}),
        (
            "Estado y rol",
            {
                "fields": (
                    "es_admin",
                    "es_activo",
                    "esta_bloqueado",
                    "motivo_bloqueo",
                    "bloqueado_en",
                    "bloqueado_por",
                )
            },
        ),
        (
            "Baja de cuenta",
            {"fields": ("desactivado_en", "desactivado_por")},
        ),
        (
            "Fechas",
            {"fields": ("last_login", "creado_en", "actualizado_en")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "fields": ("email", "username", "password1", "password2"),
            },
        ),
    )


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "nivel",
        "experiencia_anios",
        "disponibilidad_horas_semana",
        "github_username",
    )
    list_filter = ("nivel",)
    search_fields = ("usuario__email", "usuario__username", "github_username")


class CatalogoAdminBase(admin.ModelAdmin):
    list_display = ("nombre", "es_activo")
    list_filter = ("es_activo",)
    search_fields = ("nombre",)


@admin.register(Habilidad)
class HabilidadAdmin(CatalogoAdminBase):
    list_display = ("nombre", "categoria", "es_activo")
    list_filter = ("es_activo", "categoria")


@admin.register(Tecnologia)
class TecnologiaAdmin(CatalogoAdminBase):
    list_display = ("nombre", "categoria", "es_activo")
    list_filter = ("es_activo", "categoria")


@admin.register(Interes)
class InteresAdmin(CatalogoAdminBase):
    pass


@admin.register(UsuarioHabilidad)
class UsuarioHabilidadAdmin(admin.ModelAdmin):
    list_display = ("usuario", "habilidad")
    search_fields = ("usuario__email", "habilidad__nombre")


@admin.register(UsuarioTecnologia)
class UsuarioTecnologiaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tecnologia")
    search_fields = ("usuario__email", "tecnologia__nombre") 


@admin.register(UsuarioInteres)
class UsuarioInteresAdmin(admin.ModelAdmin):
    list_display = ("usuario", "interes")
    search_fields = ("usuario__email", "interes__nombre") 