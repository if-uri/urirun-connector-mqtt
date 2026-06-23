# urirun-connector-mqtt

MQTT connector for [ifURI](https://ifuri.com) / [urirun](https://github.com/if-uri/urirun).
Publish messages and bridge device commands to MQTT through `mqtt://` and
`device://` routes.

Catalog page: <https://connect.ifuri.com/connectors/mqtt>

## Routes

| URI | Operation |
| --- | --- |
| `mqtt://broker/topic/command/publish` | publish a message to a topic |
| `device://device-01/led/command/set` | set a device command, bridged to `device/<device>/<component>/set` |

## Safety / dry-run

Publishing is a side effect, so both routes default to **dry-run** — they return
the publish plan without contacting a broker (so tests and smoke run offline).
Set `dry_run=false` to actually publish, which needs the optional `paho-mqtt`
dependency and a reachable broker:

```bash
pip install "urirun-connector-mqtt[mqtt] @ git+https://github.com/if-uri/urirun-connector-mqtt.git@v0.1.0"
urirun-connector-mqtt publish --topic sensors/temp --message 21.5            # dry-run
urirun-connector-mqtt publish --topic sensors/temp --message 21.5 --dry-run false --broker localhost
```

## Test

```bash
pip install -e ".[test]" && pytest -q
```

## License

Released under the terms in [LICENSE](LICENSE).
