ARG BASE_IMAGE=aax/rpm-builder:bootstrap
# hadolint ignore=DL3006
FROM ${BASE_IMAGE} AS compiler
ARG GO_REVISION=2aae1000ea1d4b28923b96db28acf4e3b99d6aff
ARG FIPS_REVISION=dda0e0e2dfc2e6dac07c7111c0bba833704da73f
RUN mkdir -p /source/go /source/fips && \
    git -C /source/go init && \
    git -C /source/go remote add origin https://github.com/golang/go.git && \
    git -C /source/go fetch --depth 1 origin refs/tags/go1.27.3:refs/tags/go1.27.3 && \
    git -C /source/go checkout --detach "${GO_REVISION}" && \
    git -C /source/fips init && \
    git -C /source/fips remote add origin https://github.com/golang-fips/go.git && \
    git -C /source/fips fetch --depth 1 origin "${FIPS_REVISION}" && \
    git -C /source/fips checkout --detach "${FIPS_REVISION}" && \
    for patch in /source/fips/patches/*.patch; do git -C /source/go apply "$patch"; done && \
    ln -s ../go /source/fips/go
ENV GOROOT_BOOTSTRAP=/opt/aax-go GOROOT=/source/go GOTOOLCHAIN=local GOMAXPROCS=2
WORKDIR /source/go/src
RUN ./make.bash && /source/go/bin/go version
FROM compiler AS builder
WORKDIR /source
RUN bash /source/fips/scripts/crypto-test.sh --mode non-fips && \
    /source/go/bin/go test go/build internal/goexperiment
RUN bash /source/fips/scripts/crypto-test.sh \
      --mode native-fips-auto,native-fips-latest,native-fips-strict,purego,cmd/go && \
    jq -n --arg go "${GO_REVISION}" --arg fips "${FIPS_REVISION}" \
      '{go_revision: $go, fips_revision: $fips}' > /source/provenance.json
FROM scratch
COPY --from=builder /source/go /go
COPY --from=builder /source/fips /fips
COPY --from=builder /source/provenance.json /provenance.json
