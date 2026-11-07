.PHONY: up down logs test lint fmt shell
up:      ## start the dev stack
	docker compose up --build
down:
	docker compose down
logs:
	docker compose logs -f api worker
test:
	docker compose run --rm api pytest
lint:
	ruff check app tests && mypy app
fmt:
	ruff format app tests && ruff check --fix app tests
shell:
	docker compose exec api python
