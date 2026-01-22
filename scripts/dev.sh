#!/bin/bash
# Development docker-compose helper
# Always uses docker-compose.dev.yml for development

docker-compose -f docker-compose.dev.yml "$@"
