"""CT1 Airflow webserver config — session cookie isolated from CT2."""
from __future__ import annotations
import os
from flask_appbuilder.const import AUTH_DB

basedir = os.path.abspath(os.path.dirname(__file__))

WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None
AUTH_TYPE = AUTH_DB

# Unique cookie name so CT1 and CT2 don't share the browser session on localhost
SESSION_COOKIE_NAME = "ct1_session"
