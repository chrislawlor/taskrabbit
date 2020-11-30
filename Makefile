.PHONY: tasks

run: clear-messages tasks drain fill worker

build:
	DOCKER_BUILDKIT=1 \
	docker build -t message_drain .

clear-messages:
	rm -rf messages/*

tasks:
	docker-compose up tasks

shell:
	docker-compose run --rm app bash

worker-shell:
	docker-compose run --rm worker bash

drain:
	docker-compose run --rm app python message_drain.py drain --limit 10

fill:
	docker-compose run --rm app python message_drain.py fill

list:
	docker-compose run --rm app python message_drain.py list

worker:
	docker-compose up worker
