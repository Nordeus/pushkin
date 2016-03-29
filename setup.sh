#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

psql -U postgres -c "drop database if exists pushkin"
psql -U postgres -c "drop user if exists pushkin"
psql -U postgres -c "create database pushkin"
psql -U postgres -c "create user pushkin with password 'pushkin'"
psql -U postgres -c "alter database pushkin owner to pushkin"
psql -U postgres -d pushkin -c "CREATE EXTENSION HSTORE"

bash $SCRIPT_DIR/pushkin/database/db_create.sh