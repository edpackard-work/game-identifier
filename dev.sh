#!/bin/sh
# Run development Docker Compose with hot reload for both backend and frontend

docker-compose -f docker-compose.dev.yml "$@" 