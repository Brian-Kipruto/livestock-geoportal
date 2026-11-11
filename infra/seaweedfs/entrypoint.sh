#!/bin/sh
# SeaweedFS all-in-one with an S3 gateway (ADR-009). Credentials come from the environment.
set -eu
cat > /tmp/s3.json <<JSON
{"identities":[{"name":"geoportal","credentials":[{"accessKey":"${S3_ACCESS_KEY}","secretKey":"${S3_SECRET_KEY}"}],"actions":["Admin","Read","Write","List","Tagging"]}]}
JSON
# volume.max=0: size the volume-slot limit from free disk (the default of 8 runs out once a
# few buckets each grow their 7 volumes).
exec weed server -dir=/data -s3 -s3.port=8333 -s3.config=/tmp/s3.json \
  -master.volumeSizeLimitMB=1024 -volume.max=0
