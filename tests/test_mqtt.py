# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

from __future__ import annotations

import json

import urirun
from urirun import v2
from urirun_connector_mqtt import (
    connector_manifest,
    device_set,
    main,
    publish,
    urirun_bindings,
)
import urirun_connector_mqtt.core as core

ROUTE_PUBLISH = "mqtt://broker/topic/command/publish"
ROUTE_DEVICE = "device://device-01/led/command/set"


def _fake_publish_real(monkeypatch):
    """Replace the real broker call so no network is touched."""
    monkeypatch.setattr(
        core,
        "_publish_real",
        lambda topic, message, qos, retain, broker, port, username="", password="": urirun.ok(
            action="publish", published=True, topic=topic, broker=broker
        ),
    )


def test_publish_requires_topic() -> None:
    assert publish("")["ok"] is False


def test_publish_no_real_broker(monkeypatch) -> None:
    _fake_publish_real(monkeypatch)
    result = publish("sensors/temp", message="21.5", broker="b")
    assert result["ok"] is True
    assert result["published"] is True
    assert result["topic"] == "sensors/temp"
    assert result["broker"] == "b"


def test_device_set_maps_to_topic(monkeypatch) -> None:
    _fake_publish_real(monkeypatch)
    result = device_set(device="device-01", component="led", value="on")
    assert result["topic"] == "device/device-01/led/set"
    assert result["value"] == "on"
    assert result["device"] == "device-01"
    assert result["component"] == "led"


def test_publish_resolves_password_secret_reference(monkeypatch) -> None:
    seen = {}
    monkeypatch.setattr(
        core, "_publish_real",
        lambda topic, message, qos, retain, broker, port, username="", password="":
            seen.update(user=username, pw=password) or urirun.ok(published=True, topic=topic, broker=broker),
    )
    monkeypatch.setenv("MQTT_SECRET", "br0kerpass")

    ok = publish("sensors/temp", message="21.5", username="iot",
                 password="getv://MQTT_SECRET", secret_allow="getv://MQTT_SECRET")
    assert ok["ok"] is True
    assert seen == {"user": "iot", "pw": "br0kerpass"}  # reference resolved to the real password

    denied = publish("sensors/temp", message="21.5", username="iot", password="getv://MQTT_SECRET")
    assert denied["ok"] is False
    assert "denied by policy" in denied["error"]


def test_bindings_are_isolated_handlers() -> None:
    b = urirun_bindings()["bindings"]
    assert set(b) == {ROUTE_PUBLISH, ROUTE_DEVICE}

    pub = b[ROUTE_PUBLISH]
    # registry-portable in-process handler: runs out-of-process via urirun.exec
    assert pub["adapter"] == "local-function-subprocess"
    assert pub["python"]["module"] == "urirun_connector_mqtt.core"
    assert pub["python"]["export"] == "publish"
    assert "argv" not in pub

    dev = b[ROUTE_DEVICE]
    assert dev["adapter"] == "local-function-subprocess"
    assert dev["python"]["module"] == "urirun_connector_mqtt.core"
    assert dev["python"]["export"] == "device_set"
    assert "argv" not in dev

    json.dumps(urirun_bindings())  # serializable: no live ref leaks


def test_compiles_and_routes_present() -> None:
    registry = urirun.compile_registry(urirun_bindings())
    uris = {r["uri"] for r in urirun.list_routes(registry)}
    assert ROUTE_PUBLISH in uris
    assert ROUTE_DEVICE in uris


def test_publish_runs_from_compiled_registry() -> None:
    # the whole point: a serialized->compiled registry still EXECUTES the route
    # out-of-process via `python -m urirun.exec` (no `_exec.py`, no console script).
    # No real broker is reachable here, so the connector returns a JSON error
    # envelope (missing paho-mqtt / connection refused) — what matters is that the
    # handler ran as a function (`result.value` present), not a "ref is not callable".
    registry = urirun.compile_registry(json.loads(json.dumps(urirun_bindings())))
    env = v2.run(
        ROUTE_PUBLISH,
        registry,
        payload={"topic": "t", "message": "x", "broker": "127.0.0.1", "port": 1},
        mode="execute",
        policy=urirun.policy(allow=["mqtt://*"]),
    )
    result = env["result"]
    assert result["ref"] == "urirun_connector_mqtt.core:publish"
    assert isinstance(result["value"], dict)  # function ran out-of-process
    assert "is not callable" not in (result.get("stderr") or "")


def test_device_set_runs_from_compiled_registry() -> None:
    registry = urirun.compile_registry(json.loads(json.dumps(urirun_bindings())))
    env = v2.run(
        ROUTE_DEVICE,
        registry,
        payload={"device": "device-01", "component": "led", "value": "off",
                 "broker": "127.0.0.1", "port": 1},
        mode="execute",
        policy=urirun.policy(allow=["device://*"]),
    )
    result = env["result"]
    assert result["ref"] == "urirun_connector_mqtt.core:device_set"
    assert isinstance(result["value"], dict)  # function ran out-of-process
    assert "is not callable" not in (result.get("stderr") or "")


def test_manifest_prose_plus_derived_routes() -> None:
    m = connector_manifest()
    assert m["id"] == "mqtt"
    assert set(m["routes"]) == {ROUTE_PUBLISH, ROUTE_DEVICE}
    assert set(m["uriSchemes"]) == {"mqtt", "device"}
    assert m["summary"] and m["keywords"]  # prose preserved
    json.dumps(m)


def test_cli_bindings_and_manifest(capsys) -> None:
    assert main(["bindings"]) == 0
    assert ROUTE_PUBLISH in json.loads(capsys.readouterr().out)["bindings"]
    assert main(["manifest"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "mqtt"
