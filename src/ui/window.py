# window.py
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

from pathlib import Path

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk
from ..plugins.status import _status
from .info_dialog import InfoDialogMixin
from .log_panel import LogPanelMixin

@Gtk.Template(resource_path='/top/akizip/akizip/window.ui')
class AkizipWindow(LogPanelMixin, InfoDialogMixin, Adw.ApplicationWindow):
    __gtype_name__ = 'AkizipWindow'

    add_button = Gtk.Template.Child()
    choose_button = Gtk.Template.Child()
    choose_destination_button = Gtk.Template.Child()
    choose_folder_button = Gtk.Template.Child()
    destination_entry = Gtk.Template.Child()
    extract_button = Gtk.Template.Child()
    file_entry = Gtk.Template.Child()
    info_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def butadd(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return
        destination = self._destination_path_from_input()
        if destination is None:
            return
        self._run_command('archive.compress', destination / f'{selected.name}.7z', [selected])

    @Gtk.Template.Callback()
    def butinfo(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return
        self._show_info_dialog(selected)

    @Gtk.Template.Callback()
    def butextract(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return

        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.can_extract():
            self._append_log(_('Extract failed'), _('Selected path is not an archive.'), _status.ERROR)
            return

        destination = self._destination_path_from_input()
        if destination is None:
            return
        self._run_command('archive.extract', selected, destination / selected.stem)

    @Gtk.Template.Callback()
    def butmove(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return
        destination = self._destination_path_from_input()
        if destination is None:
            return
        self._run_command('system.move', selected, destination)

    @Gtk.Template.Callback()
    def on_file_entry_activate(self, entry):
        self._selected_path_from_input()

    @Gtk.Template.Callback()
    def on_destination_entry_activate(self, entry):
        self._destination_path_from_input()

    @Gtk.Template.Callback()
    def on_choose_file(self, button):
        dialog = Gtk.FileChooserNative.new(
            _('Select File'),
            self,
            Gtk.FileChooserAction.OPEN,
            _('_Open'),
            _('_Cancel'),
        )
        dialog.connect('response', self._on_choose_file_response)
        dialog.show()

    @Gtk.Template.Callback()
    def on_choose_folder(self, button):
        dialog = Gtk.FileChooserNative.new(
            _('Select Folder'),
            self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            _('_Open'),
            _('_Cancel'),
        )
        dialog.connect('response', self._on_choose_file_response)
        dialog.show()

    @Gtk.Template.Callback()
    def on_choose_destination(self, button):
        dialog = Gtk.FileChooserNative.new(
            _('Select Destination Folder'),
            self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            _('_Open'),
            _('_Cancel'),
        )
        dialog.connect('response', self._on_choose_destination_response)
        dialog.show()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pending_handles = {}
        self._pending_logs = {}

        app = self.get_application()
        if app is not None and hasattr(app, 'settings'):
            self._initial_language = app.settings.get_string('language')
            app.settings.connect('changed::language', self._on_language_changed)

        if app is not None and hasattr(app, 'system'):
            self.file_entry.set_text(app.system.selected_path())
            self.destination_entry.set_text(app.system.destination_path())

    def _on_choose_file_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file is not None:
                path = file.get_path()
                display_path = file.get_parse_name()
                if path is not None:
                    self.file_entry.set_text(display_path or path)
                    self._select_path(path, display_path)
        dialog.destroy()

    def _on_choose_destination_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file is not None:
                path = file.get_path()
                display_path = file.get_parse_name()
                if path is not None:
                    self.destination_entry.set_text(display_path or path)
                    self._select_destination(path, display_path)
        dialog.destroy()

    def _selected_path_from_input(self):
        path = self.file_entry.get_text().strip()
        if not path:
            self._append_log(_('No file selected'), None, _status.ERROR)
            return None

        app = self.get_application()
        if app is not None and hasattr(app, 'system'):
            if app.system.has_selected() and path == app.system.selected_path():
                return Path(app.system.operation_path())

        if not self._select_path(path):
            return None
        return Path(path).expanduser()

    def _destination_path_from_input(self):
        path = self.destination_entry.get_text().strip()
        if not path:
            self._append_log(_('No destination selected'), None, _status.ERROR)
            return None

        app = self.get_application()
        if app is not None and hasattr(app, 'system'):
            if app.system.has_destination() and path == app.system.destination_path():
                return Path(app.system.destination_operation_path())

        if not self._select_destination(path):
            return None
        return Path(path).expanduser()

    def _select_path(self, path, display_path=None):
        app = self.get_application()
        if app is None or not hasattr(app, 'system'):
            self._append_log(_('System state not found'), str(path), _status.ERROR)
            return False

        if display_path is None:
            app.system.select_by_input(path)
        else:
            app.system.select_by_fileview(path, display_path)
        info = app.system.info()
        if not info['success']:
            self._append_log(_('Select failed'), info['msg'], _status.ERROR)
            return False

        self._append_log(_('Selected ') + info['name'], info['path'], _status.FINISHED)
        return True

    def _select_destination(self, path, display_path=None):
        app = self.get_application()
        if app is None or not hasattr(app, 'system'):
            self._append_log(_('System state not found'), str(path), _status.ERROR)
            return False

        if display_path is None:
            app.system.select_destination_by_input(path)
        else:
            app.system.select_destination_by_fileview(path, display_path)
        info = app.system.info()
        if not info['success']:
            self._append_log(_('Select destination failed'), info['msg'], _status.ERROR)
            return False

        destination = Path(info['destination_operation_path']).name
        self._append_log(_('Destination ') + destination, info['destination_path'], _status.FINISHED)
        return True

    def _on_language_changed(self, settings, key):
        if settings.get_string(key) == self._initial_language:
            return
        self._append_log(
            _('Language changed'),
            _('Restart the application to apply the new language.'),
        )

    def _run_command(self, name, *args):
        app = self.get_application()
        command = getattr(app, 'commands', {}).get(name)
        if command is None:
            self._append_log(_('Command not found'), name)
            return

        job_queue = getattr(app, 'job_queue', None)
        if job_queue is None:
            self._append_log(_('Job queue not found'), name)
            return

        log_id = object()
        summary = self._command_summary(name, args, _status.PENDING)
        handle = job_queue.submit(
            command,
            args,
            on_success=lambda output: self._on_command_success(log_id, name, args, output),
            on_error=lambda error: self._on_command_error(log_id, name, args, error),
            timeout=60,
            task_id=name,
            msg=summary,
            on_status=lambda task_status: self._on_command_status(log_id, name, args, task_status),
        )
        self._pending_handles[log_id] = handle
        self._pending_logs[log_id] = self._append_log(
            summary,
            self._command_preview(name, args),
            _status.PENDING,
            handle,
        )

    def _on_command_status(self, log_id, name, args, task_status):
        if task_status.status == _status.WORKING:
            handle = self._pending_handles.get(log_id)
            self._remove_pending_log(log_id)
            self._pending_handles[log_id] = handle
            self._pending_logs[log_id] = self._append_log(
                self._command_summary(name, args, _status.WORKING),
                self._command_preview(name, args),
                _status.WORKING,
                handle,
            )

        if task_status.status == _status.CANCELLED:
            self._remove_pending_log(log_id)
            self._append_log(
                self._command_summary(name, args, _status.CANCELLED),
                task_status.msg,
                _status.CANCELLED,
            )

    def _on_command_success(self, log_id, name, args, output):
        print(output)
        if not self._remove_pending_log(log_id):
            return
        if name == 'system.move' and len(args) > 1:
            self._update_moved_selection(args[0], args[1])
        self._append_log(self._command_summary(name, args, _status.FINISHED), output, _status.FINISHED)

    def _on_command_error(self, log_id, name, args, error):
        if not self._remove_pending_log(log_id):
            return
        state = _status.TIMEOUT if isinstance(error, TimeoutError) else _status.ERROR
        self._append_log(self._command_summary(name, args, state), str(error), state)

    def _command_summary(self, name, args, state):
        if name == 'archive.compress':
            source_paths = args[1] if len(args) > 1 else []
            if source_paths:
                target = Path(source_paths[0]).name
            else:
                target = Path(args[0]).name if args else _('file')

            if state == _status.PENDING:
                return _('Compress ') + target
            if state == _status.WORKING:
                return _('Compress ') + target
            if state == _status.FINISHED:
                return _('Compressed ') + target
            if state == _status.TIMEOUT:
                return _('Compress timed out: ') + target
            if state == _status.CANCELLED:
                return _('Compress cancelled: ') + target
            return _('Compress failed: ') + target

        if name == 'archive.info':
            target = Path(args[0]).name if args else _('archive')
            if state == _status.PENDING:
                return _('Open ') + target
            if state == _status.WORKING:
                return _('Open ') + target
            if state == _status.FINISHED:
                return _('Opened ') + target
            if state == _status.TIMEOUT:
                return _('Open timed out: ') + target
            if state == _status.CANCELLED:
                return _('Open cancelled: ') + target
            return _('Open failed: ') + target

        if name == 'archive.extract':
            target = Path(args[0]).name if args else _('archive')
            if state == _status.PENDING:
                return _('Extract ') + target
            if state == _status.WORKING:
                return _('Extract ') + target
            if state == _status.FINISHED:
                return _('Extracted ') + target
            if state == _status.TIMEOUT:
                return _('Extract timed out: ') + target
            if state == _status.CANCELLED:
                return _('Extract cancelled: ') + target
            return _('Extract failed: ') + target

        if name == 'system.move':
            target = Path(args[0]).name if args else _('file')
            if state == _status.PENDING:
                return _('Move ') + target
            if state == _status.WORKING:
                return _('Move ') + target
            if state == _status.FINISHED:
                return _('Moved ') + target
            if state == _status.TIMEOUT:
                return _('Move timed out: ') + target
            if state == _status.CANCELLED:
                return _('Move cancelled: ') + target
            return _('Move failed: ') + target

        return name

    def _command_preview(self, name, args):
        if name == 'archive.compress':
            output = Path(args[0]).name if args else _('archive')
            source_paths = args[1] if len(args) > 1 else []
            source = Path(source_paths[0]).name if source_paths else _('file')
            return _('Create ') + output + _(' from ') + source

        if name == 'archive.info':
            archive = Path(args[0]).name if args else _('archive')
            return _('Read archive information from ') + archive

        if name == 'archive.extract':
            archive = Path(args[0]).name if args else _('archive')
            output = Path(args[1]).name if len(args) > 1 else _('folder')
            return _('Extract ') + archive + _(' to ') + output

        if name == 'system.move':
            source = Path(args[0]).name if args else _('file')
            destination = Path(args[1]).name if len(args) > 1 else _('folder')
            return _('Move ') + source + _(' to ') + destination

        return name

    def _update_moved_selection(self, source, destination):
        app = self.get_application()
        if app is None or not hasattr(app, 'system'):
            return
        moved_path = Path(destination) / Path(source).name
        app.system.select_by_input(moved_path)
        if app.system.has_selected():
            self.file_entry.set_text(app.system.selected_path())
