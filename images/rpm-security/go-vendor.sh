#!/usr/bin/env bash
set -euo pipefail
pins="${1:?A dependency pin manifest is required}"
archive="${2:?A corresponding-source archive is required}"
test -f go.mod
if [[ -s "$archive" ]]; then
    # Only the package's old vendored tree is replaced during an SRPM rebuild.
    rm -rf -- vendor
    tar -xzf "$archive" --no-same-owner
else
    modules="$(go list -mod=mod -m -json all | jq -s '.')"
    entries="$(jq -er 'to_entries[] | [.key, .value] | @tsv' "$pins")"
    updates=()
    while IFS=$'\t' read -r name target; do
        current="$(jq -r --arg name "$name" \
            '.[] | select(.Path == $name) | .Version' <<< "$modules")"
        [[ -n "$current" ]] || continue
        lowest="$(printf '%s\n%s\n' "$current" "$target" | sort -V | head -n 1)"
        if [[ "$lowest" != "$current" ]]; then
            echo "Refusing to downgrade Go dependency $name from $current to $target" >&2
            exit 1
        fi
        updates+=("$name@$target")
    done <<< "$entries"
    if (( ${#updates[@]} )); then
        GOFLAGS=-mod=mod go get "${updates[@]}"
    fi
    go mod tidy
    go mod download all
    go mod vendor
    tar -czf "$archive" go.mod go.sum vendor
fi
