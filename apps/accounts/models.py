from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ---------------------------------------------------------------------------
# USUARIO
# ---------------------------------------------------------------------------
# Se usa AbstractBaseUser + PermissionsMixin (en vez de AbstractUser) porque
# necesitamos que los nombres de columna coincidan exactamente con el
# diccionario de datos de DevMatch-BD (es_admin, es_activo, esta_bloqueado...),
# y AbstractUser trae de fábrica columnas con otros nombres (is_active, etc.)
# que tocaría remapear de todos modos.


class UsuarioManager(BaseUserManager):
    """Manager custom porque no usamos AbstractUser (sin username/email de fábrica)."""

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un email")
        if not username:
            raise ValueError("El usuario debe tener un username")
        email = self.normalize_email(email)
        usuario = self.model(email=email, username=username, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, username, password=None, **extra_fields):
        # es_admin es nuestro único "rol persistente" (ver nota en el modelo).
        extra_fields.setdefault("es_admin", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, username, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Tabla de autenticación (usuarios). Nunca se borra un usuario (Sección 6.5
    del documento de BD) — cualquier "eliminación" debe ser es_activo=False.

    Nota importante (ver DevMatch-BD, sección 5.1): "Creador" y "Colaborador"
    NO son columnas de esta tabla. Son roles contextuales:
      - Creador de un proyecto  -> aparece como proyectos.creador_id
      - Colaborador             -> tiene fila en equipos_membresias (activo)
    Ese cruce se implementará en la app `projects`/`teams`, no aquí.
    """

    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(max_length=150, unique=True)

    # Redeclarados para forzar el db_column exacto que pide la BD.
    password = models.CharField(max_length=128, db_column="password_hash")
    last_login = models.DateTimeField(
        db_column="ultimo_login", blank=True, null=True
    )

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # Único rol persistente (ver docstring de la clase).
    es_admin = models.BooleanField(default=False)

    es_activo = models.BooleanField(default=True)  # cuenta oculta/desactivada

    esta_bloqueado = models.BooleanField(default=False)  # acción punitiva/moderación
    motivo_bloqueo = models.TextField(blank=True, null=True)
    bloqueado_en = models.DateTimeField(blank=True, null=True)
    bloqueado_por = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios_bloqueados",
        db_column="bloqueado_por_id",
    )

    desactivado_en = models.DateTimeField(blank=True, null=True)
    desactivado_por = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios_desactivados",
        db_column="desactivado_por_id",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    # actualizado_en también existe como trigger (fn_set_updated_at) en la BD.
    # Se deja auto_now=True aquí; es redundante con el trigger pero no genera
    # conflicto (ver Sección 6.1 del documento de BD).
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "usuarios"

    def __str__(self):
        return self.email

    # --- Puentes hacia el sistema de permisos/admin de Django ---------
    # is_staff/is_active no existen como columnas propias en la BD; se
    # calculan a partir de las columnas reales para no duplicar información.
    @property
    def is_staff(self):
        return self.es_admin

    @property
    def is_active(self):
        return self.es_activo and not self.esta_bloqueado


# ---------------------------------------------------------------------------
# PERFIL
# ---------------------------------------------------------------------------


class Perfil(models.Model):
    """Perfil técnico estructurado. Relación 1 a 1 con Usuario. Sin es_activo
    propio: no existe una acción de "eliminar perfil" independiente de la
    cuenta (ver DevMatch-BD, 5.1)."""

    NIVEL_PRINCIPIANTE = "principiante"
    NIVEL_INTERMEDIO = "intermedio"
    NIVEL_AVANZADO = "avanzado"
    NIVEL_CHOICES = [
        (NIVEL_PRINCIPIANTE, "Principiante"),
        (NIVEL_INTERMEDIO, "Intermedio"),
        (NIVEL_AVANZADO, "Avanzado"),
    ]

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name="perfil",
        db_column="usuario_id",
    )
    nivel = models.CharField(
        max_length=20, choices=NIVEL_CHOICES, default=NIVEL_PRINCIPIANTE
    )
    experiencia_anios = models.PositiveSmallIntegerField(default=0)
    # Numérico, no etiqueta: permite calcular sobrecarga real comparando
    # contra compromisos activos (ver DevMatch-BD, 5.1).
    disponibilidad_horas_semana = models.PositiveSmallIntegerField(default=10)
    bio = models.TextField(blank=True, null=True)
    github_username = models.CharField(max_length=100, blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "perfiles"

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


# ---------------------------------------------------------------------------
# CATÁLOGOS (habilidades, tecnologías, intereses)
# ---------------------------------------------------------------------------
# Estos tres son los únicos, junto con las tablas puente, donde SÍ se permite
# un DELETE físico real en la BD (protegido por ON DELETE RESTRICT desde las
# tablas puente) — por eso no llevan el mismo bloqueo de borrado que
# proyectos/usuarios/etc.


class CatalogoBase(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    es_activo = models.BooleanField(default=True)
    desactivado_en = models.DateTimeField(blank=True, null=True)
    desactivado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="desactivado_por_id",
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.nombre


class Habilidad(CatalogoBase):
    categoria = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "habilidades"


class Tecnologia(CatalogoBase):
    categoria = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "tecnologias"


class Interes(CatalogoBase):
    # Interes NO tiene columna categoria (ver DevMatch-BD, 5.1).
    class Meta:
        db_table = "intereses"


# ---------------------------------------------------------------------------
# TABLAS PUENTE M2M
# ---------------------------------------------------------------------------
# Puras, sin es_activo y sin protección de borrado: agregar/quitar una
# etiqueta del perfil es edición normal, no un evento de historial.
# La BD usa PK compuesta (usuario_id, catalogo_id) para evitar duplicados;
# Django no soporta PK compuesta de forma nativa, así que replicamos la
# garantía con una UniqueConstraint.


class UsuarioHabilidad(models.Model):
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="usuario_id"
    )
    habilidad = models.ForeignKey(
        Habilidad, on_delete=models.RESTRICT, db_column="habilidad_id"
    )

    class Meta:
        db_table = "usuarios_habilidades"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "habilidad"], name="uq_usuario_habilidad"
            )
        ]


class UsuarioTecnologia(models.Model):
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="usuario_id"
    )
    tecnologia = models.ForeignKey(
        Tecnologia, on_delete=models.RESTRICT, db_column="tecnologia_id"
    )

    class Meta:
        db_table = "usuarios_tecnologias"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "tecnologia"], name="uq_usuario_tecnologia"
            )
        ]


class UsuarioInteres(models.Model): 
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="usuario_id"
    )
    interes = models.ForeignKey(
        Interes, on_delete=models.RESTRICT, db_column="interes_id"
    )

    class Meta:
        db_table = "usuarios_intereses"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "interes"], name="uq_usuario_interes"
            )
        ]