#!/var/www/u3734581/data/www/zetroom.ru/venv/bin/python
import os, sys
from urllib.parse import unquote
sys.path.insert(0, "/var/www/u3734581/data/www/zetroom.ru")
os.environ["DJANGO_SETTINGS_MODULE"] = "party_core.settings"
from wsgiref.handlers import CGIHandler
from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()
def fixed_app(environ, start_response):
    environ["SCRIPT_NAME"] = ""
    req_uri = environ.get("REQUEST_URI", "/")
    path = req_uri.split("?", 1)[0]
    environ["PATH_INFO"] = unquote(path)
    return app(environ, start_response)
CGIHandler().run(fixed_app)
