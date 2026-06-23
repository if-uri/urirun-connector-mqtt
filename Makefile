.PHONY: help manifest bindings smoke test
help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'
manifest: ## Print the connector manifest
	urirun-connector-mqtt manifest
bindings: ## Print urirun bindings
	urirun-connector-mqtt bindings
smoke: ## bindings -> urirun connectors smoke (dry-run publish, no broker needed)
	urirun-connector-mqtt bindings | urirun connectors smoke - \
	  --run 'mqtt://broker/topic/command/publish' --payload '{"topic":"sensors/temp","message":"21.5"}' \
	  --allow 'mqtt://*' --name mqtt
test: ## Install editable + smoke
	pip install -e . && python3 -m pytest -q && $(MAKE) smoke
