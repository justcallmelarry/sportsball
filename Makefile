build:
	docker build \
		--rm \
		--file=./Dockerfile \
		--tag=sportsball ./

run:
	docker run \
		-d \
		--rm \
		--name=sb \
		-e=TZ=Europe/Stockholm \
		sportsball

enter:
	docker exec \
		-it \
		sb \
		/bin/bash

stop:
	docker stop sb
