from django.contrib import admin

from .models import Habilidad, Interes, Perfil, Tecnologia, Usuario

# NOTA: UsuarioHabilidad, UsuarioTecnologia y UsuarioInteres NO se
# registran aquí. Django no permite registrar en el admin un modelo con
# clave primaria compuesta (CompositePrimaryKey) — el panel de admin
# necesita un solo campo pk simple para construir las URLs de edición.
# Esto es intencional: esos tres modelos coinciden con el esquema
# oficial (PK compuesta usuario_id + catalogo_id, sin columna id). Si
# el Integrador necesita cargar/ver estos datos, usar
# loaddata/dumpdata o un comando de fixtures (seed_data), no el admin.


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    # Ya NO hereda de DjangoUserAdmin: esa clase asume campos que
    # Usuario no tiene (groups, user_permissions, is_superuser como
    # campo real) porque el modelo no usa PermissionsMixin, para
    # coincidir exactamente con el esquema oficial (sin esas tablas).
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