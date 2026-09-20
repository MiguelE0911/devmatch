from django.apps import apps as django_apps
from django.core.management.base import BaseCommand

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
    """

    help = "Genera datos de prueba (fixtures) para Squad B."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("== DevMatch: seed_data =="))
        self.seed_usuarios()
        self.seed_proyectos()
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
                usuario.set_password(DEMO_PASSWORD)
                usuario.save(
                    update_fields=["username", "first_name", "last_name", "es_admin", "password"]
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
                "descripcion": "Red social ligera para estudiantes y desarrolladores junior.",
                "estado": Proyecto.ESTADO_EQUIPO_COMPLETO,
                "media": [],
                "vacantes": [],
            },
            {
                "creador": "maria@devmatch.local",
                "nombre": "FitTrack — App de hábitos",
                "descripcion": "Seguimiento de hábitos y rutinas de ejercicio con gráficos.",
                "estado": Proyecto.ESTADO_EN_DESARROLLO,
                "media": [],
                "vacantes": [],
            },
            {
                "creador": "juan@devmatch.local",
                "nombre": "ViajeSeguro — Alertas de viaje",
                "descripcion": "Sistema de alertas de seguridad para viajeros.",
                "estado": Proyecto.ESTADO_FINALIZADO,
                "media": [],
                "vacantes": [],
            },
            {
                "creador": "maria@devmatch.local",
                "nombre": "MarketAI — IA de precios",
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
                proyecto.estado = datos["estado"]
                proyecto.es_activo = True
                proyecto.save()

            for media in datos["media"]:
                ProyectoMedia.objects.get_or_create(
                    proyecto=proyecto,
                    tipo=media["tipo"],
                    defaults={"archivo_url": media["archivo_url"], "orden": media["orden"]},
                )

            for vacante in datos["vacantes"]:
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
                    vac.save()
                for nombre in vacante["habilidades"]:
                    habilidad = self._catalogo(Habilidad, nombre)
                    VacanteHabilidad.objects.get_or_create(vacante=vac, habilidad=habilidad)
                for nombre in vacante["tecnologias"]:
                    tecnologia = self._catalogo(Tecnologia, nombre)
                    VacanteTecnologia.objects.get_or_create(vacante=vac, tecnologia=tecnologia)

        self.stdout.write(self.style.SUCCESS(f"  proyectos y vacantes: {len(proyectos)}"))