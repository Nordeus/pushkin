#!/bin/bash

psql -U postgres -c "DROP DATABASE IF EXISTS pushkin"
psql -U postgres -c "CREATE DATABASE pushkin"
psql -U postgres -c "ALTER DATABASE pushkin OWNER TO pushkin"
psql -U postgres -d pushkin -c "CREATE EXTENSION HSTORE"
