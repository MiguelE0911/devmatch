from django import forms
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


class UsuarioCreationForm(forms.ModelForm):
    # Formulario para la página de "Añadir usuario" del admin. El modelo
    # declara password como CharField (db_column password_hash), así que el
    # ModelForm por defecto no hashea nada; este form lo hace con set_password
    # y expone password1/password2 como campos con PasswordInput.
    password1 = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Confirmar contraseña", widget=forms.PasswordInput
    )

    class Meta:
        model = Usuario
        fields = ("email", "username", "first_name", "last_name")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden")
        return password2

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    # Ya NO hereda de DjangoUserAdmin: esa clase asume campos que
    # Usuario no tiene (groups, user_permissions, is_superuser como
    # campo real) porque el modelo no usa PermissionsMixin, para
    # coincidir exactamente con el esquema oficial (sin esas tablas).
    model = Usuario
    add_form = UsuarioCreationForm
    ordering = ("email",)

    # add_form/add_fieldsets no los usa el ModelAdmin base por sí solo
    # (son parte de UserAdmin); se replican aquí los dos hooks mínimos.
    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)
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
    readonly_fields = ("creado_en", "actualizado_en", "last_login", "password")

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
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
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