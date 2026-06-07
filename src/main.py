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
import argparse
import sys
from pathlib import Path

from .AkizipApplication import AkizipApplication
from .job_queue import JobQueue
from .plugins import register_plugins
from .plugins.system import sysop


def _cli_extract(args):
    from .plugins.sevenzip import archive_extract

    archive_path = Path(args.archive)
    if not archive_path.exists():
        print(f'Error: archive not found: {archive_path}', file=sys.stderr)
        return 1

    dest = Path(args.dest) if args.dest else archive_path.parent

    # Determine whether to create subfolder
    # args.smart: True=smart, False=always, None=default(always)
    if args.smart is True:
        from .plugins.sevenzip import archive_list
        output = archive_list(str(archive_path))
        top_level = set()
        for line in output.splitlines():
            parts = line.split('\t')
            if len(parts) >= 2:
                path = parts[1].replace('\\', '/').split('/')[0]
                if path:
                    top_level.add(path)
        create_subfolder = len(top_level) > 1
    else:
        create_subfolder = True

    if create_subfolder:
        dest = dest / archive_path.stem

    try:
        archive_extract(str(archive_path), str(dest))
        print(f'Extracted to {dest}')
        return 0
    except Exception as e:
        print(f'Extract failed: {e}', file=sys.stderr)
        return 1


def _cli_compress(args):
    from .plugins.sevenzip import archive_compress_advance

    if not args.files:
        print('Error: no input files specified', file=sys.stderr)
        return 1

    source_paths = [Path(f) for f in args.files if Path(f).exists()]
    if not source_paths:
        print('Error: no valid input files', file=sys.stderr)
        return 1

    if args.output:
        output = Path(args.output)
    else:
        base = source_paths[0].stem
        output = Path(f'{base}.{args.format}')

    compress_args = {
        'format': args.format,
        'level': str(args.level),
        'method': args.method,
    }

    try:
        archive_compress_advance(str(output), [(str(p), '') for p in source_paths], compress_args)
        print(f'Compressed to {output}')
        return 0
    except Exception as e:
        print(f'Compress failed: {e}', file=sys.stderr)
        return 1


def _build_extract_parser(subparsers):
    p = subparsers.add_parser('extract', help='Extract an archive')
    p.add_argument('archive', help='Path to the archive file')
    p.add_argument('dest', nargs='?', help='Destination directory (default: archive directory)')
    p.add_argument('--dialog', action='store_true', default=None, dest='dialog')
    p.add_argument('--no-dialog', action='store_false', dest='dialog')
    p.add_argument('--progress', action='store_true', default=None, dest='progress')
    p.add_argument('--no-progress', action='store_false', dest='progress')
    p.add_argument('--smart', action='store_true', default=None, dest='smart')
    p.add_argument('--no-smart', action='store_false', dest='smart')
    p.set_defaults(func='extract')
    return p


def _build_compress_parser(subparsers):
    p = subparsers.add_parser('compress', help='Compress files')
    p.add_argument('files', nargs='+', help='Files to compress')
    p.add_argument('--silent', action='store_true', help='Compress without GUI')
    p.add_argument('--format', default='7z', choices=('7z', 'zip', 'tar'),
                   help='Archive format (default: 7z)')
    p.add_argument('--level', type=int, default=5, choices=range(0, 10),
                   help='Compression level 0-9 (default: 5)')
    p.add_argument('--method', default='default', help='Compression method')
    p.add_argument('--output', help='Output archive path')
    p.set_defaults(func='compress')
    return p


def main(version):
    """The application's entry point."""
    # Pre-parse for subcommands to handle silent mode early
    if len(sys.argv) > 1 and sys.argv[1] in ('extract', 'compress'):
        parser = argparse.ArgumentParser(prog='akizip')
        subparsers = parser.add_subparsers(dest='command')
        _build_extract_parser(subparsers)
        _build_compress_parser(subparsers)

        parsed, remaining = parser.parse_known_args(sys.argv[1:])

        if parsed.command == 'extract':
            show_dialog = parsed.dialog if parsed.dialog is not None else False
            show_progress = parsed.progress if parsed.progress is not None else True
            if not show_dialog and not show_progress:
                return _cli_extract(parsed)
            # GUI mode: set pending action on app
            app = AkizipApplication()
            app.commands = {}
            app.job_queue = JobQueue(default_timeout=app.settings.get_int('default-timeout'))
            app.system = sysop()
            register_plugins(app.commands)
            app.job_queue.start()
            app._cli_pending_action = ('extract', parsed)
            try:
                return app.run([sys.argv[0], parsed.archive])
            finally:
                app.job_queue.stop()

        elif parsed.command == 'compress':
            if parsed.silent:
                return _cli_compress(parsed)
            # GUI mode
            app = AkizipApplication()
            app.commands = {}
            app.job_queue = JobQueue(default_timeout=app.settings.get_int('default-timeout'))
            app.system = sysop()
            register_plugins(app.commands)
            app.job_queue.start()
            app._cli_pending_action = ('compress', parsed)
            try:
                return app.run(sys.argv[:1] + parsed.files)
            finally:
                app.job_queue.stop()

    # Normal GUI flow (no subcommand, just open archive or empty window)
    app = AkizipApplication()
    app.commands = {}
    app.job_queue = JobQueue(default_timeout=app.settings.get_int('default-timeout'))
    app.system = sysop()
    register_plugins(app.commands)
    app.job_queue.start()

    try:
        return app.run(sys.argv)
    finally:
        app.job_queue.stop()
