#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

psql -U pushkin -f $SCRIPT_DIR/db_create.sql
