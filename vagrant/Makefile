# if image name changed here it has to be updated in Vagrantfile
IMAGE=urb-build

.PHONY:all

all:
	docker images $(IMAGE) | grep $(IMAGE) >/dev/null 2>&1 || docker build --rm -t $(IMAGE) .

.PHONY:clean
clean:
	IM=$$(docker ps | awk '/$(IMAGE)/ {print $$$\1}'); if [ ! -z "$$IM" ]; then docker stop $$IM; fi
	IM=$$(docker ps -a| awk '/$(IMAGE)/ {print $$$\1}'); if [ ! -z "$$IM" ]; then docker rm $$IM; fi
	-docker rmi $(IMAGE)

