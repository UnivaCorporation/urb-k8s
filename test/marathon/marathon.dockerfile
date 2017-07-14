FROM mesosphere/marathon

RUN apt-get update && apt-get install -y libev4 libuuid1 zlib1g && apt-get clean

EXPOSE 8080
