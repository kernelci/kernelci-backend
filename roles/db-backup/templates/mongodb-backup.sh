#!/bin/bash

MONGODUMP_PATH=`which mongodump`
TIMESTAMP=`date --utc +%FT%TZ`

echo "Dumping mongodb database..."
$MONGODUMP_PATH --quiet --gzip -d kernel-ci -o /tmp/mongodump > /dev/null

echo "Creating compressed archive..."
mv /tmp/mongodump /tmp/mongodump-$TIMESTAMP
tar cfP /tmp/mongodump-$TIMESTAMP.tar /tmp/mongodump-$TIMESTAMP/
xz -6 /tmp/mongodump-$TIMESTAMP.tar && rm -rf /tmp/mongodump-$TIMESTAMP/
