from django.apps import apps as django_apps
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    python manage.py seed_data

    Genera datos de prueba para que Squad B pueda maquetar vistas sin
    depender de que el backend real esté terminado (rol del Integrador,
    ver DEVMATCH-DISTRIBUCION.md).

    Ahora mismo es un ESQUELETO: accounts.Usuario y projects.Proyecto
    todavía no existen (esas ramas están en progreso), así que el comando
    detecta eso y avisa en vez de fallar. Cuando esos modelos existan,
    completa seed_usuarios()/seed_proyectos() más abajo con datos que
    cubran varios escenarios (roles, niveles, estados de proyecto/vacante).
    """

    help = "Genera datos de prueba (fixtures) para Squad B."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("== DevMatch: seed_data =="))

        Usuario = self._get_model("accounts", "Usuario")
        Proyecto = self._get_model("projects", "Proyecto")

        if Usuario is None or Proyecto is None:
            faltantes = [
                nombre
                for nombre, modelo in (("accounts.Usuario", Usuario), ("projects.Proyecto", Proyecto))
                if modelo is None
            ]
            self.stdout.write(
                self.style.WARNING(
                    "Todavía no existen: " + ", ".join(faltantes) + ".\n"
                    "Este comando es un esqueleto — vuelve a correrlo cuando esas "
                    "apps tengan sus modelos y completa seed_usuarios()/"
                    "seed_proyectos() en apps/core/management/commands/seed_data.py."
                )
            )
            return

        self.seed_usuarios(Usuario)
        self.seed_proyectos(Proyecto)
        self.stdout.write(self.style.SUCCESS("Datos de prueba generados correctamente."))

    @staticmethod
    def _get_model(app_label, model_name):
        try:
            return django_apps.get_model(app_label, model_name)
        except LookupError:
            return None

    def seed_usuarios(self, Usuario):
        # TODO: crear usuarios con distintos roles/niveles/perfiles,
        # ver DEVMATCH-BD.md sección 5.1 (usuarios, perfiles).
        raise NotImplementedError("seed_usuarios: pendiente de implementar")

    def seed_proyectos(self, Proyecto):
        # TODO: crear proyectos/vacantes en distintos estados,
        # ver DEVMATCH-BD.md sección 5.2 (proyectos, vacantes).
        raise NotImplementedError("seed_proyectos: pendiente de implementar")