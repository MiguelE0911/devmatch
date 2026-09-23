from django import forms
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator

from .models import Habilidad, Interes, Perfil, Tecnologia, Usuario

# Estilo compartido de TODOS los inputs de las pantallas de auth
# (spec: fondo #F5F5F5, borde #7A7A7A, radio ~8px, alto ~56px,
# placeholder #959595, esquinas NO pill).
INPUT_CLASSES = (
    "h-14 w-full rounded-lg border border-[#7A7A7A]/60 bg-[#F5F5F5] "
    "px-4 text-sm text-slate-900 placeholder:text-[#959595] transition "
    "focus:border-violet-700 focus:outline-none focus:ring-2 focus:ring-violet-400/40"
)

# Username: letras (incl. acentos/ñ), números, guiones y puntos, de 3 a 30.
USERNAME_VALIDATOR = RegexValidator(
    regex=r"^[\w.-]{3,30}$",
    message="Solo letras, números y los símbolos _ . - (de 3 a 30 caracteres).",
)

# Mensaje de login genérico: no revela si el correo existe ni si la cuenta
# está desactivada/bloqueada (decisión de equipo).
ERROR_LOGIN = "Correo electrónico o contraseña incorrectos."

PASSWORD_INPUT_CLASSES = INPUT_CLASSES + " pr-14"  # espacio para el ojito


def _atributos(clases, placeholder, **extra):
    attrs = {"class": clases, "placeholder": placeholder}
    attrs.update(extra)
    return attrs


def _email_por_identificador(identificador):
    """Resuelve el email de la cuenta si `identificador` es un email o un
    username existente (insensible a mayúsculas). None si no existe."""
    if not identificador:
        return None
    identificador = identificador.strip()
    if "@" in identificador:
        return BaseUserManager.normalize_email(identificador)
    cuenta = Usuario.objects.filter(username__iexact=identificador).only("email").first()
    return cuenta.email if cuenta else None


class LoginForm(AuthenticationForm):
    """AuthenticationForm con los widgets estilizados de auth.

    Acepta como identificador el CORREO o el NOMBRE DE USUARIO de la
    cuenta. Resolution previa a que Django autentique por USERNAME_FIELD
    (email): si el texto trae "@" se trata como email; si no, se busca el
    username y se reemplaza por su email. Siempre mensaje de error genérico
    (no revela si la cuenta existe, está desactivada o bloqueada).
    """

    error_messages = {
        "invalid_login": ERROR_LOGIN,
        "inactive": ERROR_LOGIN,
    }

    username = forms.CharField(
        label="Correo electrónico o usuario",
        widget=forms.TextInput(
            attrs=_atributos(
                INPUT_CLASSES,
                "Correo electrónico o usuario",
                autocomplete="username",
                autocapitalize="none",
                autocorrect="off",
            )
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs=_atributos(
                PASSWORD_INPUT_CLASSES,
                "Contraseña",
                autocomplete="current-password",
            )
        ),
    )

    def clean(self):
        identificador = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if identificador and password:
            email = _email_por_identificador(identificador)
            if email:
                # El backend autentica por USERNAME_FIELD (email): pasamos el
                # email resuelto para que el flujo estándar siga intacto.
                self.cleaned_data["username"] = email
        return super().clean()


