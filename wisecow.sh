#!/usr/bin/env bash

SRVPORT=4499

handleRequest() {
    local request header path body status

    IFS= read -r request || return 0
    request=${request%$'\r'}

    # Read remaining HTTP headers
    while IFS= read -r header; do
        header=${header%$'\r'}
        [[ -z "$header" ]] && break
    done

    echo "$request" >&2

    path=$(echo "$request" | cut -d ' ' -f 2)

    if [[ "$path" == "/healthz" ]]; then
        body="OK"
        status="200 OK"
    else
        body="<pre>$(fortune | cowsay)</pre>"
        status="200 OK"
    fi

    # Return a properly formatted HTTP response
    printf 'HTTP/1.1 %s\r\n' "$status"
    printf 'Content-Type: text/html; charset=utf-8\r\n'
    printf 'Content-Length: %s\r\n' "$(printf '%s' "$body" | wc -c)"
    printf 'Connection: close\r\n'
    printf '\r\n'
    printf '%s' "$body"
}

if [[ "${1:-}" == "--handle-request" ]]; then
    handleRequest
    exit 0
fi

# Verify dependencies
for cmd in fortune cowsay socat; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "Missing dependency: $cmd" >&2
        exit 1
    }
done

echo "Wisdom served on port=$SRVPORT..."

exec socat \
    TCP-LISTEN:${SRVPORT},reuseaddr,fork,max-children=32 \
    EXEC:"bash /app/wisecow.sh --handle-request"
