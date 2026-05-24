.PHONY: validate generate-execution-secrets render-multinode-env smoke-compose-multinode fixture-config

validate:
	dotnet build backend/OneClickHost.Api/OneClickHost.Api.csproj
	python -m pytest worker/tests
	cd frontend && npm run lint
	cd frontend && npm run build
	docker compose config -q
	docker compose -f docker-compose.execution.yml config -q

fixture-config:
	cd fixtures/oneclick-compose-fixture && docker compose config -q

generate-execution-secrets:
	./scripts/generate-execution-secrets.sh

render-multinode-env:
	./scripts/render-multinode-env.sh

smoke-compose-multinode:
	./scripts/smoke-compose-multinode.sh
