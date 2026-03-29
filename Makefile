.PHONY: test test-unit test-integration test-coverage run deploy

test:
	pytest

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-coverage:
	pytest --cov=services --cov-report=term-missing

run:
	python3 -m flask --app services.backend.app run --port 8080

deploy:
	./infra/deploy.sh
