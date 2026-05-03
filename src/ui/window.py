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

import os
from pathlib import Path

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Pango
from ..plugins.status import _status
from .info_dialog import InfoDialogMixin
from .log_panel import LogPanelMixin


_HOST_PATH_XATTR = 'user.document-portal.host-path'
_IS_FLATPAK = os.path.exists('/.flatpak-info')


def _host_path(path):
    if not path:
        return ''
    try:
        value = os.getxattr(os.fsencode(str(path)), _HOST_PATH_XATTR)
    except OSError:
        return str(path)
    return os.fsdecode(value) or str(path)


class ArchiveEntry(GObject.Object):
    __gtype_name__ = 'AkizipArchiveEntry'

    path = GObject.Property(type=str, default='')
    size = GObject.Property(type=str, default='')
    modified = GObject.Property(type=str, default='')
    is_folder = GObject.Property(type=bool, default=False)
    full_path = GObject.Property(type=str, default='')

    def __init__(self, path='', size='', modified='', is_folder=False, full_path=''):
        super().__init__()
        self.path = path
        self.size = size
        self.modified = modified
        self.is_folder = is_folder
        self.full_path = full_path


def parse_archive_entries(output):
    entries = []
    for block in output.split('\n\n'):
        block = block.strip()
        if not block:
            continue
        entry = {}
        for line in block.splitlines():
            if ' = ' in line:
                key, value = line.split(' = ', 1)
                entry[key.strip()] = value.strip()
        if entry.get('Path'):
            entries.append(entry)
    return entries


