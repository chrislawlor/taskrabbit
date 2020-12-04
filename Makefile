.PHONY: tasks

build:
	DOCKER_BUILDKIT=1 \
	docker build -t taskrabbit .

run: clear-messages tasks drain fill worker

clear-messages:
	rm -rf messages/*

tasks:
	docker-compose up tasks

shell:
	docker-compose run --rm app bash

worker-shell:
	docker-compose run --rm worker bash

drain:
	docker-compose run --rm app python -m taskrabbit -q arithmetic drain

fill:
	docker-compose run --rm app python -m taskrabbit -x tasks fill

list:
	docker-compose run --rm app python -m taskrabbit list -c

worker:
	docker-compose up worker
