from datetime import timedelta
from decimal import Decimal

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# Contraseña de demo para TODOS los usuarios generados. Es para que Squad B
# pueda loguearse en el frontend de prueba; no es un secreto de producción.
DEMO_PASSWORD = "Devmatch2026!"


class Command(BaseCommand):
    """
    python manage.py seed_data

    Genera datos de prueba (fixtures) para que Squad B pueda maquetar y
    demos de etapa (rol del Integrador, ver DEVMATCH-DISTRIBUCION.md).

    Es IDEMPOTENTE: se puede correr varias veces sin duplicar filas
    (get_or_create por email / creador+nombre). NO usa borrados físicos,
    respetando los triggers de bloqueo del esquema oficial.

    Fechas escalonadas: los datos demo se fechan relativos a "ahora" con
    `_hace_dias(n)`, para que los listados ordenados por fecha (galería,
    dashboard, "recientes" del perfil) tengan un orden verificable a simple
    vista. Los campos auto_now_add (creado_en, postulado_en, ingreso_en)
    ignoran el valor que se pasa a create(), así que se corrigen SIEMPRE con
    un UPDATE posterior al get_or_create, tanto si la fila es nueva como si ya
    existía. Cada corrida vuelve a fijar los mismos desfases relativos.
    """

    help = "Genera datos de prueba (fixtures) para Squad B."

    @transaction.atomic
    def handle(self, *args, **options):
        # Todo o nada: si un trigger rechaza algo, la corrida no queda a medias.
        self.stdout.write(self.style.NOTICE("== DevMatch: seed_data =="))
        self.seed_usuarios()
        self.seed_proyectos()
        self.seed_interacciones()
        self.stdout.write(self.style.SUCCESS("Datos de prueba generados correctamente."))

    @staticmethod
    def _model(app_label, model_name):
        return django_apps.get_model(app_label, model_name)

    @staticmethod
    def _catalogo(Modelo, nombre):
        """Trae o crea una fila de catálogo (habilidades/tecnologías/intereses)."""
        return Modelo.objects.get_or_create(nombre=nombre)[0]

    @staticmethod
    def _username_libre(Usuario, base):
        candidato = base
        contador = 2
        while Usuario.objects.filter(username=candidato).exists():
            candidato = f"{base}-{contador}"
            contador += 1
        return candidato

    @staticmethod
    def _hace_dias(n):
        """Momento de hace `n` días (puede ser fraccionario: 2.9 = 2 d 14 h)."""
        return timezone.now() - timedelta(days=n)

    @staticmethod
    def _fijar(Modelo, pk, **campos):
        """
        Corrige fechas auto_now_add con un UPDATE posterior al INSERT. No toca
        `estado`, así que no dispara los triggers de transición ni de cupos.
        """
        Modelo.objects.filter(pk=pk).update(**campos)

    # ------------------------------------------------------------------
    # USUARIOS Y PERFILES
    # ------------------------------------------------------------------

    def seed_usuarios(self):
        Usuario = self._model("accounts", "Usuario")
        Perfil = self._model("accounts", "Perfil")
        Habilidad = self._model("accounts", "Habilidad")
        Tecnologia = self._model("accounts", "Tecnologia")
        Interes = self._model("accounts", "Interes")
        UsuarioHabilidad = self._model("accounts", "UsuarioHabilidad")
        UsuarioTecnologia = self._model("accounts", "UsuarioTecnologia")
        UsuarioInteres = self._model("accounts", "UsuarioInteres")

        usuarios = [
            {
                "email": "admin@devmatch.local",
                "username": "admin",
                "creado_hace": 120,
                "first_name": "Aura",
                "last_name": "López",
                "es_admin": True,
                "perfil": {
                    "nivel": "avanzado",
                    "experiencia_anios": 8,
                    "disponibilidad_horas_semana": 20,
                    "bio": "Administradora de la plataforma DevMatch.",
                    "github_username": "aura-dev",
                },
                "habilidades": ["Project Management", "Database Design", "DevOps"],
                "tecnologias": ["Python", "Django", "PostgreSQL"],
                "intereses": ["Open Source", "Comunidades técnicas"],
            },
            {
                "email": "maria@devmatch.local",
                "username": "maria",
                "creado_hace": 110,
                "first_name": "María",
                "last_name": "Gutiérrez",
                "es_admin": False,
                "perfil": {
                    "nivel": "avanzado",
                    "experiencia_anios": 6,
                    "disponibilidad_horas_semana": 30,
                    "bio": "Backend y bases de datos. Me gusta construir productos útiles.",
                    "github_username": "maria-gutierrez",
                },
                "habilidades": ["Backend Development", "Database Design", "DevOps"],
                "tecnologias": ["Python", "Django", "PostgreSQL", "Docker"],
                "intereses": ["Machine Learning", "Open Source"],
            },
            {
                "email": "juan@devmatch.local",
                "username": "juan",
                "creado_hace": 105,
                "first_name": "Juan",
                "last_name": "Pérez",
                "es_admin": False,
                "perfil": {
                    "nivel": "intermedio",
                    "experiencia_anios": 4,
                    "disponibilidad_horas_semana": 25,
                    "bio": "Frontend enfocado en interfaces limpias y accesibles.",
                    "github_username": "juan-perez",
                },
                "habilidades": ["Frontend Development", "UI/UX Design", "QA / Testing"],
                "tecnologias": ["JavaScript", "React", "Tailwind CSS", "Figma"],
                "intereses": ["Accesibilidad", "Open Source"],
            },
            {
                "email": "carlos@devmatch.local",
                "username": "carlos",
                "creado_hace": 95,
                "first_name": "Carlos",
                "last_name": "Mendoza",
                "es_admin": False,
                "perfil": {
                    "nivel": "principiante",
                    "experiencia_anios": 1,
                    "disponibilidad_horas_semana": 15,
                    "bio": "Arranco en el mundo del desarrollo, buscando mi primer equipo.",
                    "github_username": "carlos-mendoza",
                },
                "habilidades": ["Frontend Development", "QA / Testing"],
                "tecnologias": ["JavaScript", "Tailwind CSS"],
                "intereses": ["Gaming", "Comunidades técnicas"],
            },
            {
                "email": "ana@devmatch.local",
                "username": "ana",
                "creado_hace": 100,
                "first_name": "Ana",
                "last_name": "Ríos",
                "es_admin": False,
                "perfil": {
                    "nivel": "intermedio",
                    "experiencia_anios": 3,
                    "disponibilidad_horas_semana": 20,
                    "bio": "Data science con ganas de aplicar análisis en proyectos reales.",
                    "github_username": "ana-rios",
                },
                "habilidades": ["Data Science", "Database Design"],
                "tecnologias": ["Python", "PostgreSQL"],
                "intereses": ["Machine Learning", "Datos abiertos"],
            },
        ]

        for datos in usuarios:
            usuario = Usuario.objects.filter(email=datos["email"]).first()
            if usuario is None:
                username = self._username_libre(Usuario, datos["username"])
                usuario = Usuario(
                    email=datos["email"],
                    username=username,
                    first_name=datos["first_name"],
                    last_name=datos["last_name"],
                    es_admin=datos["es_admin"],
                )
                usuario.set_password(DEMO_PASSWORD)
                usuario.save()
            else:
                sin_colision = not Usuario.objects.filter(
                    username=datos["username"]
                ).exclude(pk=usuario.pk).exists()
                if sin_colision:
                    usuario.username = datos["username"]
                usuario.first_name = datos["first_name"]
                usuario.last_name = datos["last_name"]
                usuario.es_admin = datos["es_admin"]
                usuario.es_activo = True
                usuario.set_password(DEMO_PASSWORD)
                usuario.save(
                    update_fields=["username", "first_name", "last_name", "es_admin", "es_activo", "password"]
                )

            perfil_data = datos["perfil"]
            Perfil.objects.update_or_create(
                usuario=usuario,
                defaults={
                    "nivel": perfil_data["nivel"],
                    "experiencia_anios": perfil_data["experiencia_anios"],
                    "disponibilidad_horas_semana": perfil_data["disponibilidad_horas_semana"],
                    "bio": perfil_data["bio"],
                    "github_username": perfil_data["github_username"],
                },
            )

            for nombre in datos["habilidades"]:
                habilidad = self._catalogo(Habilidad, nombre)
                UsuarioHabilidad.objects.get_or_create(usuario=usuario, habilidad=habilidad)
            for nombre in datos["tecnologias"]:
                tecnologia = self._catalogo(Tecnologia, nombre)
                UsuarioTecnologia.objects.get_or_create(usuario=usuario, tecnologia=tecnologia)
            for nombre in datos["intereses"]:
                interes = self._catalogo(Interes, nombre)
                UsuarioInteres.objects.get_or_create(usuario=usuario, interes=interes)
            self._fijar(
                Usuario, usuario.pk, creado_en=self._hace_dias(datos["creado_hace"])
            )

        self.stdout.write(self.style.SUCCESS(f"  usuarios y perfiles: {len(usuarios)}"))

    # ------------------------------------------------------------------
    # PROYECTOS Y VACANTES
    # ------------------------------------------------------------------

    def seed_proyectos(self):
        Usuario = self._model("accounts", "Usuario")
        Habilidad = self._model("accounts", "Habilidad")
        Tecnologia = self._model("accounts", "Tecnologia")
        Proyecto = self._model("projects", "Proyecto")
        Vacante = self._model("projects", "Vacante")
        ProyectoMedia = self._model("projects", "ProyectoMedia")
        VacanteHabilidad = self._model("projects", "VacanteHabilidadRequerida")
        VacanteTecnologia = self._model("projects", "VacanteTecnologiaRequerida")

        proyectos = [
            {
                "creador": "maria@devmatch.local",
                "nombre": "BrainTwist — Quizzes educativos",
                "creado_hace": 10,
                "descripcion": "Plataforma de quizzes con dificultad adaptativa para aulas.",
                "estado": Proyecto.ESTADO_PUBLICADO,
                "media": [{"tipo": ProyectoMedia.TIPO_LOGO, "archivo_url": "/media/seed/braintwist.png", "orden": 0}],
                "vacantes": [
                    {
                        "titulo": "Frontend Developer",
                        "descripcion": "Maquetar y conectar la interfaz de quizzes.",
                        "estado": Vacante.ESTADO_ABIERTA,
                        "cupos_totales": 2,
                        "habilidades": ["Frontend Development"],
                        "tecnologias": ["React", "Tailwind CSS"],
                    },
                    {
                        "titulo": "QA / Testing",
                        "descripcion": "Cubrir la suite de tests del módulo de evaluación.",
                        "estado": Vacante.ESTADO_ABIERTA,
                        "cupos_totales": 1,
                        "habilidades": ["QA / Testing"],
                        "tecnologias": ["JavaScript"],
                    },
                ],
            },
            {
                "creador": "maria@devmatch.local",
                "nombre": "ClinVis — Dashboards clínicos",
                "creado_hace": 40,
                "descripcion": "Visualización de indicadores para centros de salud.",
                "estado": Proyecto.ESTADO_RECLUTANDO,
                "media": [{"tipo": ProyectoMedia.TIPO_LOGO, "archivo_url": "/media/seed/clinvis.png", "orden": 0}],
                "vacantes": [
                    {
                        "titulo": "Backend Developer",
                        "descripcion": "API de indicadores y servicios de integración.",
                        "estado": Vacante.ESTADO_ABIERTA,
                        "cupos_totales": 3,
                        "habilidades": ["Backend Development", "Database Design"],
                        "tecnologias": ["Python", "Django", "PostgreSQL"],
                    },
                    {
                        "titulo": "Data Scientist",
                        "descripcion": "Modelos de análisis sobre los indicadores clínicos.",
                        "estado": Vacante.ESTADO_ABIERTA,
                        "cupos_totales": 1,
                        "habilidades": ["Data Science"],
                        "tecnologias": ["Python"],
                    },
                ],
            },
            {
                "creador": "juan@devmatch.local",
                "nombre": "DevRoom — Comunidad dev",
                "creado_hace": 55,
                "descripcion": "Red social ligera para estudiantes y desarrolladores junior.",
                "estado": Proyecto.ESTADO_EQUIPO_COMPLETO,
                "media": [],
                "vacantes": [],
            },
            {
                "creador": "maria@devmatch.local",
                "nombre": "FitTrack — App de hábitos",
                "creado_hace": 68,
                "descripcion": "Seguimiento de hábitos y rutinas de ejercicio con gráficos.",
                "estado": Proyecto.ESTADO_EN_DESARROLLO,
                "media": [],
                "vacantes": [],
            },
            {
                "creador": "juan@devmatch.local",
                "nombre": "ViajeSeguro — Alertas de viaje",
                "creado_hace": 90,
                "cierre_hace": 30,
                "descripcion": "Sistema de alertas de seguridad para viajeros.",
                "estado": Proyecto.ESTADO_FINALIZADO,
                "media": [],
                "vacantes": [],
            },
            {
                "creador": "juan@devmatch.local",
                "nombre": "PetMatch — Adopción responsable",
                "creado_hace": 18,
                "descripcion": "Conectar refugios con familias adoptantes y dar seguimiento a las adopciones.",
                "estado": Proyecto.ESTADO_RECLUTANDO,
                "media": [],
                "vacantes": [
                    {
                        "titulo": "Fullstack Developer",
                        "descripcion": "Formularios de adopción y panel de refugios.",
                        "estado": Vacante.ESTADO_ABIERTA,
                        "cupos_totales": 2,
                        "habilidades": ["Fullstack Development"],
                        "tecnologias": ["JavaScript", "Django"],
                    },
                ],
            },
            {
                "creador": "maria@devmatch.local",
                "nombre": "ResuMate — Optimizador de CV",
                "creado_hace": 3,
                "descripcion": "Sugerencias automáticas para armar un CV orientado a reclutadores tech.",
                "estado": Proyecto.ESTADO_PUBLICADO,
                "media": [],
                "vacantes": [
                    {
                        "titulo": "Backend Developer",
                        "descripcion": "Motor de sugerencias y análisis del CV.",
                        "estado": Vacante.ESTADO_ABIERTA,
                        "cupos_totales": 2,
                        "habilidades": ["Backend Development"],
                        "tecnologias": ["Python", "Django"],
                    },
                ],
            },
            {
                "creador": "juan@devmatch.local",
                "nombre": "GymLog — Entrenamientos colaborativos",
                "creado_hace": 27,
                "descripcion": "Rutinas compartidas y seguimiento de progreso entre estudiantes.",
                "estado": Proyecto.ESTADO_RECLUTANDO,
                "media": [],
                "vacantes": [
                    {
                        "titulo": "Frontend Developer",
                        "descripcion": "Interfaz de rutinas y gráficos de progreso.",
                        "estado": Vacante.ESTADO_ABIERTA,
                        "cupos_totales": 1,
                        "habilidades": ["Frontend Development"],
                        "tecnologias": ["React"],
                    },
                ],
            },
            {
                "creador": "maria@devmatch.local",
                "nombre": "MarketAI — IA de precios",
                "creado_hace": 80,
                "cierre_hace": 50,
                "descripcion": "Motor piloto de estimación de precios que no llegó a validarse.",
                "estado": Proyecto.ESTADO_CANCELADO,
                "media": [],
                "vacantes": [
                    {
                        "titulo": "Data Scientist",
                        "descripcion": "Modelo piloto de estimación de precios.",
                        "estado": Vacante.ESTADO_CANCELADA,
                        "cupos_totales": 1,
                        "habilidades": ["Data Science"],
                        "tecnologias": ["Python"],
                    },
                ],
            },
        ]

        for datos in proyectos:
            creador = Usuario.objects.get(email=datos["creador"])
            proyecto, creado = Proyecto.objects.get_or_create(
                creador=creador,
                nombre=datos["nombre"],
                defaults={
                    "descripcion": datos["descripcion"],
                    "estado": datos["estado"],
                },
            )
            if not creado:
                proyecto.descripcion = datos["descripcion"]
                proyecto.es_activo = True
                # No forzar transición si está en estado terminal (respeta triggers)
                terminales = {Proyecto.ESTADO_FINALIZADO, Proyecto.ESTADO_CANCELADO}
                if proyecto.estado not in terminales:
                    proyecto.estado = datos["estado"]
                proyecto.save(update_fields=["descripcion", "estado", "es_activo"])

            fechas = {"creado_en": self._hace_dias(datos["creado_hace"])}
            # finalizado_en/cancelado_en: el trigger solo los rellena al CAMBIAR
            # de estado; el seed inserta ya en estado terminal, así que se fijan
            # aquí, coherentes con el estado real del proyecto.
            if "cierre_hace" in datos:
                if proyecto.estado == Proyecto.ESTADO_FINALIZADO:
                    fechas["finalizado_en"] = self._hace_dias(datos["cierre_hace"])
                elif proyecto.estado == Proyecto.ESTADO_CANCELADO:
                    fechas["cancelado_en"] = self._hace_dias(datos["cierre_hace"])
            self._fijar(Proyecto, proyecto.pk, **fechas)

            for media in datos["media"]:
                ProyectoMedia.objects.get_or_create(
                    proyecto=proyecto,
                    tipo=media["tipo"],
                    defaults={"archivo_url": media["archivo_url"], "orden": media["orden"]},
                )

            for orden, vacante in enumerate(datos["vacantes"]):
                vac, _creada = Vacante.objects.get_or_create(
                    proyecto=proyecto,
                    titulo=vacante["titulo"],
                    defaults={
                        "descripcion": vacante["descripcion"],
                        "cupos_totales": vacante["cupos_totales"],
                        "estado": vacante["estado"],
                    },
                )
                if not _creada:
                    vac.estado = vacante["estado"]
                    vac.cupos_totales = vacante["cupos_totales"]
                    vac.es_activo = True
                    vac.save(update_fields=["estado", "cupos_totales", "es_activo"])
                self._fijar(
                    Vacante,
                    vac.pk,
                    creado_en=self._hace_dias(datos["creado_hace"] - 0.1 * (orden + 1)),
                )
                for nombre in vacante["habilidades"]:
                    habilidad = self._catalogo(Habilidad, nombre)
                    VacanteHabilidad.objects.get_or_create(vacante=vac, habilidad=habilidad)
                for nombre in vacante["tecnologias"]:
                    tecnologia = self._catalogo(Tecnologia, nombre)
                    VacanteTecnologia.objects.get_or_create(vacante=vac, tecnologia=tecnologia)

        self.stdout.write(self.style.SUCCESS(f"  proyectos y vacantes: {len(proyectos)}"))

    # ------------------------------------------------------------------
    # POSTULACIONES, INVITACIONES Y MEMBRESÍAS (escenarios de Match Score)
    # ------------------------------------------------------------------
    # Datos deterministas (no aleatorios) para que Squad B pueda maquetar el
    # desglose del Match Score (CR-05) y el snapshot congelado (CR-07) sin
    # esperar al motor real de Squad A. Cada escenario declara el puntaje por
    # factor; `match_score` se calcula con los pesos vigentes para que el
    # porcentaje y su desglose nunca queden incoherentes entre sí.

    def _pesos_activos(self):
        """Devuelve el perfil de pesos vigente (singleton) o lo crea."""
        Configuracion = self._model("matching", "ConfiguracionPesosMatching")
        pesos = Configuracion.objects.filter(es_activo=True).first()
        if pesos is None:
            pesos = Configuracion.objects.create(
                nombre="Ponderación estándar v1.0",
                peso_habilidades=Decimal("0.35"),
                peso_nivel=Decimal("0.15"),
                peso_tecnologias=Decimal("0.30"),
                peso_experiencia=Decimal("0.10"),
                peso_disponibilidad=Decimal("0.10"),
                es_activo=True,
            )
        return pesos

    @staticmethod
    def _score_y_factores(pesos, factores):
        """
        Construye el `match_factores` (JSONB) en la forma documentada en
        DEVMATCH-BD 9 y calcula el `match_score` ponderado con esos mismos
        pesos (suma exacta, sin recálculos posteriores).
        """
        desglose = {}
        score = Decimal("0")
        for nombre in (
            "habilidades",
            "nivel",
            "tecnologias",
            "experiencia",
            "disponibilidad",
        ):
            peso = getattr(pesos, f"peso_{nombre}")
            puntaje = int(factores.get(nombre, 0))
            desglose[nombre] = {"score": puntaje, "peso": float(peso)}
            score += Decimal(puntaje) * peso
        return score.quantize(Decimal("0.01")), desglose

    @staticmethod
    def _buscar_vacante(Proyecto, Vacante, nombre_proyecto, titulo_vacante):
        proyecto = Proyecto.objects.filter(nombre=nombre_proyecto).first()
        if proyecto is None:
            return None, None
        vacante = Vacante.objects.filter(
            proyecto=proyecto, titulo=titulo_vacante
        ).first()
        return proyecto, vacante

    @staticmethod
    def _upsert_postulacion(Postulacion, vacante, usuario, defaults):
        """
        Garantiza que la postulación de este escenario tenga EXACTAMENTE los
        valores declarados (score/factores/estado), aunque ya exista una fila de
        una siembra anterior en la BD compartida. Prefiere reutilizar la fila
        activa (pendiente/preseleccionada) para no dejar dos activas por par.
        """
        qs = Postulacion.objects.filter(vacante=vacante, postulante=usuario)
        activas = (Postulacion.ESTADO_PENDIENTE, Postulacion.ESTADO_PRESELECCIONADA)
        post = (
            qs.filter(estado__in=activas).order_by("-id").first()
            or qs.order_by("-id").first()
        )
        if post is None:
            return Postulacion.objects.create(
                vacante=vacante, postulante=usuario, **defaults
            )
        for campo, valor in defaults.items():
            setattr(post, campo, valor)
        post.save(update_fields=list(defaults.keys()))
        return post

    def _normalizar_seed_legado(self, Postulacion, pesos):
        """
        Las siembras anteriores dejaban postulaciones con
        `match_factores={"notas": "seed"}` (sin desglose por factor), lo que
        deja en blanco la barra y el desglose del Match Score en la UI. Se les
        reemplaza por un desglose válido que reproduce su `match_score`. Solo
        toca filas marcadas como seed (nunca datos reales) y es idempotente:
        tras normalizar, la marca desaparece.
        """
        nombres = (
            "habilidades",
            "nivel",
            "tecnologias",
            "experiencia",
            "disponibilidad",
        )
        actualizadas = 0
        for post in Postulacion.objects.filter(match_factores={"notas": "seed"}):
            base = post.match_score
            if base != base.to_integral_value():
                continue
            _, factores = self._score_y_factores(
                pesos, {nombre: int(base) for nombre in nombres}
            )
            post.match_factores = factores
            if post.pesos_usados_id is None:
                post.pesos_usados = pesos
                post.save(update_fields=["match_factores", "pesos_usados"])
            else:
                post.save(update_fields=["match_factores"])
            actualizadas += 1
        return actualizadas

    def seed_interacciones(self):
        Usuario = self._model("accounts", "Usuario")
        Proyecto = self._model("projects", "Proyecto")
        Vacante = self._model("projects", "Vacante")
        Postulacion = self._model("applications", "Postulacion")
        Invitacion = self._model("teams", "Invitacion")
        EquipoMembresia = self._model("teams", "EquipoMembresia")

        pesos = self._pesos_activos()

        # Escenarios de postulación: ALTO (calza con los requisitos), MEDIO
        # (calce parcial) y BAJO (poca compatibilidad). Cubren el rango que la
        # vista de Match Score debe saber pintar (barra + desglose por factor).
        escenarios = [
            {
                "postulante": "juan@devmatch.local",
                "proyecto": "BrainTwist — Quizzes educativos",
                "vacante": "Frontend Developer",
                "estado": Postulacion.ESTADO_PENDIENTE,
                "factores": {"habilidades": 95, "nivel": 80, "tecnologias": 100, "experiencia": 70, "disponibilidad": 100},
                "postulado_hace": 8,
            },
            {
                "postulante": "ana@devmatch.local",
                "proyecto": "ClinVis — Dashboards clínicos",
                "vacante": "Data Scientist",
                "estado": Postulacion.ESTADO_PENDIENTE,
                "factores": {"habilidades": 90, "nivel": 80, "tecnologias": 100, "experiencia": 70, "disponibilidad": 80},
                "postulado_hace": 30,
            },
            {
                "postulante": "carlos@devmatch.local",
                "proyecto": "BrainTwist — Quizzes educativos",
                "vacante": "Frontend Developer",
                "estado": Postulacion.ESTADO_PRESELECCIONADA,
                "factores": {"habilidades": 70, "nivel": 40, "tecnologias": 80, "experiencia": 30, "disponibilidad": 70},
                "postulado_hace": 6,
            },
            {
                "postulante": "ana@devmatch.local",
                "proyecto": "ClinVis — Dashboards clínicos",
                "vacante": "Backend Developer",
                "estado": Postulacion.ESTADO_PENDIENTE,
                "factores": {"habilidades": 55, "nivel": 80, "tecnologias": 85, "experiencia": 60, "disponibilidad": 80},
                "postulado_hace": 35,
            },
            {
                "postulante": "carlos@devmatch.local",
                "proyecto": "ClinVis — Dashboards clínicos",
                "vacante": "Backend Developer",
                "estado": Postulacion.ESTADO_RECHAZADA,
                "factores": {"habilidades": 25, "nivel": 40, "tecnologias": 30, "experiencia": 20, "disponibilidad": 70},
                "postulado_hace": 33,
                "decidido_hace": 28,
                "motivo": "Perfil sin experiencia en backend.",
            },
            {
                "postulante": "admin@devmatch.local",
                "proyecto": "ResuMate — Optimizador de CV",
                "vacante": "Backend Developer",
                "estado": Postulacion.ESTADO_PENDIENTE,
                "factores": {"habilidades": 25, "nivel": 100, "tecnologias": 40, "experiencia": 100, "disponibilidad": 100},
                "postulado_hace": 2,
            },
            {
                "postulante": "carlos@devmatch.local",
                "proyecto": "ResuMate — Optimizador de CV",
                "vacante": "Backend Developer",
                "estado": Postulacion.ESTADO_PENDIENTE,
                "factores": {"habilidades": 10, "nivel": 40, "tecnologias": 20, "experiencia": 15, "disponibilidad": 60},
                "postulado_hace": 1,
            },
        ]

        creadas = 0
        for esc in escenarios:
            usuario = Usuario.objects.filter(email=esc["postulante"]).first()
            proyecto, vacante = self._buscar_vacante(
                Proyecto, Vacante, esc["proyecto"], esc["vacante"]
            )
            if usuario is None or vacante is None:
                continue
            if proyecto.creador_id == usuario.id:
                continue
            score, factores = self._score_y_factores(pesos, esc["factores"])
            defaults = {
                "estado": esc["estado"],
                "match_score": score,
                "match_factores": factores,
                "pesos_usados": pesos,
                "decidido_por": None,
                "decidido_en": None,
                "motivo_decision": esc.get("motivo", ""),
            }
            if esc["estado"] in (
                Postulacion.ESTADO_ACEPTADA,
                Postulacion.ESTADO_RECHAZADA,
            ):
                defaults["decidido_por"] = proyecto.creador
                defaults["decidido_en"] = self._hace_dias(esc["decidido_hace"])
            post = self._upsert_postulacion(Postulacion, vacante, usuario, defaults)
            self._fijar(
                Postulacion, post.pk, postulado_en=self._hace_dias(esc["postulado_hace"])
            )
            creadas += 1

        # Membresías por postulación aceptada. La aceptación y el INSERT de la
        # membresía van en una sola transacción (DEVMATCH-BD 8.3). El trigger
        # trg_membresia_actualiza_cupos recalcula cupos_ocupados: NUNCA lo
        # escribimos a mano. `carlos` queda con 2 membresías activas y pocas
        # horas de disponibilidad -> escenario de choque de disponibilidad;
        # ResuMate queda con 1/2 cupos (casi llena) -> límite de cupos.
        # Cada tupla: (email, proyecto, vacante, postulado_hace, decidido_hace),
        # con los desfases en días.
        aceptadas = [
            ("ana@devmatch.local", "ResuMate — Optimizador de CV", "Backend Developer", 2.5, 2.2),
            ("carlos@devmatch.local", "BrainTwist — Quizzes educativos", "QA / Testing", 9, 7),
            ("carlos@devmatch.local", "GymLog — Entrenamientos colaborativos", "Frontend Developer", 25, 22),
        ]
        membresias = 0
        for email, nombre_proyecto, titulo_vacante, postulado_hace, decidido_hace in aceptadas:
            usuario = Usuario.objects.filter(email=email).first()
            proyecto, vacante = self._buscar_vacante(
                Proyecto, Vacante, nombre_proyecto, titulo_vacante
            )
            if usuario is None or vacante is None or proyecto.creador_id == usuario.id:
                continue
            score, factores = self._score_y_factores(
                pesos,
                {"habilidades": 80, "nivel": 70, "tecnologias": 80, "experiencia": 60, "disponibilidad": 80},
            )
            fecha_decision = self._hace_dias(decidido_hace)
            try:
                with transaction.atomic():
                    postulacion = self._upsert_postulacion(
                        Postulacion,
                        vacante,
                        usuario,
                        {
                            "estado": Postulacion.ESTADO_ACEPTADA,
                            "match_score": score,
                            "match_factores": factores,
                            "pesos_usados": pesos,
                            "decidido_por": proyecto.creador,
                            "decidido_en": fecha_decision,
                            "motivo_decision": "",
                        },
                    )
                    membresia, _ = EquipoMembresia.objects.get_or_create(
                        vacante=vacante,
                        usuario=usuario,
                        defaults={
                            "proyecto": proyecto,
                            "postulacion": postulacion,
                            "invitacion": None,
                            "estado": EquipoMembresia.ESTADO_ACTIVO,
                        },
                    )
                    self._fijar(
                        Postulacion,
                        postulacion.pk,
                        postulado_en=self._hace_dias(postulado_hace),
                    )
                    # Ingresa al equipo en el momento en que se acepta.
                    self._fijar(EquipoMembresia, membresia.pk, ingreso_en=fecha_decision)
                    membresias += 1
            except Exception:
                continue

        # Membresía por invitación aceptada (origen XOR: invitación, no
        # postulación) para que Squad B pueda probar ambos caminos de ingreso.
        # Cada tupla: (email, proyecto, vacante, creada_hace, respondida_hace).
        invitaciones = [
            ("admin@devmatch.local", "PetMatch — Adopción responsable", "Fullstack Developer", 15, 13),
        ]
        for email, nombre_proyecto, titulo_vacante, creada_hace, respondida_hace in invitaciones:
            usuario = Usuario.objects.filter(email=email).first()
            proyecto, vacante = self._buscar_vacante(
                Proyecto, Vacante, nombre_proyecto, titulo_vacante
            )
            if usuario is None or vacante is None or proyecto.creador_id == usuario.id:
                continue
            fecha_respuesta = self._hace_dias(respondida_hace)
            try:
                with transaction.atomic():
                    invitacion, _ = Invitacion.objects.get_or_create(
                        vacante=vacante,
                        usuario_invitado=usuario,
                        defaults={
                            "invitado_por": proyecto.creador,
                            "estado": Invitacion.ESTADO_ACEPTADA,
                            "respondido_en": fecha_respuesta,
                        },
                    )
                    if invitacion.estado != Invitacion.ESTADO_ACEPTADA:
                        invitacion.estado = Invitacion.ESTADO_ACEPTADA
                        invitacion.respondido_en = fecha_respuesta
                        invitacion.save(update_fields=["estado", "respondido_en"])
                    self._fijar(
                        Invitacion,
                        invitacion.pk,
                        creado_en=self._hace_dias(creada_hace),
                        respondido_en=fecha_respuesta,
                    )
                    membresia, _ = EquipoMembresia.objects.get_or_create(
                        vacante=vacante,
                        usuario=usuario,
                        defaults={
                            "proyecto": proyecto,
                            "postulacion": None,
                            "invitacion": invitacion,
                            "estado": EquipoMembresia.ESTADO_ACTIVO,
                        },
                    )
                    self._fijar(EquipoMembresia, membresia.pk, ingreso_en=fecha_respuesta)
                    membresias += 1
            except Exception:
                continue

        normalizadas = self._normalizar_seed_legado(Postulacion, pesos)

        self.stdout.write(
            self.style.SUCCESS(
                f"  interacciones: {creadas} postulaciones, {membresias} membresías "
                f"(1 vía invitación), {normalizadas} filas seed antiguas normalizadas"
            )
        )