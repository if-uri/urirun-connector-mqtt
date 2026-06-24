# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""MQTT publish + device-command bridge routes for urirun.

Two routes, matching the connect.ifuri.com contract:

* ``mqtt://broker/topic/command/publish``  -- publish a message to a topic
* ``device://device-01/led/command/set``   -- set a device command, bridged to an
  MQTT publish on ``device/<device>/<component>/set``

Each route is declared once with a typed ``@<conn>.handler(..., isolated=True)``:
the function signature becomes the input schema and the function *is* the
implementation. ``isolated=True`` runs the route out-of-process through the
shared ``python -m urirun.exec`` runner, so the binding stays
**registry-portable** — it executes from a compiled/served registry
(``urirun run`` / ``urirun node serve``) with only the package importable, no
``_exec.py`` shim and no console-script install.

Both routes publish to a broker over the network. The dry-run gate belongs to
urirun's registry runner (``urirun run ... --execute``), not to a function
param: the route logic always contains only the real path. Publishing needs the
optional ``paho-mqtt`` dependency and a reachable broker. The manifest stays
prose-only; ``routes``/``uriSchemes`` are derived from the declared routes.

Both connector objects share the ``mqtt`` connector id, so a single
``conn.bindings()`` / ``conn.manifest()`` / ``conn.cli()`` covers both schemes.
"""

from __future__ import annotations

import re
from typing import Any

import urirun

CONNECTOR_ID = "mqtt"
conn = urirun.connector(CONNECTOR_ID, scheme="mqtt", target="broker")
# device:// command-bridge routes (device://device-01/...) live in the same connector.
device = urirun.connector(CONNECTOR_ID, scheme="device", target="device-01")


# --- route logic (real implementation) ------------------------------------

def _resolve_secret(value: str, secret_allow: str = "") -> str:
    """Resolve a credential that may be a secret *reference*, via the urirun secrets layer.

    ``value`` may be a literal, a ``secret://``/``getv://`` reference, or a ``{getv:NAME}`` /
    ``{secret:...}`` placeholder, resolved under a deny-by-default allow-list (``secret_allow``
    globs). A literal passes through; empty returns ''. Keeps the broker password addressed by
    reference instead of being embedded in the URI/manifest.
    """
    value = (value or "").strip()
    if not value:
        return ""
    try:
        from urirun.runtime import secrets as _secrets
    except Exception:  # noqa: BLE001 - older urirun without the secrets layer
        return value if ("://" not in value and "{" not in value) else ""
    allow = [p for p in re.split(r"[,\s]+", secret_allow or "") if p]
    if _secrets.has_secret(value):
        return _secrets.fill_secrets(value, execute=True, allow=allow)
    if value.startswith(("secret://", "getv://")):
        return _secrets.resolve(value, execute=True, allow=allow).reveal()
    return value


def _publish_real(topic: str, message: str, qos: int, retain: bool, broker: str, port: int,
                  username: str = "", password: str = "") -> dict[str, Any]:
    try:
        import paho.mqtt.publish as mqtt_publish
    except ImportError:
        return urirun.fail("paho-mqtt is not installed; install with the [mqtt] extra")
    auth = {"username": username, "password": password} if username else None
    try:
        mqtt_publish.single(topic, payload=message, qos=qos, retain=retain,
                            hostname=broker, port=port, auth=auth)
    except Exception as exc:  # noqa: BLE001 - report broker errors as JSON
        return urirun.fail(str(exc), action="publish", topic=topic)
    return urirun.ok(action="publish", published=True, topic=topic, broker=broker)


# --- route declarations: schema + implementation derived from the signature ---

@conn.handler("topic/command/publish", isolated=True, meta={"label": "Publish an MQTT message"})
def publish(topic: str, message: str = "", qos: int = 0, retain: bool = False, broker: str = "localhost", port: int = 1883,
            username: str = "", password: str = "", secret_allow: str = "") -> dict[str, Any]:
    """Publish a message to an MQTT topic over the network.

    For an authenticated broker pass ``username`` and ``password``; the password may be a
    secret *reference* (``getv://MQTT_PASS`` / ``secret://keyring/mqtt#pass``) resolved through
    the secrets layer under ``secret_allow`` (deny-by-default). Anonymous brokers need neither.
    """
    if not topic:
        return urirun.fail("topic is required")
    try:
        secret = _resolve_secret(password, secret_allow)
    except PermissionError as exc:
        return urirun.fail(f"password secret denied by policy (add it to secret_allow): {exc}", action="publish", topic=topic)
    return _publish_real(topic, message, qos, retain, broker, port, username=username, password=secret)


@device.handler("device://device-01/led/command/set", isolated=True, meta={"label": "Set a device command over MQTT"})
def device_set(device: str = "device-01", component: str = "led", value: str = "on", broker: str = "localhost", port: int = 1883,
               username: str = "", password: str = "", secret_allow: str = "") -> dict[str, Any]:
    """Set a device command, bridged to an MQTT publish on ``device/<device>/<component>/set``."""
    topic = f"device/{device}/{component}/set"
    result = publish(topic, message=value, broker=broker, port=port,
                     username=username, password=password, secret_allow=secret_allow)
    result["device"] = device
    result["component"] = component
    result["value"] = value
    return result


# --- authoring surface: bindings / manifest / CLI --------------------------

def urirun_bindings() -> dict[str, Any]:
    """Serializable v2 bindings for this connector (entry point: urirun.bindings).

    Both connector objects share the ``mqtt`` id, so one ``.bindings()`` returns
    both routes.
    """
    return conn.bindings()


def connector_manifest() -> dict[str, Any]:
    """Full manifest: prose (connector.manifest.json) + routes/uriSchemes/
    adapterKinds/examples derived from the handlers."""
    return conn.manifest(urirun.load_manifest(__package__))


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point: subcommands + dispatch derived from the handlers."""
    return conn.cli(argv, manifest_prose=urirun.load_manifest(__package__))


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
