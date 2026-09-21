#!/bin/bash
# push.sh <base-url> <token>   — upload web/ to the running server
set -eu
BASE="$1"; TOK="$2"
cd "$(dirname "$0")/web"
n=0
while IFS= read -r -d '' f; do
  rel="${f#./}"
  code=$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -X PUT \
    -H "x-upload-token: $TOK" --data-binary "@$rel" "$BASE/__upload/$rel")
  echo "$code  $rel"
  [ "$code" = "200" ] || exit 1
  n=$((n+1))
done < <(find . -type f -print0)
echo "uploaded $n files"