class RegistroForm(forms.ModelForm):
    """Formulario de alta de cuenta (solo datos de usuario, 6 campos).

    NO crea el Perfil técnico: se completa después en profile_form.
    El modelo guarda el password como CharField (columna password_hash),
    así que aquí se hashea explícitamente con set_password.

    Validaciones:
      - Username con formato restringido y sin duplicados (iexact).
      - Email real y sin duplicados (iexact).
      - Nombre y Apellido obligatorios.
      - Contraseñas iguales y que pasen los 4 validators de base.py.
    """

    username = forms.CharField(
        label="Nombre de usuario",
        validators=[USERNAME_VALIDATOR],
        help_text="Máximo 30 caracteres: letras, números y los símbolos _ . -",
        widget=forms.TextInput(
            attrs=_atributos(
                INPUT_CLASSES,
                "Nombre de usuario",
                autocomplete="username",
                autocapitalize="none",
            )
        ),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        help_text="Usá un correo válido (ej. nombre@dominio.com).",
        widget=forms.EmailInput(
            attrs=_atributos(
                INPUT_CLASSES,
                "Correo electrónico",
                autocomplete="email",
                autocapitalize="none",
            )
        ),
    )
    first_name = forms.CharField(
        label="Nombre",
        help_text="Tu nombre (ej. María).",
        widget=forms.TextInput(
            attrs=_atributos(
                INPUT_CLASSES,
                "Nombre",
                autocomplete="given-name",
            )
        ),
    )
    last_name = forms.CharField(
        label="Apellido",
        help_text="Tu apellido (ej. Gutiérrez).",
        widget=forms.TextInput(
            attrs=_atributos(
                INPUT_CLASSES,
                "Apellido",
                autocomplete="family-name",
            )
        ),
    )
    password1 = forms.CharField(
        label="Contraseña",
        help_text="Mínimo 8 caracteres: evitá tu usuario, correo o claves comunes.",
        widget=forms.PasswordInput(
            attrs=_atributos(
                PASSWORD_INPUT_CLASSES,
                "Contraseña",
                autocomplete="new-password",
                minlength="8",
            )
        ),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        help_text="Repite la misma contraseña.",
        widget=forms.PasswordInput(
            attrs=_atributos(
                PASSWORD_INPUT_CLASSES,
                "Confirmar contraseña",
                autocomplete="new-password",
                minlength="8",
            )
        ),
    )

    class Meta:
        model = Usuario
        fields = ("username", "email", "first_name", "last_name")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username and Usuario.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        email = BaseUserManager.normalize_email(email.strip())
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo electrónico.")
        self.cleaned_data["email"] = email
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden")

        # Usuario momentáneo para que UserAttributeSimilarityValidator
        # compare contra el email/username/nombre del formulario actual.
        usuario = Usuario(
            username=self.cleaned_data.get("username"),
            email=self.cleaned_data.get("email"),
            first_name=self.cleaned_data.get("first_name"),
            last_name=self.cleaned_data.get("last_name"),
        )
        validate_password(password2, user=usuario)
        return password2

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


# ---------------------------------------------------------------------------
# PERFIL TÉCNICO (edición) — forms.py se mantiene como única fuente de estilos
# de inputs (ver DEVMATCH-DESIGN: no inventar colores). Fondo #F5F5F5 y borde
# #6B7280 reutilizan el patrón de INPUT_CLASSES de las pantallas de auth.
# ---------------------------------------------------------------------------
PROFILE_INPUT_CLASSES = (
    "h-11 w-full rounded-[10px] border border-gray-500 bg-[#F5F5F5] "
    "px-3.5 text-sm text-slate-900 placeholder:text-[#959595] transition "
    "focus:border-violet-700 focus:bg-[#E9E5FC] focus:outline-none "
    "focus:ring-2 focus:ring-violet-400/40"
)


def _perfil_atributos(clases, placeholder, **extra):
    attrs = {"class": clases, "placeholder": placeholder}
    attrs.update(extra)
    return attrs


