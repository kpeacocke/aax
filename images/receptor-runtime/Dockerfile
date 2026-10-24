ARG BASE_IMAGE=receptor:upstream
FROM golang:1.27.3-bookworm AS builder
WORKDIR /source
COPY . .
RUN go get github.com/klauspost/compress@v1.18.7 \
    golang.org/x/crypto@v0.57.0 golang.org/x/net@v0.60.0 golang.org/x/text@v0.42.0 && \
    go mod tidy && \
    go test -timeout 120s ./pkg/utils ./pkg/framer ./pkg/certificates
ARG VERSION=1.6.9.dev1
RUN make VERSION="${VERSION}" receptor

# hadolint ignore=DL3006
FROM ${BASE_IMAGE}
COPY --from=builder /source/receptor /usr/bin/receptor
