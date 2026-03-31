"""AAX WSGI compatibility wrapper for galaxy-ng service.

Keeps upstream Django routing intact and only redirects legacy root/UI
paths to the Galaxy API entrypoint.
"""

from pulpcore.app.wsgi import application as django_application


def application(environ, start_response):
    path = environ.get("PATH_INFO", "")

    if path == "/" or path == "/ui/" or path.startswith("/ui/"):
        start_response("302 Found", [("Location", "/api/galaxy/"), ("Content-Length", "0")])
        return [b""]

    return django_application(environ, start_response)
