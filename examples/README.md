# mqtt connector — examples

Publish to MQTT devices (topic resolved without a broker).

## Install
```bash
urirun install urirun-connector-mqtt
```
`urirun install` resolves catalog ids via connect.ifuri.com; `--catalog <url>` points at a
local/on-prem registry; a full package name / git URL / path falls back to `pip install`.

## Run
```bash
# Publish to MQTT devices (topic resolved without a broker) (read)
urirun run 'device://device-01/led/command/set' --payload '{"state": "on"}' --execute --allow 'device://*'

# preview without running (dry-run): drop --execute
urirun run 'device://device-01/led/command/set' --payload '{"state": "on"}' --allow 'device://*'
```

## Inspect the runtime (no path — like error:// / log://)
```bash
urirun list | grep 'device://'                                   # this connector's routes
urirun run 'registry://local/routes/query/list' --payload '{"scheme":"device"}' --allow 'registry://*'
urirun run 'registry://local/bindings/query/show' --payload '{"uri":"device://device-01/led/command/set"}' --allow 'registry://*'   # full typed contract
urirun errors                                                      # recent runtime errors (error://)
```

## Generate a client / API surface from the binding
```bash
urirun discover | urirun gen openapi - --out openapi.json   # OpenAPI 3 (one path per route)
urirun discover | urirun gen proto   - --out service.proto  # protobuf + gRPC (typed rpc per route)
urirun discover | urirun gen client  - --out client.py      # typed Python client
```
