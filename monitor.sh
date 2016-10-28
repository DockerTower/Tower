#!/bin/bash
while true; do

inotifywait -e modify,create,delete -r $(pwd)/src && \
docker rmi -f tower:latest && docker build -f Dockerfile -t tower:latest .

done
