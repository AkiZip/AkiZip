# main.py
#
# Copyright 2026 akizip
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
import sys
from .AkizipApplication import AkizipApplication
from .job_queue import JobQueue
from .plugins import register_plugins
from .plugins.system import sysop


def main(version):
    """The application's entry point."""
    app = AkizipApplication()
    app.commands = {}
    app.job_queue = JobQueue(default_timeout=app.settings.get_int('default-timeout'))
    app.system = sysop()
    register_plugins(app.commands)
    scan_threads = app.settings.get_int('experimental-scan-threads')
    for name in ('system.set_scan_threads', 'archive.set_scan_threads'):
        command = app.commands.get(name)
        if command is not None:
            command(scan_threads)
    app.job_queue.start()

    try:
        return app.run(sys.argv)
    finally:
        app.job_queue.stop()
