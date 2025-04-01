#!/bin/bash

set -e
set -x

cd src

if [[ "${1}" == "celery" ]]; then
  celery --app=tasks.tasks:celery worker -l INFO
elif [[ "${1}" == "flower" ]]; then
  celery --app=tasks.tasks:celery flower
elif [[ "${1}" == "beat" ]]; then
  celery --app=tasks.tasks:celery beat -l info
 fi
