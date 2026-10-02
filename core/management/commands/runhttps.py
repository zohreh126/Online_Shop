"""Run the Django development server over local HTTPS.

This command intentionally targets local development and demo environments.
For a real deployment, TLS should terminate at a production web server or
reverse proxy instead.
"""

from __future__ import annotations

import re
import shutil
import ssl
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.servers.basehttp import (
    ThreadedWSGIServer,
    WSGIRequestHandler,
    get_internal_wsgi_application,
)

_ADDRPORT_RE = re.compile(r"^(?P<host>[^:]+)(?::(?P<port>\d+))?$")


class SecureWSGIRequestHandler(WSGIRequestHandler):
    """Tell Django that requests arrived through the local TLS socket."""

    def get_environ(self):
        environ = super().get_environ()
        environ["wsgi.url_scheme"] = "https"
        return environ


class SecureThreadedWSGIServer(ThreadedWSGIServer):
    """Threaded Django WSGI server with an SSL-wrapped listening socket."""

    def __init__(self, *args, ssl_context: ssl.SSLContext, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket = ssl_context.wrap_socket(self.socket, server_side=True)


class Command(BaseCommand):
    help = "Run the local Django development server over HTTPS."

    def add_arguments(self, parser):
        parser.add_argument(
            "addrport",
            nargs="?",
            default="127.0.0.1:8443",
            help="Address and port, for example 127.0.0.1:8443.",
        )
        parser.add_argument(
            "--cert-file",
            default=".local-certs/nexora-local.crt",
            help="Path to the self-signed certificate.",
        )
        parser.add_argument(
            "--key-file",
            default=".local-certs/nexora-local.key",
            help="Path to the private key.",
        )

    def handle(self, *args, **options):
        host, port = self._parse_addrport(options["addrport"])
        cert_file = Path(options["cert_file"]).expanduser()
        key_file = Path(options["key_file"]).expanduser()

        self._ensure_certificate(cert_file, key_file)
        self._configure_local_https(host, port)

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(
            certfile=str(cert_file),
            keyfile=str(key_file),
        )

        try:
            application = get_internal_wsgi_application()
            server = SecureThreadedWSGIServer(
                (host, port),
                SecureWSGIRequestHandler,
                ssl_context=ssl_context,
                ipv6=False,
            )
            server.set_app(application)
        except OSError as exc:
            raise CommandError(f"HTTPS server could not start: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Nexora HTTPS development server running at "
                f"https://{host}:{port}/"
            )
        )
        self.stdout.write(
            "The certificate is self-signed and intended for local development only."
        )

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nHTTPS development server stopped.")
        finally:
            server.server_close()

    @staticmethod
    def _parse_addrport(value):
        match = _ADDRPORT_RE.match(value.strip())
        if not match:
            raise CommandError(
                "Invalid address. Use HOST:PORT, for example 127.0.0.1:8443."
            )

        host = match.group("host")
        port = int(match.group("port") or 8443)
        if not 1 <= port <= 65535:
            raise CommandError("Port must be between 1 and 65535.")
        return host, port

    @staticmethod
    def _ensure_certificate(cert_file: Path, key_file: Path):
        if cert_file.exists() and key_file.exists():
            return

        openssl = shutil.which("openssl")
        if openssl is None:
            raise CommandError(
                "openssl is required to generate the local HTTPS certificate."
            )

        cert_file.parent.mkdir(parents=True, exist_ok=True)
        command = [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "30",
            "-keyout",
            str(key_file),
            "-out",
            str(cert_file),
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise CommandError(
                f"Could not generate local certificate: {exc.stderr.strip()}"
            ) from exc

    @staticmethod
    def _configure_local_https(host, port):
        # These settings are normally false for plain HTTP local development.
        # The command is the explicit opt-in path for HTTPS, so make cookie and
        # CSRF behavior match the secure transport without changing runserver.
        settings.AUTH_COOKIE_SECURE = True
        settings.CSRF_COOKIE_SECURE = True
        settings.SESSION_COOKIE_SECURE = True

        trusted_origins = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []))
        for trusted_host in {host, "localhost", "127.0.0.1"}:
            origin = f"https://{trusted_host}:{port}"
            if origin not in trusted_origins:
                trusted_origins.append(origin)
        settings.CSRF_TRUSTED_ORIGINS = trusted_origins

        allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
        for allowed_host in {host, "localhost", "127.0.0.1"}:
            if allowed_host not in allowed_hosts and "*" not in allowed_hosts:
                allowed_hosts.append(allowed_host)
        settings.ALLOWED_HOSTS = allowed_hosts
