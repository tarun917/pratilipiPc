from django.apps import AppConfig


class DigitalcomicdeskConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'digitalcomicDesk'

    def ready(self):
        # Import signals so handlers register
        from . import signals  # noqa: F401
