from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


# ---------------------------------------------------------------------------
# USUARIO
# ---------------------------------------------------------------------------
# IMPORTANTE: ya NO hereda de PermissionsMixin.
#
# El esquema oficial (devmatch_schema_v1.sql, provisto por el organizador)
# NO tiene columna is_superuser ni tablas de groups/user_permissions.
# PermissionsMixin las agrega automáticamente por debajo, y eso generaba
# una columna y dos tablas que no existen en la base de datos real,
# provocando fallos de migración. es_admin es el único rol persistente
# que pide la especificación (ver DevMatch-BD, 5.1) — no necesitamos el
# sistema de grupos/permisos granular de Django para esto.


class UsuarioManager(BaseUserManager):
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
        extra_fields.setdefault("es_admin", True)
        return self.create_user(email, username, password, **extra_fields)


class Usuario(AbstractBaseUser):
    """
    Tabla de autenticación (usuarios). Nunca se borra un usuario — el
    esquema oficial lo bloquea con un trigger BEFORE DELETE
    (trg_bloquear_borrado_usuarios). Cualquier "eliminación" debe ser
    es_activo=False.

    Nota: "Creador" y "Colaborador" NO son columnas de esta tabla. Son
    roles contextuales: Creador si aparece en proyectos.creador_id,
    Colaborador si tiene fila en equipos_membresias con estado='activo'.
    """

    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(max_length=150, unique=True)

    # Redeclarados para forzar el db_column exacto que exige el SQL oficial.
    password = models.CharField(max_length=128, db_column="password_hash")
    last_login = models.DateTimeField(
        db_column="ultimo_login", blank=True, null=True
    )

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    es_admin = models.BooleanField(default=False)  # único rol persistente
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
    actualizado_en = models.DateTimeField(auto_now=True)  # también hay trigger fn_set_updated_at

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "usuarios"

    def __str__(self):
        return self.email

    # --- Puentes manuales al sistema de auth/admin de Django -----------
    # Reemplazan lo que PermissionsMixin daba "gratis", sin agregar
    # columnas ni tablas que no existen en el esquema oficial.
    @property
    def is_staff(self):
        return self.es_admin

    @property
    def is_superuser(self):
        return self.es_admin

    @property
    def is_active(self):
        return self.es_activo and not self.esta_bloqueado

    def has_perm(self, perm, obj=None):
        return self.es_admin

    def has_module_perms(self, app_label):
        return self.es_admin


# ---------------------------------------------------------------------------
# PERFIL
# ---------------------------------------------------------------------------


class Perfil(models.Model):
    """Perfil técnico estructurado. Relación 1 a 1 con Usuario."""

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
    disponibilidad_horas_semana = models.PositiveSmallIntegerField(default=10)
    bio = models.TextField(blank=True, null=True)
    github_username = models.CharField(max_length=100, blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "perfiles"

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


# ---------------------------------------------------------------------------
# CATÁLOGOS (habilidades, tecnologías, intereses)
# ---------------------------------------------------------------------------
# Son los únicos, junto con las tablas puente, donde SÍ se permite un
# DELETE físico real (protegido solo por ON DELETE RESTRICT desde las
# tablas puente, sin trigger de bloqueo adicional).


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
    creado_en = models.DateTimeField(auto_now_add=True)

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
    # Interes NO tiene columna categoria en el SQL oficial.
    class Meta:
        db_table = "intereses"


# ---------------------------------------------------------------------------
# TABLAS PUENTE M2M
# ---------------------------------------------------------------------------
# El SQL oficial usa PK compuesta (usuario_id, catalogo_id) — SIN columna
# id autoincremental. Usamos CompositePrimaryKey (Django 5.2+) para que
# la tabla generada coincida exactamente, sin agregar un id de más que
# no existe en la base real.


class UsuarioHabilidad(models.Model):
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="usuario_id"
    )
    habilidad = models.ForeignKey(
        Habilidad, on_delete=models.RESTRICT, db_column="habilidad_id"
    )
    pk = models.CompositePrimaryKey("usuario_id", "habilidad_id")

    class Meta:
        db_table = "usuarios_habilidades"


class UsuarioTecnologia(models.Model):
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="usuario_id"
    )
    tecnologia = models.ForeignKey(
        Tecnologia, on_delete=models.RESTRICT, db_column="tecnologia_id"
    )
    pk = models.CompositePrimaryKey("usuario_id", "tecnologia_id")

    class Meta:
        db_table = "usuarios_tecnologias"


class UsuarioInteres(models.Model):
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="usuario_id"
    )
    interes = models.ForeignKey(
        Interes, on_delete=models.RESTRICT, db_column="interes_id"
    )
    pk = models.CompositePrimaryKey("usuario_id", "interes_id")

    class Meta:
        db_table = "usuarios_intereses"