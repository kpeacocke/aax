"""Read-only Cliconf support for DrayTek switch CLIs."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible.errors import AnsibleConnectionFailure
from ansible_collections.ansible.netcommon.plugins.plugin_utils.cliconf_base import CliconfBase


class Cliconf(CliconfBase):
    """Expose generic command execution while refusing configuration methods."""

    def get_device_info(self):
        return {"network_os": "draytek"}

    def get_config(self, flags=None, format=None):
        raise AnsibleConnectionFailure("get_config is not implemented for DrayTek")

    def edit_config(self, candidate=None, commit=True, replace=None, comment=None):
        raise AnsibleConnectionFailure("edit_config is not implemented for DrayTek")

    def get_capabilities(self):
        result = super(Cliconf, self).get_capabilities()
        result["device_operations"] = self.get_device_operations()
        return json.dumps(result)

    def get_device_operations(self):
        return {
            "supports_diff_replace": False,
            "supports_commit": False,
            "supports_rollback": False,
            "supports_defaults": False,
            "supports_onbox_diff": False,
            "supports_commit_comment": False,
            "supports_multiline_delimiter": False,
            "supports_diff_match": False,
            "supports_diff_ignore_lines": False,
            "supports_generate_diff": False,
            "supports_replace": False,
        }
