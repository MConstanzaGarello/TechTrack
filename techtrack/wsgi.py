"""Punto de entrada WSGI (lo usa gunicorn en Render)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "techtrack.settings")

application = get_wsgi_application()
