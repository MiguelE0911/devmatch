from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# PROYECTO
# ---------------------------------------------------------------------------


class Proyecto(models.Model):
    """
    Tabla `proyectos`. Nunca se borra un proyecto — el esquema oficial lo
    bloquea con un trigger BEFORE DELETE (trg_bloquear_borrado_proyectos).
    Cualquier "eliminación" debe ser es_activo=False.
    """

    ESTADO_BORRADOR = "borrador"
    ESTADO_PUBLICADO = "publicado"
    ESTADO_RECLUTANDO = "reclutando"
    ESTADO_EQUIPO_COMPLETO = "equipo_completo"
    ESTADO_EN_DESARROLLO = "en_desarrollo"
    ESTADO_FINALIZADO = "finalizado"
    ESTADO_CANCELADO = "cancelado"
    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, "Borrador"),
        (ESTADO_PUBLICADO, "Publicado"),
        (ESTADO_RECLUTANDO, "Reclutando"),
        (ESTADO_EQUIPO_COMPLETO, "Equipo completo"),
        (ESTADO_EN_DESARROLLO, "En desarrollo"),
        (ESTADO_FINALIZADO, "Finalizado"),
        (ESTADO_CANCELADO, "Cancelado"),
    ]

    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="proyectos_creados",
        db_column="creador_id",
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=ESTADO_BORRADOR
    )
    es_activo = models.BooleanField(default=True)
    logo_url = models.TextField(blank=True, null=True)

    finalizado_en = models.DateTimeField(blank=True, null=True)
    cancelado_en = models.DateTimeField(blank=True, null=True)

    desactivado_en = models.DateTimeField(blank=True, null=True)
    desactivado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="desactivado_por_id",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)  # también hay trigger fn_set_updated_at

    class Meta:
        db_table = "proyectos"

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# VACANTE
# ---------------------------------------------------------------------------


class Vacante(models.Model):
    """
    Tabla `vacantes`. `cupos_ocupados` y, en consecuencia, `estado`
    ('cubierta'/'abierta') los mantiene automáticamente el trigger
    trg_membresia_actualiza_cupos al aceptar/retirar miembros del equipo
    (ver DevMatch-BD, 6.2) — no se deben escribir a mano desde la app.
    """

    ESTADO_ABIERTA = "abierta"
    ESTADO_CUBIERTA = "cubierta"
    ESTADO_CANCELADA = "cancelada"
    ESTADO_CHOICES = [
        (ESTADO_ABIERTA, "Abierta"),
        (ESTADO_CUBIERTA, "Cubierta"),
        (ESTADO_CANCELADA, "Cancelada"),
    ]

    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="vacantes",
        db_column="proyecto_id",
    )
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField()
    cupos_totales = models.PositiveSmallIntegerField()
    cupos_ocupados = models.PositiveSmallIntegerField(default=0)
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default=ESTADO_ABIERTA
    )
    es_activo = models.BooleanField(default=True)

    desactivado_en = models.DateTimeField(blank=True, null=True)
    desactivado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="desactivado_por_id",
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)  # también hay trigger fn_set_updated_at

    class Meta:
        db_table = "vacantes"

    def __str__(self):
        return f"{self.titulo} ({self.proyecto.nombre})"


# ---------------------------------------------------------------------------
# PROYECTO MEDIA
# ---------------------------------------------------------------------------


class ProyectoMedia(models.Model):
    """
    Tabla `proyecto_media`: logos y prototipos (procesados con Pillow más
    adelante). A diferencia de proyectos/vacantes, es un adjunto y no un
    registro crítico de negocio: no tiene actualizado_en ni
    desactivado_por_id (ver DevMatch-BD, 5.2).
    """

    TIPO_LOGO = "logo"
    TIPO_PROTOTIPO = "prototipo"
    TIPO_CHOICES = [
        (TIPO_LOGO, "Logo"),
        (TIPO_PROTOTIPO, "Prototipo"),
    ]

    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.CASCADE,
        related_name="media",
        db_column="proyecto_id",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    archivo_url = models.TextField()
    orden = models.PositiveSmallIntegerField(default=0)
    es_activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "proyecto_media"

    def __str__(self):
        return f"{self.tipo} de {self.proyecto.nombre}"


# ---------------------------------------------------------------------------
# TABLAS PUENTE M2M — requisitos de la vacante
# ---------------------------------------------------------------------------
# El SQL oficial usa PK compuesta (vacante_id, catalogo_id) — SIN columna
# id autoincremental. Mismo patrón que usó Wilma en accounts (usuarios_*).
# Lo que se defina aquí es la lista ACTUAL de requisitos; lo que se usó en
# cada postulación queda congelado aparte en postulaciones.match_factores
# (Etapa 2, ver DevMatch-BD 5.2).


class VacanteHabilidadRequerida(models.Model):
    vacante = models.ForeignKey(
        Vacante, on_delete=models.CASCADE, db_column="vacante_id"
    )
    habilidad = models.ForeignKey(
        "accounts.Habilidad", on_delete=models.RESTRICT, db_column="habilidad_id"
    )
    pk = models.CompositePrimaryKey("vacante_id", "habilidad_id")

    class Meta:
        db_table = "vacante_habilidades_requeridas"


class VacanteTecnologiaRequerida(models.Model):
    vacante = models.ForeignKey(
        Vacante, on_delete=models.CASCADE, db_column="vacante_id"
    )
    tecnologia = models.ForeignKey(
        "accounts.Tecnologia", on_delete=models.RESTRICT, db_column="tecnologia_id"
    )
    pk = models.CompositePrimaryKey("vacante_id", "tecnologia_id")

    class Meta:
        db_table = "vacante_tecnologias_requeridas"
