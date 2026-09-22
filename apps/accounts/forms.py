from django import forms
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator

from .models import Usuario

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