# add_dialog.py
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
from gettext import gettext as _
from pathlib import Path

from gi.repository import Adw, Gtk, Pango

from .move_folder_chooser import FolderChooserDialog

_HOST_PATH_XATTR = 'user.document-portal.host-path'


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


class AddDialog:
    """Dialog for adding multiple files and folders to the current archive."""

    def __init__(self, parent_window):
        self._parent_window = parent_window

        builder = Gtk.Builder.new_from_resource('/top/akizip/akizip/add-dialog.ui')
        content = builder.get_object('content')
        self._source_label = builder.get_object('source_label')
        self._source_list = builder.get_object('source_list')
        self._remove_btn = builder.get_object('remove_btn')
        self._dest_entry = builder.get_object('dest_entry')

        self._source_paths = []
        self._folder_set = set()
        self._on_confirm = None

        self.dialog = Adw.AlertDialog.new(_('Add to Archive'), _('Add files and folders to the current archive.'))
        dialog_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dialog_content.set_size_request(320, -1)
        dialog_content.append(content)
        self.dialog.set_extra_child(dialog_content)
        self.dialog.add_response('cancel', _('_Cancel'))
        self.dialog.add_response('confirm', _('_Add'))
        self.dialog.set_response_appearance('confirm', Adw.ResponseAppearance.SUGGESTED)
        self.dialog.set_default_response('confirm')
        self.dialog.set_close_response('cancel')

        builder.get_object('add_files_btn').connect('clicked', self._on_add_files)
        builder.get_object('add_folders_btn').connect('clicked', self._on_add_folders)
        self._remove_btn.connect('clicked', self._on_remove)
        builder.get_object('dest_browse').connect('clicked', self._on_dest_browse)
        self._source_list.connect('row-selected', self._on_source_selected)
        self._dest_entry.connect('changed', lambda _e: self._update_confirm_sensitive())
        self.dialog.connect('response', self._on_response)

        self._update_source_list()

    def set_folders(self, folders):
        self._folder_set = set(folders)

    def set_current_path(self, path):
        self._dest_entry.set_text((path.rstrip('/') + '/') if path else '/')

    def add_source_paths(self, paths):
        for path in paths:
            if path and path not in self._source_paths:
                self._source_paths.append(path)
        self._update_source_list()

    def connect_confirm(self, callback):
        self._on_confirm = callback

    def present(self):
        self.dialog.present(self._parent_window)

    def get_source_paths(self):
        return list(self._source_paths)

    def get_dest_folder(self):
        return self._dest_entry.get_text().strip().lstrip('/').rstrip('/')

    def _update_source_list(self):
        while True:
            row = self._source_list.get_first_child()
            if row is None:
                break
            self._source_list.remove(row)
        for path in self._source_paths:
            label = Gtk.Label()
            label.set_label(_host_path(path))
            label.set_xalign(0)
            label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            label.set_margin_start(6)
            label.set_margin_end(6)
            label.set_margin_top(4)
            label.set_margin_bottom(4)
            self._source_list.append(label)
        self._source_label.set_label(_('Source items ({})').format(len(self._source_paths)))
        self._remove_btn.set_sensitive(False)
        self._update_confirm_sensitive()

    def _update_confirm_sensitive(self):
        self.dialog.set_response_enabled('confirm', len(self._source_paths) > 0)

    def _on_source_selected(self, _list, row):
        self._remove_btn.set_sensitive(row is not None)

    def _on_add_files(self, _btn):
        self._pick_sources(
            _('Select Files'),
            Gtk.FileChooserAction.OPEN,
        )

    def _on_add_folders(self, _btn):
        self._pick_sources(
            _('Select Folders'),
            Gtk.FileChooserAction.SELECT_FOLDER,
        )

    def _pick_sources(self, title, action):
        chooser = Gtk.FileChooserNative.new(
            title,
            self._parent_window,
            action,
            _('_Add'),
            _('_Cancel'),
        )
        chooser.set_select_multiple(True)

        def on_response(c, response):
            if response == Gtk.ResponseType.ACCEPT:
                self.add_source_paths(
                    path for path in
                    (f.get_path() for f in c.get_files())
                    if path
                )
            c.destroy()

        chooser.connect('response', on_response)
        chooser.show()

    def _on_remove(self, _btn):
        row = self._source_list.get_selected_row()
        if row is None:
            return
        idx = row.get_index()
        if 0 <= idx < len(self._source_paths):
            self._source_paths.pop(idx)
            self._update_source_list()

    def _on_dest_browse(self, _btn):
        chooser = FolderChooserDialog(self._parent_window)
        chooser.set_folders(self._folder_set)
        chooser.set_current_path(self.get_dest_folder())

        def on_selected(path):
            self._dest_entry.set_text(path + '/' if path else '/')

        chooser.connect_select(on_selected)
        chooser.present()

    def _on_response(self, _dialog, response):
        if response == 'confirm' and self._on_confirm is not None:
            self._on_confirm(self.get_source_paths(), self.get_dest_folder())
