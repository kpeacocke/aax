#!/bin/bash
set -e

# Entrypoint script for Ansible Execution Environment
# Allows flexible container usage for running Ansible commands

# If no command provided, start an interactive shell
if [ $# -eq 0 ]; then
    exec /bin/bash
fi

# Execute the provided command
exec "$@"
