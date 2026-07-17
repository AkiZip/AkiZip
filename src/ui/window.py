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
import tempfile
from pathlib import Path

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Pango
from ..plugins.password import is_password_error
from ..plugins.status import _status
from ..plugins.system import ARCHIVE_SUFFIXES, archive_suffix
from .info_dialog import InfoDialogMixin
from .log_panel import LogPanelMixin


_HOST_PATH_XATTR = 'user.document-portal.host-path'
_IS_FLATPAK = os.path.exists('/.flatpak-info')


def _host_path(path):
    if not path:
        return ''
    p = Path(path)
    try:
        value = os.getxattr(os.fsencode(str(p)), _HOST_PATH_XATTR)
        return os.fsdecode(value) or str(p)
    except OSError:
        for parent in p.parents:
            try:
                value = os.getxattr(os.fsencode(str(parent)), _HOST_PATH_XATTR)
                host_parent = os.fsdecode(value) or str(parent)
                return str(Path(host_parent) / p.relative_to(parent))
            except OSError:
                continue
        return str(p)


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
    info_button = Gtk.Template.Child()
    move_button = Gtk.Template.Child()
    delete_button = Gtk.Template.Child()
    extract_split_button = Gtk.Template.Child()
    extract_menu_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    address_entry = Gtk.Template.Child()
    file_list_stack = Gtk.Template.Child()
    file_list_scroller = Gtk.Template.Child()
    context_menu = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def butadd(self, button):
        self._present_compress_dialog()


    def _default_compress_format(self):
        return self._default_compress_options()['format']

    def _default_compress_options(self):
        options = {
            'format': '7z',
            'level': 5,
            'method': 'default',
            'dictionary_size': 0,
            'threads': 0,
        }
        app = self.get_application()
        if app is None or not hasattr(app, 'settings'):
            return options

        archive_format = self._settings_get_string('default-compress-format', options['format'])
        method = self._settings_get_string('default-compress-method', options['method'])
        _VALID_FORMATS = ('7z', 'tar', 'zip')
        options['format'] = archive_format if archive_format in _VALID_FORMATS else '7z'
        level = self._settings_get_int('default-compress-level', options['level'])
        options['level'] = level if level in (0, 1, 3, 5, 7, 9) else 5
        fmt = options['format']
        if fmt == '7z':
            options['method'] = method if method in ('default', 'LZMA2', 'LZMA', 'PPMd', 'BZip2') else 'default'
        elif fmt == 'tar':
            options['method'] = method if method in ('GNU', 'POSIX') else 'GNU'
        elif fmt == 'zip':
            options['method'] = method if method in ('Deflate', 'Deflate64', 'BZip2', 'LZMA', 'PPMd') else 'Deflate'
        options['dictionary_size'] = self._settings_get_int('default-compress-dictionary-size', options['dictionary_size'])
        options['threads'] = self._settings_get_int('default-compress-threads', options['threads'])
        options['encrypt_names'] = self._settings_get_boolean('default-compress-encrypt-names', False)
        return options

    def _settings_get_string(self, key, fallback):
        app = self.get_application()
        if app is None or not hasattr(app, 'settings'):
            return fallback
        try:
            return app.settings.get_string(key)
        except Exception:
            return fallback

    def _settings_get_int(self, key, fallback):
        app = self.get_application()
        if app is None or not hasattr(app, 'settings'):
            return fallback
        try:
            return app.settings.get_int(key)
        except Exception:
            return fallback

    def _settings_get_boolean(self, key, fallback):
        app = self.get_application()
        if app is None or not hasattr(app, 'settings'):
            return fallback
        try:
            return app.settings.get_boolean(key)
        except Exception:
            return fallback

    def _run_default_compress_multi(self, output_path, source_paths):
        options = self._default_compress_options()
        self._run_command(
            'archive.compress_advance',
            output_path,
            source_paths,
            self._advanced_compress_args(options),
        )

    def _run_advanced_compress_multi(self, output_path, source_paths, options):
        self._run_command(
            'archive.compress_advance',
            output_path,
            source_paths,
            self._advanced_compress_args(options),
        )

    def _advanced_compress_args(self, options):
        fmt = options['format']
        args = [f"-t{fmt}"]
        if fmt == 'tar':
            return args
        args.append(f"-mx={options['level']}")
        if options['method'] != 'default':
            if fmt == 'zip':
                args.append(f"-mm={options['method']}")
            else:
                args.append(f"-m0={options['method']}")
        if fmt == '7z' and options['dictionary_size'] > 0:
            args.append(f"-md={options['dictionary_size']}m")
        if options['threads'] > 0:
            args.append(f"-mmt={options['threads']}")
        password = options.get('password', '')
        if password:
            args.append(f"-p{password}")
            if fmt == '7z' and options.get('encrypt_names'):
                args.append('-mhe=on')
        return args

    @Gtk.Template.Callback()
    def butinfo(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return
        self._show_info_dialog(selected)

    @Gtk.Template.Callback()
    def buttest(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return

        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.can_extract():
            self._append_log(_('Test failed'), _('Selected path is not an archive.'), _status.ERROR)
            return

        def run_test(password):
            def on_error(error):
                if is_password_error(error):
                    self._present_password_dialog(
                        lambda new_password: run_test(new_password)
                    )
                    return True
                return False

            self._run_command(
                'archive.test',
                selected,
                password,
                on_error_extra=on_error,
            )

        run_test(None)

    @Gtk.Template.Callback()
    def butmove(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return

        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.can_extract():
            self._append_log(_('Move failed'), _('Selected path is not an archive.'), _status.ERROR)
            return
        if not app.system.can_modify():
            self._append_log(_('Move failed'), _('This archive format does not support modification.'), _status.ERROR)
            return

        selection = getattr(self, '_file_list_selection', None)
        if selection is None:
            return
        item = selection.get_selected_item()
        if item is None or item.path == '..':
            self._show_notification(_('No file selected'), _status.ERROR)
            return

        target_name = item.path
        dialog = Adw.AlertDialog.new(_('Move'), _('Move "{}" to:').format(target_name))
        entry = Gtk.Entry()
        entry.set_text(item.full_path.rstrip('/') if item.is_folder else item.full_path)
        entry.set_activates_default(True)

        browse_button = Gtk.Button(icon_name='folder-symbolic')
        browse_button.set_tooltip_text(_('Select destination folder'))
        browse_button.set_valign(Gtk.Align.CENTER)

        def on_browse_clicked(_btn):
            from .move_folder_chooser import FolderChooserDialog
            chooser = FolderChooserDialog(self)
            chooser.set_folders(self._folder_set)
            if item.is_folder:
                chooser.set_source_path(item.full_path.rstrip('/'))
            chooser.set_current_path('')

            def on_selected(path):
                if path:
                    entry.set_text(path + '/' + item.path)
                else:
                    entry.set_text(item.path)

            chooser.connect_select(on_selected)
            chooser.present()

        browse_button.connect('clicked', on_browse_clicked)

        entry.set_hexpand(True)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_hexpand(True)
        box.append(entry)
        box.append(browse_button)
        dialog.set_extra_child(box)
        dialog.add_response('cancel', _('_Cancel'))
        dialog.add_response('confirm', _('_Move'))
        dialog.set_response_appearance('confirm', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('confirm')
        dialog.set_close_response('cancel')

        def run_move(password):
            def on_error(error):
                if is_password_error(error):
                    self._present_password_dialog(
                        lambda new_password: run_move(new_password)
                    )
                    return True
                return False

            dst_path = entry.get_text().strip().lstrip('/').rstrip('/')
            if not dst_path:
                dst_path = item.path.rstrip('/')
            src_path = item.full_path.rstrip('/') if item.is_folder else item.full_path
            self._run_command(
                'archive.move',
                selected,
                src_path,
                dst_path,
                password,
                on_success_extra=lambda _output: self._refresh_file_list(),
                on_error_extra=on_error,
            )

        def on_response(_d, response):
            if response == 'confirm':
                run_move(None)

        dialog.connect('response', on_response)
        dialog.present(self)

    def butadd_file(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return

        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.can_extract():
            self._append_log(_('Add failed'), _('Selected path is not an archive.'), _status.ERROR)
            return
        if not app.system.can_modify():
            self._append_log(_('Add failed'), _('This archive format does not support modification.'), _status.ERROR)
            return

        source_path = None

        dialog = Adw.AlertDialog.new(_('Add File'), _('Add a file to the current archive.'))
        dialog.add_response('cancel', _('_Cancel'))
        dialog.add_response('confirm', _('_Add'))
        dialog.set_response_appearance('confirm', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('confirm')
        dialog.set_close_response('cancel')

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        content.set_size_request(350, -1)

        # Source file row
        source_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        source_box.set_hexpand(True)
        source_label = Gtk.Label(label=_('File'))
        source_label.set_size_request(80, -1)
        source_label.set_xalign(0)
        source_entry = Gtk.Entry()
        source_entry.set_placeholder_text(_('Select a file'))
        source_entry.set_editable(False)
        source_entry.set_hexpand(True)
        source_browse = Gtk.Button(icon_name='document-open-symbolic')
        source_browse.set_tooltip_text(_('Select file'))
        source_browse.set_valign(Gtk.Align.CENTER)

        def on_source_browse(_btn):
            chooser = Gtk.FileChooserNative.new(
                _('Select File'),
                self,
                Gtk.FileChooserAction.OPEN,
                _('_Open'),
                _('_Cancel'),
            )

            def on_response(c, response):
                nonlocal source_path
                if response == Gtk.ResponseType.ACCEPT:
                    file = c.get_file()
                    if file is not None:
                        path = file.get_path()
                        if path is not None:
                            source_path = path
                            source_entry.set_text(_host_path(path))
                c.destroy()

            chooser.connect('response', on_response)
            chooser.show()

        source_browse.connect('clicked', on_source_browse)
        source_box.append(source_label)
        source_box.append(source_entry)
        source_box.append(source_browse)
        content.append(source_box)

        # Destination folder row
        dest_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dest_box.set_hexpand(True)
        dest_label = Gtk.Label(label=_('Destination'))
        dest_label.set_size_request(80, -1)
        dest_label.set_xalign(0)
        dest_entry = Gtk.Entry()
        dest_entry.set_text(self._current_internal_path or '/')
        dest_entry.set_placeholder_text(_('Destination folder'))
        dest_entry.set_hexpand(True)
        dest_browse = Gtk.Button(icon_name='folder-symbolic')
        dest_browse.set_tooltip_text(_('Select destination folder'))
        dest_browse.set_valign(Gtk.Align.CENTER)

        def on_dest_browse(_btn):
            from .move_folder_chooser import FolderChooserDialog
            chooser = FolderChooserDialog(self)
            chooser.set_folders(self._folder_set)
            chooser.set_current_path(self._current_internal_path.rstrip('/'))

            def on_selected(path):
                dest_entry.set_text(path + '/' if path else '/')

            chooser.connect_select(on_selected)
            chooser.present()

        dest_browse.connect('clicked', on_dest_browse)
        dest_box.append(dest_label)
        dest_box.append(dest_entry)
        dest_box.append(dest_browse)
        content.append(dest_box)

        dialog.set_extra_child(content)

        def run_add(password):
            def on_error(error):
                if is_password_error(error):
                    self._present_password_dialog(
                        lambda new_password: run_add(new_password)
                    )
                    return True
                return False

            if not source_path:
                self._show_notification(_('No file selected'), _status.ERROR)
                return

            dest_folder = dest_entry.get_text().strip().lstrip('/').rstrip('/')
            self._run_command(
                'archive.add',
                selected,
                source_path,
                dest_folder,
                password,
                on_success_extra=lambda _output: self._refresh_file_list(),
                on_error_extra=on_error,
            )

        def on_response(_d, response):
            if response == 'confirm':
                run_add(None)

        dialog.connect('response', on_response)
        dialog.present(self)

    @Gtk.Template.Callback()
    def butdelete(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return

        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.can_extract():
            self._append_log(_('Delete failed'), _('Selected path is not an archive.'), _status.ERROR)
            return
        if not app.system.can_modify():
            self._append_log(_('Delete failed'), _('This archive format does not support modification.'), _status.ERROR)
            return

        selection = getattr(self, '_file_list_selection', None)
        if selection is None:
            return
        item = selection.get_selected_item()
        if item is None or item.path == '..':
            self._show_notification(_('No file selected'), _status.ERROR)
            return

        target_name = item.path
        dialog = Adw.AlertDialog.new(_('Delete'), _('Are you sure you want to delete "{}"?').format(target_name))
        dialog.add_response('cancel', _('_Cancel'))
        dialog.add_response('confirm', _('_Delete'))
        dialog.set_response_appearance('confirm', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response('cancel')
        dialog.set_close_response('cancel')

        def run_delete(password):
            def on_error(error):
                if is_password_error(error):
                    self._present_password_dialog(
                        lambda new_password: run_delete(new_password)
                    )
                    return True
                return False

            file_name = item.full_path.rstrip('/') if item.is_folder else item.full_path
            self._run_command(
                'archive.delete',
                selected,
                [file_name],
                password,
                on_success_extra=lambda _output: self._refresh_file_list(),
                on_error_extra=on_error,
            )

        def on_response(_d, response):
            if response == 'confirm':
                run_delete(None)

        dialog.connect('response', on_response)
        dialog.present(self)

    @Gtk.Template.Callback()
    def butextract(self, button):
        selected = self._selected_path_from_input()
        if selected is None:
            return

        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.can_extract():
            self._append_log(_('Extract failed'), _('Selected path is not an archive.'), _status.ERROR)
            return

        def run_extract(dest, password):
            def on_error(error):
                if is_password_error(error):
                    self._present_password_dialog(
                        lambda new_password: run_extract(dest, new_password)
                    )
                    return True
                return False

            self._run_command(
                'archive.extract',
                selected,
                dest / selected.stem,
                password,
                on_error_extra=on_error,
            )

        self._present_extract_dialog(run_extract)

    def butextract_one(self, button):
        selection = getattr(self, '_file_list_selection', None)
        if selection is None:
            return
        item = selection.get_selected_item()
        if item is None:
            self._show_notification(_('No file selected'), _status.ERROR)
            return
        self._on_extract_entry_clicked(item)

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

    def _present_compress_dialog(self):
        source_paths = []
        last_output = {'display': None, 'op': None}
        default_options = self._default_compress_options()

        builder = Gtk.Builder.new_from_resource('/top/akizip/akizip/compress-dialog.ui')
        content = builder.get_object('content')
        output_entry = builder.get_object('output_entry')
        output_entry.set_editable(not _IS_FLATPAK)
        output_browse = builder.get_object('output_browse')
        source_label = builder.get_object('source_label')
        source_list = builder.get_object('source_list')
        add_files_btn = builder.get_object('add_files_btn')
        add_folders_btn = builder.get_object('add_folders_btn')
        remove_btn = builder.get_object('remove_btn')
        format_combo = builder.get_object('format_combo')
        level_combo = builder.get_object('level_combo')
        method_combo = builder.get_object('method_combo')
        dictionary_spin = builder.get_object('dictionary_spin')
        threads_spin = builder.get_object('threads_spin')
        password_entry = builder.get_object('password_entry')
        encrypt_names_check = builder.get_object('encrypt_names_check')
        suggest_btn = builder.get_object('suggest_btn')

        _METHOD_ITEMS = {
            '7z': [('default', _('Default')), ('LZMA2', 'LZMA2'), ('LZMA', 'LZMA'), ('PPMd', 'PPMd'), ('BZip2', 'BZip2')],
            'tar': [('GNU', 'GNU'), ('POSIX', 'POSIX')],
            'zip': [('Deflate', 'Deflate'), ('Deflate64', 'Deflate64'), ('BZip2', 'BZip2'), ('LZMA', 'LZMA'), ('PPMd', 'PPMd')],
        }

        def _populate_method_combo(fmt, select_id=None):
            method_combo.remove_all()
            items = _METHOD_ITEMS.get(fmt, [])
            for item_id, label in items:
                method_combo.append(item_id, label)
            if select_id and any(i[0] == select_id for i in items):
                method_combo.set_active_id(select_id)
            elif items:
                method_combo.set_active_id(items[0][0])

        format_combo.set_active_id(default_options['format'])
        level_combo.set_active_id(str(default_options['level']))
        _populate_method_combo(default_options['format'], default_options['method'])
        dictionary_spin.set_value(default_options['dictionary_size'])
        threads_spin.set_value(default_options['threads'])
        encrypt_names_check.set_active(default_options.get('encrypt_names', False))

        dialog = Adw.AlertDialog.new(_('Compress'), None)
        dialog.set_extra_child(content)
        dialog.add_response('cancel', _('_Cancel'))
        dialog.add_response('confirm', _('Compress'))
        dialog.set_response_appearance('confirm', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('confirm')
        dialog.set_close_response('cancel')

        def update_source_list():
            while True:
                row = source_list.get_first_child()
                if row is None:
                    break
                source_list.remove(row)
            for path in source_paths:
                label = Gtk.Label()
                label.set_label(_host_path(path))
                label.set_xalign(0)
                label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
                label.set_margin_start(6)
                label.set_margin_end(6)
                label.set_margin_top(4)
                label.set_margin_bottom(4)
                source_list.append(label)
            source_label.set_label(_('Source items ({})').format(len(source_paths)))
            remove_btn.set_sensitive(False)
            confirm_sensitive = len(source_paths) > 0 and output_entry.get_text().strip()
            dialog.set_response_enabled('confirm', confirm_sensitive)

        def on_output_changed(_entry):
            text = output_entry.get_text().strip()
            confirm_sensitive = len(source_paths) > 0 and text
            dialog.set_response_enabled('confirm', confirm_sensitive)
            suffix = Path(text).suffix.lstrip('.').lower()
            if suffix in ('7z', 'tar', 'zip') and format_combo.get_active_id() != suffix:
                format_combo.set_active_id(suffix)

        output_entry.connect('changed', on_output_changed)

        def on_source_selected(_list, row):
            remove_btn.set_sensitive(row is not None)

        source_list.connect('row-selected', on_source_selected)

        def on_add_files(_btn):
            chooser = Gtk.FileChooserNative.new(
                _('Select Files'),
                self,
                Gtk.FileChooserAction.OPEN,
                _('_Add'),
                _('_Cancel'),
            )
            chooser.set_select_multiple(True)

            def on_response(c, response):
                if response == Gtk.ResponseType.ACCEPT:
                    for file in chooser.get_files():
                        path = file.get_path()
                        if path and path not in source_paths:
                            source_paths.append(path)
                    update_source_list()
                c.destroy()

            chooser.connect('response', on_response)
            chooser.show()

        def on_add_folders(_btn):
            chooser = Gtk.FileChooserNative.new(
                _('Select Folders'),
                self,
                Gtk.FileChooserAction.SELECT_FOLDER,
                _('_Add'),
                _('_Cancel'),
            )
            chooser.set_select_multiple(True)

            def on_response(c, response):
                if response == Gtk.ResponseType.ACCEPT:
                    for file in chooser.get_files():
                        path = file.get_path()
                        if path and path not in source_paths:
                            source_paths.append(path)
                    update_source_list()
                c.destroy()

            chooser.connect('response', on_response)
            chooser.show()

        def on_remove(_btn):
            row = source_list.get_selected_row()
            if row is None:
                return
            idx = row.get_index()
            if 0 <= idx < len(source_paths):
                source_paths.pop(idx)
                update_source_list()

        def on_browse_output(_btn):
            chooser = Gtk.FileChooserNative.new(
                _('Save Archive As'),
                self,
                Gtk.FileChooserAction.SAVE,
                _('_Save'),
                _('_Cancel'),
            )
            if source_paths:
                archive_format = format_combo.get_active_id() or self._default_compress_format()
                default_name = Path(source_paths[0]).name + f'.{archive_format}'
                chooser.set_current_name(default_name)

            def on_response(c, response):
                if response == Gtk.ResponseType.ACCEPT:
                    file = c.get_file()
                    if file is not None:
                        op = file.get_path()
                        if op is not None:
                            display = _host_path(op)
                            display_path = Path(display)
                            suffix = display_path.suffix.lstrip('.').lower()
                            if suffix not in ('7z', 'tar', 'zip'):
                                op = str(Path(op).with_suffix('.7z'))
                                display = str(display_path.with_suffix('.7z'))
                            if Path(op).exists():
                                dialog = Adw.AlertDialog.new(_('Overwrite is not currently supported'), None)
                                dialog.add_response('ok', _('_OK'))
                                dialog.set_default_response('ok')
                                dialog.set_close_response('ok')
                                dialog.present(self)
                            else:
                                output_entry.set_text(display)
                                last_output['display'] = display
                                last_output['op'] = op
                c.destroy()

            chooser.connect('response', on_response)
            chooser.show()

        def on_format_changed(combo):
            fmt = combo.get_active_id() or '7z'
            current_id = method_combo.get_active_id()
            _populate_method_combo(fmt, current_id)
            level_combo.set_sensitive(fmt in ('7z', 'zip'))
            method_combo.set_sensitive(fmt in ('7z', 'tar', 'zip'))
            dictionary_spin.set_sensitive(fmt == '7z')
            threads_spin.set_sensitive(fmt in ('7z', 'zip'))
            password_entry.set_sensitive(fmt != 'tar')
            encrypt_names_check.set_sensitive(fmt == '7z')
            if fmt != '7z':
                encrypt_names_check.set_active(False)
            text = output_entry.get_text().strip()
            if text:
                op_path = Path(text)
                suffix = op_path.suffix.lstrip('.').lower()
                if suffix in ('7z', 'tar', 'zip') and suffix != fmt:
                    new_text = str(op_path.with_suffix(f'.{fmt}'))
                    output_entry.set_text(new_text)
                    if last_output['display'] == text and last_output['op']:
                        last_output['display'] = new_text
                        last_output['op'] = str(Path(last_output['op']).with_suffix(f'.{fmt}'))

        format_combo.connect('changed', on_format_changed)
        on_format_changed(format_combo)

        def on_suggest(_btn):
            if not source_paths:
                self._show_notification(_('No source items to analyze'), _status.WARNING)
                return

            app = self.get_application()
            scan = getattr(app, 'commands', {}).get('system.scan')
            suggest = getattr(app, 'commands', {}).get('system.suggest_zip_paramiters')
            if scan is None or suggest is None:
                self._show_notification(_('Recommendation not available'), _status.ERROR)
                return

            try:
                depth = app.settings.get_int('compress-scan-depth') if (app is not None and hasattr(app, 'settings')) else 3
                merged = {
                    'root': 'multiple',
                    'max_depth': depth,
                    'total': 0,
                    'files': 0,
                    'folders': 0,
                    'total_size': 0,
                    'largest_file': {'path': '', 'size': 0},
                    'extensions': {},
                    'categories': {
                        'compressed': {'count': 0, 'size': 0},
                        'media': {'count': 0, 'size': 0},
                        'documents': {'count': 0, 'size': 0},
                        'code': {'count': 0, 'size': 0},
                        'other': {'count': 0, 'size': 0},
                    },
                    'size_buckets': {
                        'small': {'count': 0, 'size': 0},
                        'medium': {'count': 0, 'size': 0},
                        'large': {'count': 0, 'size': 0},
                        'huge': {'count': 0, 'size': 0},
                    },
                    'errors': [],
                }
                for src in source_paths:
                    result = scan(str(src), depth)
                    merged['files'] += result.get('files', 0)
                    merged['folders'] += result.get('folders', 0)
                    merged['total'] = merged['files'] + merged['folders']
                    merged['total_size'] += result.get('total_size', 0)
                    merged['errors'].extend(result.get('errors', []))
                    if result.get('largest_file', {}).get('size', 0) > merged['largest_file']['size']:
                        merged['largest_file'] = result['largest_file']
                    for key, val in result.get('extensions', {}).items():
                        bucket = merged['extensions'].setdefault(key, {'count': 0, 'size': 0})
                        bucket['count'] += val.get('count', 0)
                        bucket['size'] += val.get('size', 0)
                    for key, val in result.get('categories', {}).items():
                        bucket = merged['categories'].setdefault(key, {'count': 0, 'size': 0})
                        bucket['count'] += val.get('count', 0)
                        bucket['size'] += val.get('size', 0)
                    for key, val in result.get('size_buckets', {}).items():
                        bucket = merged['size_buckets'].setdefault(key, {'count': 0, 'size': 0})
                        bucket['count'] += val.get('count', 0)
                        bucket['size'] += val.get('size', 0)

                suggestion = suggest(merged)
            except Exception as error:
                self._show_notification(_('Recommendation failed'), _status.ERROR)
                self._append_log(_('Compression recommendation failed'), str(error), _status.WARNING)
                return

            fmt = suggestion.get('format', '7z')
            if fmt in ('7z', 'tar', 'zip'):
                format_combo.set_active_id(fmt)

            level = suggestion.get('level')
            if level is not None and str(level) in ('0', '1', '3', '5', '7', '9'):
                level_combo.set_active_id(str(level))

            method = suggestion.get('method', 'default')
            if method == 'store':
                if fmt == 'tar':
                    method = 'GNU'
                elif fmt == 'zip':
                    method = 'Deflate'
                else:
                    method = 'default'
            valid_methods = [item[0] for item in _METHOD_ITEMS.get(fmt, [])]
            if method in valid_methods:
                method_combo.set_active_id(method)
            elif valid_methods:
                method_combo.set_active_id(valid_methods[0])

            dictionary = suggestion.get('dictionary', '0')
            if isinstance(dictionary, str) and dictionary.endswith('m'):
                try:
                    dictionary_spin.set_value(int(dictionary[:-1]))
                except ValueError:
                    dictionary_spin.set_value(0)
            elif isinstance(dictionary, int):
                dictionary_spin.set_value(dictionary)
            else:
                dictionary_spin.set_value(0)

            threads = suggestion.get('threads', '0')
            if threads == 'on':
                threads_spin.set_value(0)
            else:
                try:
                    threads_spin.set_value(int(threads))
                except (ValueError, TypeError):
                    threads_spin.set_value(0)

            on_format_changed(format_combo)

            reasons = suggestion.get('reason', [])
            if reasons:
                self._append_log(
                    _('Compression recommendation'),
                    ' '.join(suggestion.get('sevenzip_args', [])),
                    _status.FINISHED,
                )
                for r in reasons:
                    self._append_log(_('Recommendation reason'), r, _status.FINISHED)

        add_files_btn.connect('clicked', on_add_files)
        add_folders_btn.connect('clicked', on_add_folders)
        remove_btn.connect('clicked', on_remove)
        output_browse.connect('clicked', on_browse_output)
        output_entry.connect('activate', lambda _e: dialog.response('confirm'))
        suggest_btn.connect('clicked', on_suggest)

        def on_response(_d, response):
            if response == 'confirm':
                text = output_entry.get_text().strip()
                if not text or not source_paths:
                    return
                if last_output['display'] == text and last_output['op']:
                    output_path = Path(last_output['op'])
                else:
                    output_path = Path(text).expanduser()
                paths = [Path(p) for p in source_paths]
                options = {
                    'format': format_combo.get_active_id() or '7z',
                    'level': int(level_combo.get_active_id() or '5'),
                    'method': method_combo.get_active_id() or 'default',
                    'dictionary_size': dictionary_spin.get_value_as_int(),
                    'threads': threads_spin.get_value_as_int(),
                    'password': password_entry.get_text(),
                    'encrypt_names': encrypt_names_check.get_active(),
                }
                self._run_advanced_compress_multi(output_path, paths, options)

        dialog.connect('response', on_response)
        dialog.present(self)

    def _present_password_dialog(self, on_password_entered):
        dialog = Adw.AlertDialog.new(_('Password Required'), None)
        dialog.set_body(_('This archive is encrypted. Please enter the password.'))

        password_entry = Gtk.PasswordEntry()
        password_entry.set_show_peek_icon(True)
        password_entry.set_hexpand(True)
        password_entry.set_margin_top(12)
        password_entry.set_margin_bottom(12)
        dialog.set_extra_child(password_entry)

        dialog.add_response('cancel', _('_Cancel'))
        dialog.add_response('confirm', _('_OK'))
        dialog.set_response_appearance('confirm', Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response('confirm')

        def on_response(_d, response):
            if response == 'confirm':
                password = password_entry.get_text()
                on_password_entered(password)

        dialog.connect('response', on_response)
        dialog.present(self)

    def _present_extract_dialog(self, on_chosen):
        builder = Gtk.Builder.new_from_resource('/top/akizip/akizip/extract-dialog.ui')
        box = builder.get_object('content')
        entry = builder.get_object('entry')
        entry.set_editable(not _IS_FLATPAK)
        browse_button = builder.get_object('browse_button')
        password_entry = builder.get_object('password_entry')

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
                password = password_entry.get_text() or None
                dest = Path(last['op']) if (last['display'] == text and last['op']) else Path(text).expanduser()
                on_chosen(dest, password)

        dialog.connect('response', on_response)
        dialog.present(self)

    def _build_file_list(self):
        self._file_list_store = Gio.ListStore(item_type=ArchiveEntry)
        selection = Gtk.SingleSelection(model=self._file_list_store)
        view = Gtk.ColumnView(model=selection)
        view.set_show_row_separators(True)
        view.set_show_column_separators(False)
        view.connect('activate', self._on_row_activate)

        gesture = Gtk.GestureClick()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.connect('pressed', self._on_list_right_click)
        view.add_controller(gesture)

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
        self._file_list_selection = selection

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
        self._list_items.add(list_item)

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
        self._list_items.add(list_item)

    def _on_list_right_click(self, gesture, _n_press, x, y):
        view = self._file_list_view
        position = Gtk.INVALID_LIST_POSITION
        for list_item in self._list_items:
            pos = list_item.get_position()
            if pos == Gtk.INVALID_LIST_POSITION:
                continue
            child = list_item.get_child()
            if child is None:
                continue
            row = child.get_parent()
            if row is not None:
                row = row.get_parent()
            if row is None:
                continue
            ok, bounds = row.compute_bounds(view)
            if ok and bounds.origin.y <= y <= bounds.origin.y + bounds.size.height:
                position = pos
                break
        if position == Gtk.INVALID_LIST_POSITION:
            return
        item = self._file_list_store.get_item(position)
        if item is None or item.path == '..':
            return
        self._file_list_selection.set_selected(position)

        popover = Gtk.PopoverMenu.new_from_model(self.context_menu)
        popover.set_parent(view)
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        popover.connect('closed', lambda p: GLib.idle_add(p.unparent))
        popover.popup()

    def _on_size_bind(self, factory, list_item):
        size = list_item.get_item().size
        text = ''
        if size:
            try:
                text = self._format_size(int(size))
            except (TypeError, ValueError):
                text = size
        list_item.get_child().set_text(text)

    def _on_modified_bind(self, factory, list_item):
        list_item.get_child().set_text(list_item.get_item().modified)

    def _on_extract_entry_clicked(self, item):
        if item is None or item.path == '..':
            return

        selected = self._selected_path_from_input()
        if selected is None:
            return

        def run_extract(dest, password):
            def on_error(error):
                if is_password_error(error):
                    self._present_password_dialog(
                        lambda new_password: run_extract(dest, new_password)
                    )
                    return True
                return False

            self._run_command(
                'archive.extract_file',
                selected,
                item.full_path.rstrip('/') if item.is_folder else item.full_path,
                dest,
                password,
                on_error_extra=on_error,
            )

        self._present_extract_dialog(run_extract)

    def _on_row_activate(self, view, position):
        item = self._file_list_store.get_item(position)
        if item is None:
            return
        if item.is_folder:
            self._current_internal_path = item.full_path
            self._render_current_folder()
            return
        if item.path != '..' and archive_suffix(Path(item.path)) in ARCHIVE_SUFFIXES:
            self._open_nested_archive(item)

    def _open_nested_archive(self, item):
        app = self.get_application()
        if app is None or not hasattr(app, 'system') or not app.system.has_selected():
            return

        selected = Path(app.system.operation_path())
        job_queue = getattr(app, 'job_queue', None)
        if job_queue is None:
            return

        try:
            temp_dir = tempfile.mkdtemp(prefix='akizip-nested-')
        except Exception as error:
            self._show_notification(_('Failed to create temporary directory'), _status.ERROR)
            return

        file_name = item.full_path.rstrip('/') if item.is_folder else item.full_path
        display_name = item.path.rstrip('/') if item.is_folder else item.path

        def run_extract(password):
            extract_args = (selected, file_name, temp_dir)
            if password is not None:
                extract_args = (selected, file_name, temp_dir, password)

            def on_error(error):
                self.file_list_stack.set_visible_child_name('list')
                if is_password_error(error):
                    self._present_password_dialog(
                        lambda new_password: run_extract(new_password)
                    )
                    return
                self._show_notification(str(error), _status.ERROR)

            job_queue.submit(
                app.commands['archive.extract_file'],
                extract_args,
                on_success=lambda output: _on_extract_success(output),
                on_error=on_error,
                task_id='archive.extract_file',
                msg=_('Extract ') + display_name,
            )

        def _on_extract_success(output):
            extracted_path = Path(temp_dir) / display_name
            if not extracted_path.exists():
                self._show_notification(_('Extracted file not found'), _status.ERROR)
                return
            if self._select_path(str(extracted_path), display_name):
                app.system.is_nested = True
                app.system._temp_dirs.append(temp_dir)
                self._update_archive_buttons()
                self._refresh_file_list()
                self._update_title()
                self._sync_address_bar()

        self.file_list_stack.set_visible_child_name('loading')
        run_extract(None)

    def _refresh_file_list(self):
        self._all_entries = []
        self._folder_set = set()
        self._current_internal_path = ''
        self._file_list_store.remove_all()
        app = self.get_application()
        if app is None or not hasattr(app, 'system'):
            self.file_list_stack.set_visible_child_name('empty')
            return
        if not app.system.has_selected():
            self.file_list_stack.set_visible_child_name('empty')
            return
        if not app.system.is_archive():
            self.file_list_stack.set_visible_child_name('not_archive')
            return
        if app.system.format_category() == 'no_preview':
            self.file_list_stack.set_visible_child_name('no_preview')
            return

        selected = Path(app.system.operation_path())
        command = getattr(app, 'commands', {}).get('archive.list')
        job_queue = getattr(app, 'job_queue', None)
        if command is None or job_queue is None:
            self.file_list_stack.set_visible_child_name('empty_archive')
            return

        self.file_list_stack.set_visible_child_name('loading')

        def run_list(password):
            list_args = (selected,)
            if password is not None:
                list_args = (selected, password)

            def on_error(error):
                if is_password_error(error):
                    self._present_password_dialog(
                        lambda new_password: run_list(new_password)
                    )
                    return
                self._on_file_list_error(error)

            job_queue.submit(
                command,
                list_args,
                on_success=lambda output: self._populate_file_list(output),
                on_error=on_error,
                task_id='archive.list',
                msg=_('List ') + selected.name,
            )

        run_list(None)

    def _populate_file_list(self, output):
        self._all_entries = parse_archive_entries(output)
        app = self.get_application()
        if app is not None and hasattr(app, 'system') and app.system.has_selected():
            suffix = archive_suffix(app.system.selected)
            if suffix in ('.tar.bz2', '.tar.xz'):
                has_real_entry = any(
                    not entry.get('Path', '').startswith('/')
                    for entry in self._all_entries
                )
                if not has_real_entry:
                    inner_name = app.system.selected.name
                    if suffix == '.tar.bz2':
                        inner_name = inner_name[:-4]
                    else:
                        inner_name = inner_name[:-3]
                    self._all_entries.append({
                        'Path': inner_name,
                        'Size': '',
                        'Modified': '',
                    })
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
            self.file_list_stack.set_visible_child_name('empty_archive')
        else:
            self.file_list_stack.set_visible_child_name('list')
        self._sync_address_bar()
        self._update_title()

    def _on_file_list_error(self, error):
        self._all_entries = []
        self._folder_set = set()
        self._current_internal_path = ''
        self._append_log(_('List failed'), str(error), _status.ERROR)
        self.file_list_stack.set_visible_child_name('empty_archive')

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
        self._list_items = set()

        app = self.get_application()
        if app is not None and hasattr(app, 'settings'):
            self._initial_language = app.settings.get_string('language')
            app.settings.connect('changed::language', self._on_language_changed)

        action = Gio.SimpleAction.new('extract-selected', None)
        action.connect('activate', lambda _a, _p: self.butextract_one(None))
        self.add_action(action)

        action = Gio.SimpleAction.new('extract-all', None)
        action.connect('activate', lambda _a, _p: self.butextract(None))
        self.add_action(action)

        self._add_file_action = Gio.SimpleAction.new('add-file', None)
        self._add_file_action.connect('activate', lambda _a, _p: self.butadd_file(None))
        self.add_action(self._add_file_action)

        self._move_action = Gio.SimpleAction.new('move-selected', None)
        self._move_action.connect('activate', lambda _a, _p: self.butmove(None))
        self.add_action(self._move_action)

        self._delete_action = Gio.SimpleAction.new('delete-selected', None)
        self._delete_action.connect('activate', lambda _a, _p: self.butdelete(None))
        self.add_action(self._delete_action)

        self._build_file_list()
        self.address_entry.set_editable(not _IS_FLATPAK)
        self.file_list_stack.set_visible_child_name('empty')
        self._update_archive_buttons()
        self._sync_address_bar()
        self._update_title()
        self._update_extract_button_for_locale()
        self.connect('destroy', self._on_destroy)

    def _on_destroy(self, widget):
        app = self.get_application()
        if app is not None and hasattr(app, 'system'):
            app.system.cleanup_temp_dirs()

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
        if app is None or not hasattr(app, 'system'):
            self._append_log(_('No file selected'), None, _status.ERROR)
            self._show_notification(_('No file selected'), _status.ERROR)
            return None
        if app.system.selected is None:
            self._append_log(_('No file selected'), None, _status.ERROR)
            self._show_notification(_('No file selected'), _status.ERROR)
            return None
        if not app.system.selected.exists():
            self._append_log(_('File not found'), str(app.system.selected), _status.ERROR)
            self._show_notification(_('File not found'), _status.ERROR)
            return None
        return Path(app.system.operation_path())

    def _select_path(self, path, display_path=None):
        app = self.get_application()
        if app is None or not hasattr(app, 'system'):
            self._append_log(_('System state not found'), str(path), _status.ERROR)
            return False

        app.system.cleanup_temp_dirs()
        app.system.is_nested = False

        if display_path is None:
            app.system.select_by_input(path)
        else:
            app.system.select_by_fileview(path, display_path)
        info = app.system.info()
        if not info['success']:
            self._append_log(_('Select failed'), info['msg'], _status.ERROR)
            return False

        self._append_log(_('Selected ') + info['name'], info['path'], _status.FINISHED)
        self._update_archive_buttons()
        if info.get('format_category') == 'unverified':
            dialog = Adw.AlertDialog.new(
                _('Format compatibility warning'),
                _('This format has not been verified for compatibility. Move and delete operations are disabled.'),
            )
            dialog.add_response('ok', _('_OK'))
            dialog.set_default_response('ok')
            dialog.set_close_response('ok')
            dialog.present(self)
        elif info.get('format_category') == 'no_preview':
            dialog = Adw.AlertDialog.new(
                _('Preview not supported'),
                _('This format does not support preview. Only extract is available.'),
            )
            dialog.add_response('ok', _('_OK'))
            dialog.set_default_response('ok')
            dialog.set_close_response('ok')
            dialog.present(self)
        elif info.get('format_category') == 'nested':
            dialog = Adw.AlertDialog.new(
                _('Nested archive opened'),
                _('This archive was extracted from a parent archive. Move and delete operations are disabled.'),
            )
            dialog.add_response('ok', _('_OK'))
            dialog.set_default_response('ok')
            dialog.set_close_response('ok')
            dialog.present(self)
        return True

    def _update_archive_buttons(self):
        app = self.get_application()
        if app is None or not hasattr(app, 'system'):
            can_modify = False
            has_selected_archive = False
        else:
            can_modify = app.system.can_modify()
            has_selected_archive = app.system.has_selected() and app.system.is_archive()
        if self.move_button is not None:
            self.move_button.set_sensitive(can_modify)
        if self.delete_button is not None:
            self.delete_button.set_sensitive(can_modify)
        if hasattr(self, '_add_file_action') and self._add_file_action is not None:
            self._add_file_action.set_enabled(can_modify and has_selected_archive)
        if hasattr(self, '_move_action') and self._move_action is not None:
            self._move_action.set_enabled(can_modify)
        if hasattr(self, '_delete_action') and self._delete_action is not None:
            self._delete_action.set_enabled(can_modify)

    def _on_language_changed(self, settings, key):
        if settings.get_string(key) == self._initial_language:
            return
        dialog = Adw.AlertDialog.new(
            _('Language changed'),
            _('Restart the application to apply the new language.'),
        )
        dialog.add_response('ok', _('_OK'))
        dialog.set_default_response('ok')
        dialog.set_close_response('ok')
        dialog.present(self)

    def _create_progress_dialog(self, title, handle):
        dialog = Adw.AlertDialog.new(title, '')
        dialog.add_response('cancel', _('Cancel'))
        dialog.set_close_response('cancel')

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        progress_bar = Gtk.ProgressBar()
        progress_bar.set_show_text(True)
        box.append(progress_bar)

        eta_label = Gtk.Label()
        eta_label.add_css_class('dim-label')
        box.append(eta_label)

        dialog.set_extra_child(box)

        def on_response(_d, response):
            if response == 'cancel' and handle is not None:
                handle.cancel()

        dialog.connect('response', on_response)
        dialog.present(self)

        dialog._progress_bar = progress_bar
        dialog._eta_label = eta_label
        return dialog

    def _format_eta(self, seconds):
        if seconds is None:
            return _('Calculating...')
        if seconds < 0:
            return ''
        seconds = int(seconds)
        if seconds < 60:
            return _('%d seconds remaining') % seconds
        return _('%d minutes remaining') % int(seconds / 60)

    def _update_progress_dialog(self, dialog, percent, eta=None):
        if dialog is None:
            return
        dialog._progress_bar.set_fraction(percent / 100.0)
        if hasattr(dialog, '_eta_label') and dialog._eta_label is not None:
            dialog._eta_label.set_text(self._format_eta(eta))

    def _close_progress_dialog(self, dialog):
        if dialog is not None:
            dialog.close()

    def _run_command(self, name, *args, on_success_extra=None, on_error_extra=None):
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

        has_progress = name in ('archive.compress_advance', 'archive.extract', 'archive.extract_file', 'archive.test', 'archive.delete', 'archive.move', 'archive.add')
        progress_dialog = None

        def on_success(output):
            self._close_progress_dialog(progress_dialog)
            self._on_command_success(log_id, name, args, output)
            if on_success_extra is not None:
                on_success_extra(output)

        def on_error(error):
            self._close_progress_dialog(progress_dialog)
            if on_error_extra is not None and on_error_extra(error):
                return
            self._on_command_error(log_id, name, args, error)

        def on_status(task_status):
            if has_progress and task_status.progress is not None:
                self._update_progress_dialog(progress_dialog, task_status.progress, getattr(task_status, 'eta', None))
            self._on_command_status(log_id, name, args, task_status)

        handle = job_queue.submit(
            command,
            args,
            on_success=on_success,
            on_error=on_error,
            task_id=name,
            msg=summary,
            on_status=on_status,
        )
        if has_progress:
            progress_dialog = self._create_progress_dialog(summary, handle)
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
            summary = self._command_summary(name, args, _status.CANCELLED)
            self._append_log(summary, task_status.msg, _status.CANCELLED)
            self._show_notification(summary, _status.CANCELLED)

    def _on_command_success(self, log_id, name, args, output):
        print(output)
        if not self._remove_pending_log(log_id):
            return
        summary = self._command_summary(name, args, _status.FINISHED)
        self._append_log(summary, output, _status.FINISHED)
        self._show_notification(summary, _status.FINISHED)

    def _on_command_error(self, log_id, name, args, error):
        if not self._remove_pending_log(log_id):
            return
        state = _status.TIMEOUT if isinstance(error, TimeoutError) else _status.ERROR
        summary = self._command_summary(name, args, state)
        self._append_log(summary, str(error), state)
        self._show_notification(summary, state)

    def _show_notification(self, message, state=_status.FINISHED):
        if self.toast_overlay is None:
            return
        toast = Adw.Toast.new(message)
        toast.set_timeout(4)
        self.toast_overlay.add_toast(toast)

    def _command_summary(self, name, args, state):
        if name == 'archive.compress_advance':
            source_paths = args[1] if len(args) > 1 else []
            if len(source_paths) > 1:
                target = _('{} items').format(len(source_paths))
            elif source_paths:
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

        if name == 'archive.test':
            target = Path(args[0]).name if args else _('archive')
            if state == _status.PENDING:
                return _('Test ') + target
            if state == _status.WORKING:
                return _('Test ') + target
            if state == _status.FINISHED:
                return _('Tested ') + target
            if state == _status.TIMEOUT:
                return _('Test timed out: ') + target
            if state == _status.CANCELLED:
                return _('Test cancelled: ') + target
            return _('Test failed: ') + target

        if name == 'archive.extract_file':
            target = Path(args[1]).name if len(args) > 1 else _('file')
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

        if name == 'archive.delete':
            target = Path(args[1][0]).name if len(args) > 1 and args[1] else _('file')
            if state == _status.PENDING:
                return _('Delete ') + target
            if state == _status.WORKING:
                return _('Delete ') + target
            if state == _status.FINISHED:
                return _('Deleted ') + target
            if state == _status.TIMEOUT:
                return _('Delete timed out: ') + target
            if state == _status.CANCELLED:
                return _('Delete cancelled: ') + target
            return _('Delete failed: ') + target

        if name == 'archive.move':
            target = Path(args[1]).name if len(args) > 1 else _('file')
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

        if name == 'archive.add':
            target = Path(args[1]).name if len(args) > 1 else _('file')
            if state == _status.PENDING:
                return _('Add ') + target
            if state == _status.WORKING:
                return _('Add ') + target
            if state == _status.FINISHED:
                return _('Added ') + target
            if state == _status.TIMEOUT:
                return _('Add timed out: ') + target
            if state == _status.CANCELLED:
                return _('Add cancelled: ') + target
            return _('Add failed: ') + target

        return name

    def _command_preview(self, name, args):
        if name == 'archive.compress_advance':
            output = Path(args[0]).name if args else _('archive')
            source_paths = args[1] if len(args) > 1 else []
            if len(source_paths) > 1:
                source = _('{} items').format(len(source_paths))
            else:
                source = Path(source_paths[0]).name if source_paths else _('file')
            # TRANSLATORS: {output} is the archive name, {source} is the source file or folder name
            preview = _('Create {output} from {source}').format(output=output, source=source)
            if name == 'archive.compress_advance' and len(args) > 2 and args[2]:
                # TRANSLATORS: {params} are the compression parameters, for example "-mx=9 -mmt=2"
                preview = preview + '\n' + _('Parameters: {params}').format(params=' '.join(args[2]))
            return preview

        if name == 'archive.info':
            archive = Path(args[0]).name if args else _('archive')
            # TRANSLATORS: {archive} is the name of the archive file
            return _('Read archive information from {archive}').format(archive=archive)

        if name == 'archive.extract':
            archive = Path(args[0]).name if args else _('archive')
            output = Path(args[1]).name if len(args) > 1 else _('folder')
            # TRANSLATORS: {archive} is the archive name, {folder} is the destination folder
            return _('Extract {archive} to {folder}').format(archive=archive, folder=output)

        if name == 'archive.test':
            archive = Path(args[0]).name if args else _('archive')
            # TRANSLATORS: {archive} is the name of the archive file
            return _('Test {archive}').format(archive=archive)

        if name == 'archive.extract_file':
            archive = Path(args[0]).name if args else _('archive')
            file_name = Path(args[1]).name if len(args) > 1 else _('file')
            output = Path(args[2]).name if len(args) > 2 else _('folder')
            # TRANSLATORS: {file} is the file inside the archive, {archive} is the archive name, {folder} is the destination folder
            return _('Extract {file} from {archive} to {folder}').format(file=file_name, archive=archive, folder=output)

        if name == 'archive.delete':
            archive = Path(args[0]).name if args else _('archive')
            file_name = Path(args[1][0]).name if len(args) > 1 and args[1] else _('file')
            # TRANSLATORS: {file} is the file inside the archive, {archive} is the archive name
            return _('Delete {file} from {archive}').format(file=file_name, archive=archive)

        if name == 'archive.move':
            archive = Path(args[0]).name if args else _('archive')
            file_name = Path(args[1]).name if len(args) > 1 else _('file')
            dst = Path(args[2]).name if len(args) > 2 else _('destination')
            # TRANSLATORS: {file} is the file inside the archive, {destination} is the destination path inside the archive, {archive} is the archive name
            return _('Move {file} to {destination} in {archive}').format(file=file_name, destination=dst, archive=archive)

        if name == 'archive.add':
            archive = Path(args[0]).name if args else _('archive')
            file_name = Path(args[1]).name if len(args) > 1 else _('file')
            dst = args[2] if len(args) > 2 else _('root')
            # TRANSLATORS: {file} is the file to add, {destination} is the path inside the archive (or "root"), {archive} is the archive name
            return _('Add {file} to {destination} in {archive}').format(file=file_name, destination=dst, archive=archive)

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

    def _get_effective_locale(self):
        app = self.get_application()
        if app is not None and hasattr(app, 'settings'):
            lang_setting = app.settings.get_string('language')
            if lang_setting and lang_setting != 'auto':
                return lang_setting.split('_')[0].lower()

        for env_var in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
            val = os.environ.get(env_var, '')
            if val:
                first_lang = val.split(':')[0]
                if first_lang and first_lang not in ('C', 'POSIX'):
                    return first_lang.split('_')[0].lower()

        return 'en'

    def _update_extract_button_for_locale(self):
        lang = self._get_effective_locale()
        if lang in ('pl', 'ta'):
            self.extract_split_button.set_visible(False)
            self.extract_menu_button.set_visible(True)
        else:
            self.extract_split_button.set_visible(True)
            self.extract_menu_button.set_visible(False)
