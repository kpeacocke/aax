# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Map inventory project and artifact paths inside the serialized AWX worker.
- Keep project and template pages usable when the devel API rejects the pinned
  UI's optional legacy notification-role probe, without changing API permissions.
- Validate the mDNS exporter, Avahi, reflected VLANs and explicit container health
  after maintenance, using the inventory address for network checks.

### Added

- Initial release of AAX
