# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.0.0 (2026-04-08)


### Features

* add .dockerignore, update Dockerfile with additional labels and dependencies, and bump ansible-core version to 2.20.0 ([7765bc0](https://github.com/kpeacocke/aax/commit/7765bc071be57ed14b58ce9df7f08b0671644aea))
* add CI/CD workflow documentation and update README with testing details ([14d77dd](https://github.com/kpeacocke/aax/commit/14d77dd47356b9df817cb096e9286d6a20626d47))
* add CODEOWNERS, Dependabot, and VSCode settings for improved project management ([5e44dbd](https://github.com/kpeacocke/aax/commit/5e44dbda7aeab2b6f9ab42b0bf2b778d61fedb99))
* add dev-tools image and related tests to CI/CD workflows ([6d57a28](https://github.com/kpeacocke/aax/commit/6d57a28711e365af2d2abfc0e4f2ce88512ce4fe))
* add Docker Compose support for local development and testing ([a22018f](https://github.com/kpeacocke/aax/commit/a22018fdf319f84eb31bd2e8c68821124dc06118))
* add Docker group access for vscode user and update pre-commit hook configuration ([040625c](https://github.com/kpeacocke/aax/commit/040625cb20fd857ea962ac7f161ca2e913094c04))
* add Dockerfile and devcontainer configuration for improved development environment ([9c9049b](https://github.com/kpeacocke/aax/commit/9c9049bd1ab9691a88ab7f58d2e01647826ce50b))
* add Dockerfile and requirements for Ansible development tools with health check ([97a407b](https://github.com/kpeacocke/aax/commit/97a407b241f7eb2fcb00d5b7ac6746910d91fd92))
* add Dockerfile and requirements for ansible-builder with health check ([510f2d2](https://github.com/kpeacocke/aax/commit/510f2d2c484e3ef04cc2cc8aaedebd0fe08036e7))
* add Dockerfile and requirements for ansible-core environment setup ([c3f049f](https://github.com/kpeacocke/aax/commit/c3f049f434a095c91f3567e747b72d32b313f1fb))
* add Dockerfile for ee-builder image with ansible-builder installation ([cf8444b](https://github.com/kpeacocke/aax/commit/cf8444b14ebd2fda9f59adc519cc706a979f909b))
* add entrypoint script for flexible Ansible command execution and update Dockerfile to include it ([efc5910](https://github.com/kpeacocke/aax/commit/efc5910decc45b5273b5d5640e770ea70aa73ba0))
* add instructions for building custom Ansible Execution Environment images and using ansible-builder ([8a52f46](https://github.com/kpeacocke/aax/commit/8a52f46ad14ac8d70d320eab113b48a7a0053142))
* add issue templates for bug reports, feature requests, and documentation issues ([4f7fad3](https://github.com/kpeacocke/aax/commit/4f7fad38416be23726c2fd47173a67a85bc7bb08))
* add Makefile for convenient development tasks and Docker management ([f0ea237](https://github.com/kpeacocke/aax/commit/f0ea23766317013ab26d09797cf26814983b4353))
* add Makefile Tools configuration for enhanced build management ([38e3603](https://github.com/kpeacocke/aax/commit/38e3603596a2fb5adfb033d123b4e7d14d30a5e7))
* Add Private Automation Hub with Galaxy NG and Pulp ([2d8ff94](https://github.com/kpeacocke/aax/commit/2d8ff94dcb5c83d063c9715ba4f6f65ce31e9a0f))
* add pull_policy: build to all build services for Portainer/standalone Docker compatibility ([#11](https://github.com/kpeacocke/aax/issues/11)) ([3741156](https://github.com/kpeacocke/aax/commit/37411560b7899184e62a1a4926de200ca85541f0))
* add pytest configuration and tests for AAX Docker images ([ffa8b39](https://github.com/kpeacocke/aax/commit/ffa8b39da30c305a61bd18729923568fc44ab584))
* add support for ee-builder image in CI workflows and tests ([764fc7b](https://github.com/kpeacocke/aax/commit/764fc7b981742b3c874b4cc6285d9fac8b875c02))
* Implement AWX controller stack with Docker Compose and build from source ([0d3b206](https://github.com/kpeacocke/aax/commit/0d3b206cf44282b119087c91aa1731da0b204946))
* **k8s:** Add Kubernetes deployment manifests and related configurations ([5c95278](https://github.com/kpeacocke/aax/commit/5c95278ab92768f28e1857dabea3e0c91cd9ff21))
* **k8s:** use same AWX nginx pattern as compose ([09cf914](https://github.com/kpeacocke/aax/commit/09cf914711b60116224e398ea7829505d7d14388))
* update Dockerfile and release workflow for improved development environment and caching ([2c71114](https://github.com/kpeacocke/aax/commit/2c7111436657ad53bcba33b7f570b1032e7f8678))
* update Dockerfile with additional labels, add ansible.cfg for configuration, and bump ansible-runner version to 2.4.2 ([ce4dbb9](https://github.com/kpeacocke/aax/commit/ce4dbb9942d7f081035a9e70f2242792f6121431))
* update issue templates and add GitHub workflows for release automation and branch name enforcement ([b729cff](https://github.com/kpeacocke/aax/commit/b729cffdff69475cb9840ac4cc74ee778665fb45))
* update VSCode configuration and add Makefile tasks for building and testing ee-base image ([a79a6f0](https://github.com/kpeacocke/aax/commit/a79a6f0af347517024944d84fa1677327cf413d0))


### Bug Fixes

* clean up devcontainer.json by removing unnecessary blank lines and ensuring proper environment variable configuration ([3b0f173](https://github.com/kpeacocke/aax/commit/3b0f173d5908e7f00f1d44514925e5e0b29a62ed))
* clean up SECURITY.md for consistency ([c3f049f](https://github.com/kpeacocke/aax/commit/c3f049f434a095c91f3567e747b72d32b313f1fb))
* Complete audit items and fix test hangs ([9f7ce0a](https://github.com/kpeacocke/aax/commit/9f7ce0a3e46e6001d1091ac48108a37578fe7584))
* compose profile defaults, AWX startup race conditions, and entrypoint fixes ([#22](https://github.com/kpeacocke/aax/issues/22)) ([0802845](https://github.com/kpeacocke/aax/commit/0802845de5c8968ce69a7da43cc829e3a9636467))
* **controller:** align AWX ports with official image and stabilize task startup ([1dab2be](https://github.com/kpeacocke/aax/commit/1dab2beff03f1b10a8813bbb9e8aaa885d271acd))
* **controller:** extend AWX healthcheck grace period on slow NAS ([8d0a9f4](https://github.com/kpeacocke/aax/commit/8d0a9f435e2480f769a50a30084284e486c49b78))
* **controller:** inject AWX nginx config so uWSGI proxy actually works ([07938c0](https://github.com/kpeacocke/aax/commit/07938c0b8cce850662e33e4bcd261c8f19373c09))
* **controller:** provision awx instance before dispatcher start ([0b24915](https://github.com/kpeacocke/aax/commit/0b2491564da31b9b9ecb3c1bfa15415bc66cbb86))
* **eda:** simplify healthcheck to process-alive check ([2c36b60](https://github.com/kpeacocke/aax/commit/2c36b6082f5fb5e6e12cf019af74c57178fefee0))
* **gateway:** allow CHOWN capability for nginx temp dir init ([67d2d74](https://github.com/kpeacocke/aax/commit/67d2d744b11eb68b54a4964ffe51724ddb2edc55))
* **gateway:** allow nginx setgid/setuid worker drop ([a6bfce4](https://github.com/kpeacocke/aax/commit/a6bfce454979ad9878c8e6be370fe9fc570df691))
* **hub:** add restart policies and finite Pulp API poll timeout ([0cef16a](https://github.com/kpeacocke/aax/commit/0cef16a7ea286ac4204a564820422ebc240b98e5))
* **images:** use available receptor tag ([3850679](https://github.com/kpeacocke/aax/commit/385067989762a7f6e40ab4a537f04c4a7cfb206f))
* **portainer:** hardcode receptor image in compose services ([5ab5e97](https://github.com/kpeacocke/aax/commit/5ab5e97579ac6571630a81476d62d12fbe94a7a9))
* **portainer:** remove AWX nginx bind-mount dependency ([2a15910](https://github.com/kpeacocke/aax/commit/2a159106b04a4eb9661e54a97ccf5d60daaff992))
* remove duplicate ansible network definition ([#6](https://github.com/kpeacocke/aax/issues/6)) ([f92805a](https://github.com/kpeacocke/aax/commit/f92805ad4361c0b6ce0c0b37ae97b0508e5d596d))
* remove exclusion for .devcontainer and .pre-commit-config.yaml in check-executables-have-shebangs hook ([d262b56](https://github.com/kpeacocke/aax/commit/d262b56826e53c8b058fc85a548a812775368854))
* remove unnecessary blank lines in VSCode configuration files ([b578433](https://github.com/kpeacocke/aax/commit/b57843341a6998863a3e6ca78c4c03dae8e6bd52))
* resolve security code scanning alerts ([#10](https://github.com/kpeacocke/aax/issues/10)) ([c5f1bfa](https://github.com/kpeacocke/aax/commit/c5f1bfae70016b95bc506aef46cb46fff0a52689))
* update pre-commit configuration for secrets detection and baseline ([c3f049f](https://github.com/kpeacocke/aax/commit/c3f049f434a095c91f3567e747b72d32b313f1fb))
* update spell checker dictionary with additional words ([f177d99](https://github.com/kpeacocke/aax/commit/f177d99d6b14ab1e8549990c69d85e64bb68ca02))
* upgrade ansible-lint to 25.12.1 for Python 3.14 compatibility ([5669867](https://github.com/kpeacocke/aax/commit/5669867d55d90682a67f438a394057ee9010fb85))
* **validation:** resolve full-suite regressions and pin receptor ([edcac1b](https://github.com/kpeacocke/aax/commit/edcac1b56c5703d086bd45fcddc8422590689db1))

## [Unreleased]

### Added

- Initial release of AAX