class ProfileEditForm(forms.ModelForm):
    """Perfil técnico editable. Combina datos de la cuenta (Usuario) y del
    perfil (Perfil) en un solo form, tal como consume la vista de edición.

    - Usuario: nombre, apellido y username se editan directamente; el correo
      se muestra solo-lectura (es la llave de autenticación, no se cambia).
    - Perfil: nivel, años de experiencia, disponibilidad y biografía.
    - skills: se pasan como listas de PKs en `habilidades`, `tecnologias` e
      `intereses`; la vista sincroniza las tablas puente desde cleaned_data.
    """

    username = forms.CharField(
        label="Nombre de usuario",
        validators=[USERNAME_VALIDATOR],
        widget=forms.TextInput(
            attrs=_perfil_atributos(
                PROFILE_INPUT_CLASSES,
                "Nombre de usuario",
                autocomplete="username",
                autocapitalize="none",
            )
        ),
    )
    first_name = forms.CharField(
        label="Nombre",
        required=False,
        widget=forms.TextInput(
            attrs=_perfil_atributos(
                PROFILE_INPUT_CLASSES, "Nombre", autocomplete="given-name"
            )
        ),
    )
    last_name = forms.CharField(
        label="Apellido",
        required=False,
        widget=forms.TextInput(
            attrs=_perfil_atributos(
                PROFILE_INPUT_CLASSES, "Apellido", autocomplete="family-name"
            )
        ),
    )
    # Correo solo-lectura: no se envía (disabled), solo se muestra destacado.
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": (
                    "h-11 w-full rounded-[10px] border border-violet-700 "
                    "bg-[#E9E5FC] px-3.5 text-sm text-slate-900 opacity-90"
                ),
                "readonly": True,
            }
        ),
    )
    nivel = forms.ChoiceField(
        label="Nivel técnico",
        choices=Perfil.NIVEL_CHOICES,
        widget=forms.Select(
            attrs=_perfil_atributos(PROFILE_INPUT_CLASSES, "Nivel técnico")
        ),
    )
    experiencia_anios = forms.IntegerField(
        label="Años de experiencia",
        min_value=0,
        widget=forms.NumberInput(
            attrs=_perfil_atributos(
                PROFILE_INPUT_CLASSES, "Años de experiencia"
            )
        ),
    )
    disponibilidad_horas_semana = forms.IntegerField(
        label="Disponibilidad",
        min_value=0,
        help_text="Horas por semana",
        widget=forms.NumberInput(
            attrs=_perfil_atributos(
                PROFILE_INPUT_CLASSES, "Horas por semana"
            )
        ),
    )
    bio = forms.CharField(
        label="Biografía",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": (
                    "min-h-28 w-full rounded-[16px] border border-gray-500 "
                    "bg-[#F5F5F5] px-3.5 py-3 text-sm text-slate-900 "
                    "placeholder:text-[#959595] transition resize-none "
                    "focus:border-violet-700 focus:bg-[#E9E5FC] "
                    "focus:outline-none focus:ring-2 focus:ring-violet-400/40"
                ),
                "placeholder": "Contanos en qué trabajás, tu enfoque y lo que te apasiona…",
                "rows": 4,
            }
        ),
    )
    habilidades = forms.ModelMultipleChoiceField(
        queryset=Habilidad.objects.filter(es_activo=True).order_by("nombre"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    tecnologias = forms.ModelMultipleChoiceField(
        queryset=Tecnologia.objects.filter(es_activo=True).order_by("nombre"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    intereses = forms.ModelMultipleChoiceField(
        queryset=Interes.objects.filter(es_activo=True).order_by("nombre"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Perfil
        fields = (
            "nivel",
            "experiencia_anios",
            "disponibilidad_horas_semana",
            "bio",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.usuario_id:
            usuario = self.instance.usuario
            self.fields["username"].initial = usuario.username
            self.fields["first_name"].initial = usuario.first_name
            self.fields["last_name"].initial = usuario.last_name
            self.fields["email"].initial = usuario.email
            self.initial["habilidades"] = list(
                usuario.usuariohabilidad_set.values_list("habilidad_id", flat=True)
            )
            self.initial["tecnologias"] = list(
                usuario.usuariotecnologia_set.values_list("tecnologia_id", flat=True)
            )
            self.initial["intereses"] = list(
                usuario.usuariointeres_set.values_list("interes_id", flat=True)
            )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        duplicado = (
            Usuario.objects.filter(username__iexact=username)
            .exclude(pk=self.instance.usuario_id)
            .exists()
        )
        if duplicado:
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def save(self, commit=True):
        # El form edita datos de Usuario y de Perfil a la vez: el ModelForm
        # base solo guarda Perfil (instance), así que persistimos también los
        # cambios sobre la cuenta (manteniendo el correo, que es solo lectura).
        perfil = super().save(commit=commit)
        if commit and perfil.usuario_id:
            usuario = perfil.usuario
            usuario.username = self.cleaned_data["username"]
            usuario.first_name = self.cleaned_data["first_name"]
            usuario.last_name = self.cleaned_data["last_name"]
            usuario.save(update_fields=["username", "first_name", "last_name"])
        return perfil