"""Minimal terminal support for DrayTek switch CLIs."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re

from ansible_collections.ansible.netcommon.plugins.plugin_utils.terminal_base import TerminalBase


class TerminalModule(TerminalBase):
    """Recognise DrayTek prompts without making configuration changes."""

    terminal_stdout_re = [
        re.compile(rb"[\r\n]?[A-Za-z0-9_.:/()\- ]+[>#]\s?$"),
    ]
    terminal_stderr_re = [
        re.compile(rb"(?:invalid|unknown|unsupported|ambiguous)\s+(?:input|command)", re.I),
        re.compile(rb"(?:error|failed):", re.I),
    ]
