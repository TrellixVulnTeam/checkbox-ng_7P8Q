# This file is part of Checkbox.
#
# Copyright 2012, 2013 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
#
# Checkbox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Checkbox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Checkbox.  If not, see <http://www.gnu.org/licenses/>.

"""
:mod:`checkbox_ng.main` -- command line interface
=================================================
"""

import logging
import sys

from plainbox.impl.commands import PlainBoxToolBase
from plainbox.impl.commands.check_config import CheckConfigCommand
from plainbox.impl.commands.dev import DevCommand
from plainbox.impl.commands.script import ScriptCommand

from checkbox_ng import __version__ as version
from checkbox_ng.commands.cli import CliCommand
from checkbox_ng.commands.sru import SRUCommand
try:
    from checkbox_ng.commands.service import ServiceCommand
except ImportError:
    pass
from checkbox_ng.config import CertificationConfig, CheckBoxConfig


logger = logging.getLogger("checkbox.ng.main")


class CheckBoxNGTool(PlainBoxToolBase):

    @classmethod
    def get_exec_name(cls):
        return "checkbox"

    @classmethod
    def get_exec_version(cls):
        return "{}.{}.{}".format(*version[:3])

    @classmethod
    def get_config_cls(cls):
        return CheckBoxConfig

    def add_subcommands(self, subparsers):
        SRUCommand(
            self._provider_list, self._config).register_parser(subparsers)
        CheckConfigCommand(
            self._config).register_parser(subparsers)
        ScriptCommand(
            self._provider_list, self._config).register_parser(subparsers)
        DevCommand(
            self._provider_list, self._config).register_parser(subparsers)
        CliCommand(
            self._provider_list, self._config, 'default').register_parser(
            subparsers, 'checkbox-cli')
        CliCommand(
            self._provider_list, self._config, 'server-cert').register_parser(
            subparsers, 'certification-server')
        CliCommand(
            self._provider_list, self._config, 'ihv-firmware').register_parser(
            subparsers, 'driver-test-suite-cli')
        try:
            ServiceCommand(self._provider_list, self._config).register_parser(
                subparsers)
        except NameError:
            pass


class CertificationNGTool(CheckBoxNGTool):

    @classmethod
    def get_config_cls(cls):
        return CertificationConfig


def main(argv=None):
    """
    checkbox command line utility
    """
    raise SystemExit(CheckBoxNGTool().main(argv))


def checkbox_cli(argv=None):
    """
    CheckBox command line utility
    """
    if argv:
        args = argv
    else:
        args = sys.argv[1:]
    raise SystemExit(
        CheckBoxNGTool().main(['checkbox-cli'] + args))


def cdts_cli(argv=None):
    """
    certification-server command line utility
    """
    if argv:
        args = argv
    else:
        args = sys.argv[1:]
    raise SystemExit(
        CheckBoxNGTool().main(['driver-test-suite-cli'] + args))


def cert_server(argv=None):
    """
    certification-server command line utility
    """
    if argv:
        args = argv
    else:
        args = sys.argv[1:]
    raise SystemExit(
        CertificationNGTool().main(['certification-server'] + args))