@Gtk.Template(resource_path='/top/akizip/akizip/window.ui')
class AkizipWindow(LogPanelMixin, InfoDialogMixin, Adw.ApplicationWindow):
    __gtype_name__ = 'AkizipWindow'

    add_button = Gtk.Template.Child()
    choose_button = Gtk.Template.Child()
    extract_button = Gtk.Template.Child()
    info_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    address_entry = Gtk.Template.Child()
    file_list_stack = Gtk.Template.Child()
    file_list_scroller = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def butadd(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return
        self._present_compress_dialog(
            lambda dest: self._run_command(
                'archive.compress',
                dest / f'{selected.name}.7z',
                [selected],
            )
        )

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

        self._present_extract_dialog(
            lambda dest: self._run_command(
                'archive.extract',
                selected,
                dest / selected.stem,
            )
        )

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
    def on_address_activate(self, entry):
        text = entry.get_text().strip()
        if not text:
            return

        app = self.get_application()
        if (app is not None and hasattr(app, 'system')
                and app.system.is_archive() and self._all_entries):
            archive_path = app.system.selected_path()
            prefix = archive_path.rstrip('/') + '/'
            if text == archive_path or text == prefix:
                self._current_internal_path = ''
                self._render_current_folder()
                return
            if text.startswith(prefix):
                internal = text[len(prefix):].strip('/')
                if internal == '' or internal in self._folder_set:
                    self._current_internal_path = (internal + '/') if internal else ''
                    self._render_current_folder()
                    return

        path = str(Path(text).expanduser())
        if self._select_path(path):
            self._refresh_file_list()
            self._update_title()
            self._sync_address_bar()

    def _open_folder_chooser_for_entry(self, entry, on_picked=None):
        chooser = Gtk.FileChooserNative.new(
            _('Select Destination Folder'),
            self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            _('_Open'),
            _('_Cancel'),
        )

        def chooser_response(c, response):
            if response == Gtk.ResponseType.ACCEPT:
                file = c.get_file()
                if file is not None:
                    op = file.get_path()
                    if op is not None:
                        display = _host_path(op)
                        entry.set_text(display)
                        if on_picked is not None:
                            on_picked(display, op)
            c.destroy()

        chooser.connect('response', chooser_response)
        chooser.show()

    def _present_compress_dialog(self, on_chosen):
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        entry.set_placeholder_text(_('Destination folder'))
        entry.set_editable(not _IS_FLATPAK)

        browse_button = Gtk.Button()
        browse_button.set_icon_name('folder-symbolic')
        browse_button.set_tooltip_text(_('Select Destination Folder'))

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(entry)
        box.append(browse_button)

        dialog = Adw.AlertDialog.new(_('Compress'), None)
        dialog.set_extra_child(box)
        dialog.add_response('cancel', _('_Cancel'))
        dialog.add_response('confirm', _('Compress'))
        dialog.set_response_appearance('confirm', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('confirm')
        dialog.set_close_response('cancel')

        last = {'display': None, 'op': None}

        def on_picked(display, op):
            last['display'] = display
            last['op'] = op

        browse_button.connect('clicked',
            lambda _btn: self._open_folder_chooser_for_entry(entry, on_picked=on_picked))
        entry.connect('activate', lambda _e: dialog.response('confirm'))

        def on_response(_d, response):
            if response == 'confirm':
                text = entry.get_text().strip()
                if not text:
                    return
                if last['display'] == text and last['op']:
                    on_chosen(Path(last['op']))
                else:
                    on_chosen(Path(text).expanduser())

        dialog.connect('response', on_response)
        dialog.present(self)

    def _present_extract_dialog(self, on_chosen):
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        entry.set_placeholder_text(_('Destination folder'))
        entry.set_editable(not _IS_FLATPAK)

        browse_button = Gtk.Button()
        browse_button.set_icon_name('folder-symbolic')
        browse_button.set_tooltip_text(_('Select Destination Folder'))

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(entry)
        box.append(browse_button)

        dialog = Adw.AlertDialog.new(_('Extract'), None)
        dialog.set_extra_child(box)
        dialog.add_response('cancel', _('_Cancel'))
        dialog.add_response('confirm', _('Extract'))
        dialog.set_response_appearance('confirm', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('confirm')
        dialog.set_close_response('cancel')

        last = {'display': None, 'op': None}

        def on_picked(display, op):
            last['display'] = display
            last['op'] = op

        browse_button.connect('clicked',
            lambda _btn: self._open_folder_chooser_for_entry(entry, on_picked=on_picked))
        entry.connect('activate', lambda _e: dialog.response('confirm'))

        def on_response(_d, response):
            if response == 'confirm':
                text = entry.get_text().strip()
                if not text:
                    return
                if last['display'] == text and last['op']:
                    on_chosen(Path(last['op']))
                else:
                    on_chosen(Path(text).expanduser())

        dialog.connect('response', on_response)
        dialog.present(self)

    def _build_file_list(self):
        self._file_list_store = Gio.ListStore(item_type=ArchiveEntry)
        selection = Gtk.SingleSelection(model=self._file_list_store)
        view = Gtk.ColumnView(model=selection)
        view.set_show_row_separators(True)
        view.set_show_column_separators(False)
        view.connect('activate', self._on_row_activate)

        columns = (
            (_('Path'), self._on_path_setup, self._on_path_bind, True),
            (_('Size'), self._on_text_setup, self._on_size_bind, False),
            (_('Modified'), self._on_text_setup, self._on_modified_bind, False),
        )
        for title, setup, bind, expand in columns:
            factory = Gtk.SignalListItemFactory()
            factory.connect('setup', setup)
            factory.connect('bind', bind)
            column = Gtk.ColumnViewColumn(title=title, factory=factory)
            column.set_expand(expand)
            column.set_resizable(True)
            view.append_column(column)

        self.file_list_scroller.set_child(view)
        self._file_list_view = view

    def _on_path_setup(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        image = Gtk.Image()
        image.set_pixel_size(16)
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_hexpand(True)
        box.append(image)
        box.append(label)
        list_item.set_child(box)

    def _on_path_bind(self, factory, list_item):
        item = list_item.get_item()
        box = list_item.get_child()
        image = box.get_first_child()
        label = image.get_next_sibling()
        if item.path == '..':
            image.set_from_icon_name('go-up-symbolic')
        elif item.is_folder:
            image.set_from_icon_name('folder-symbolic')
        else:
            image.set_from_icon_name('text-x-generic-symbolic')
        label.set_text(item.path)

    def _on_text_setup(self, factory, list_item):
        label = Gtk.Label(xalign=0)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_margin_start(6)
        label.set_margin_end(6)
        label.set_margin_top(2)
        label.set_margin_bottom(2)
        list_item.set_child(label)

    def _on_size_bind(self, factory, list_item):
        list_item.get_child().set_text(list_item.get_item().size)

    def _on_modified_bind(self, factory, list_item):
        list_item.get_child().set_text(list_item.get_item().modified)

    def _on_row_activate(self, view, position):
        item = self._file_list_store.get_item(position)
        if item is None or not item.is_folder:
            return
        self._current_internal_path = item.full_path
        self._render_current_folder()

    def _refresh_file_list(self):
        self._all_entries = []
        self._folder_set = set()
        self._current_internal_path = ''
        self._file_list_store.remove_all()
        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.is_archive():
            self.file_list_stack.set_visible_child_name('empty')
            return

        selected = Path(app.system.operation_path())
        command = getattr(app, 'commands', {}).get('archive.list')
        job_queue = getattr(app, 'job_queue', None)
        if command is None or job_queue is None:
            self.file_list_stack.set_visible_child_name('empty')
            return

        self.file_list_stack.set_visible_child_name('loading')
        job_queue.submit(
            command,
            (selected,),
            on_success=lambda output: self._populate_file_list(output),
            on_error=lambda error: self._on_file_list_error(error),
            timeout=120,
            task_id='archive.list',
            msg=_('List ') + selected.name,
        )

    def _populate_file_list(self, output):
        self._all_entries = parse_archive_entries(output)
        self._folder_set = self._collect_folders(self._all_entries)
        self._current_internal_path = ''
        self._render_current_folder()

    def _collect_folders(self, entries):
        folders = set()
        for entry in entries:
            path = entry.get('Path', '').replace('\\', '/').rstrip('/')
            if not path:
                continue
            if 'D' in entry.get('Attributes', '') or entry.get('Folder') == '+':
                folders.add(path)
            parts = path.split('/')
            for i in range(1, len(parts)):
                folders.add('/'.join(parts[:i]))
        return folders

    def _parent_folder(self, internal_path):
        p = internal_path.rstrip('/')
        if '/' not in p:
            return ''
        return p.rsplit('/', 1)[0] + '/'

    def _build_rows_for_folder(self, folder):
        children = {}
        for entry in self._all_entries:
            path = entry.get('Path', '').replace('\\', '/').rstrip('/')
            if not path:
                continue
            if folder:
                if not path.startswith(folder):
                    continue
                rest = path[len(folder):]
            else:
                rest = path
            if not rest:
                continue
            seg, _, tail = rest.partition('/')
            if not seg:
                continue
            full = (folder + seg) if folder else seg
            is_folder_now = bool(tail) or full in self._folder_set
            if is_folder_now:
                child = children.setdefault(seg, {
                    'is_folder': True,
                    'size': '',
                    'modified': '',
                    'full_path': full + '/',
                })
                child['is_folder'] = True
                child['full_path'] = full + '/'
            else:
                if seg in children and children[seg]['is_folder']:
                    continue
                children[seg] = {
                    'is_folder': False,
                    'size': entry.get('Size', ''),
                    'modified': entry.get('Modified', ''),
                    'full_path': full,
                }

        rows = []
        for name in sorted(children, key=lambda n: (not children[n]['is_folder'], n.lower())):
            child = children[name]
            rows.append(ArchiveEntry(
                path=name + ('/' if child['is_folder'] else ''),
                size=child['size'],
                modified=child['modified'],
                is_folder=child['is_folder'],
                full_path=child['full_path'],
            ))
        return rows

    def _render_current_folder(self):
        self._file_list_store.remove_all()
        if self._current_internal_path:
            parent = self._parent_folder(self._current_internal_path)
            self._file_list_store.append(ArchiveEntry(
                path='..',
                is_folder=True,
                full_path=parent,
            ))
        for row in self._build_rows_for_folder(self._current_internal_path):
            self._file_list_store.append(row)
        if self._file_list_store.get_n_items() == 0:
            self.file_list_stack.set_visible_child_name('empty')
        else:
            self.file_list_stack.set_visible_child_name('list')
        self._sync_address_bar()
        self._update_title()

    def _on_file_list_error(self, error):
        self._all_entries = []
        self._folder_set = set()
        self._current_internal_path = ''
        self._append_log(_('List failed'), str(error), _status.ERROR)
        self.file_list_stack.set_visible_child_name('empty')

    def _sync_address_bar(self):
        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.has_selected():
            self.address_entry.set_text('')
            return
        text = app.system.selected_path()
        if app.system.is_archive() and self._current_internal_path:
            if not text.endswith('/'):
                text = text + '/'
            text = text + self._current_internal_path
        self.address_entry.set_text(text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pending_handles = {}
        self._pending_logs = {}
        self._all_entries = []
        self._folder_set = set()
        self._current_internal_path = ''

        app = self.get_application()
        if app is not None and hasattr(app, 'settings'):
            self._initial_language = app.settings.get_string('language')
            app.settings.connect('changed::language', self._on_language_changed)

        self._build_file_list()
        self.address_entry.set_editable(not _IS_FLATPAK)
        self.file_list_stack.set_visible_child_name('empty')
        self._sync_address_bar()
        self._update_title()

    def _on_choose_file_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file is not None:
                path = file.get_path()
                if path is not None:
                    display_path = _host_path(path)
                    if self._select_path(path, display_path):
                        self._refresh_file_list()
                        self._update_title()
                        self._sync_address_bar()
        dialog.destroy()

    def _selected_path_from_input(self):
        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.has_selected():
            self._append_log(_('No file selected'), None, _status.ERROR)
            self.toast_overlay.add_toast(Adw.Toast.new(_('No file selected')))
            return None
        return Path(app.system.operation_path())

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

        return name

    def _update_title(self):
        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.has_selected():
            self.set_title('Akizip')
            return
        title = app.system.selected_path()
        if app.system.is_archive() and self._current_internal_path:
            if not title.endswith('/'):
                title = title + '/'
            title = title + self._current_internal_path
        self.set_title(title)
