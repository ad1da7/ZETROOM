import os, sys
INTERP = "/var/www/u3734581/data/www/zetroom.ru/venv/bin/python"
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)
sys.path.insert(0, "/var/www/u3734581/data/www/zetroom.ru")
os.environ["DJANGO_SETTINGS_MODULE"] = "party_core.settings"
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
