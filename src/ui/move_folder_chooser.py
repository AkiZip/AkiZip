# move_folder_chooser.py
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
from gettext import gettext as _

from gi.repository import Gtk


class FolderChooserDialog:
    def __init__(self, parent_window):
        builder = Gtk.Builder.new_from_resource('/top/akizip/akizip/move-folder-chooser.ui')
        self.window = builder.get_object('window')
        self.window.set_transient_for(parent_window)
        self.current_path_entry = builder.get_object('current_path_entry')
        self.folder_list = builder.get_object('folder_list')
        self.cancel_button = builder.get_object('cancel_button')
        self.select_button = builder.get_object('select_button')

        self._folder_set = set()
        self._current_path = ''
        self._source_path = ''
        self._on_select = None
        self._row_paths = {}
        self._last_activated_row = None

        self.folder_list.connect('row-activated', self._on_row_activated)
        self.cancel_button.connect('clicked', self._on_cancel_clicked)
        self.select_button.connect('clicked', self._on_select_clicked)

    def set_folders(self, folders):
        self._folder_set = set(folders)

    def set_current_path(self, path):
        self._current_path = path
        self._render()

    def set_source_path(self, path):
        self._source_path = path

    def present(self):
        self.window.present()

    def connect_select(self, callback):
        self._on_select = callback

    def _clear_list(self):
        self._row_paths.clear()
        while True:
            row = self.folder_list.get_first_child()
            if row is None:
                break
            self.folder_list.remove(row)

    def _parent_path(self, path):
        if '/' not in path:
            return ''
        return path.rsplit('/', 1)[0]

    def _get_direct_children(self, parent_path):
        children = set()
        prefix = parent_path + '/' if parent_path else ''
        for folder in self._folder_set:
            if folder == parent_path:
                continue
            if not folder.startswith(prefix):
                continue
            rest = folder[len(prefix):]
            if '/' in rest:
                child = prefix + rest.split('/')[0]
            else:
                child = folder
            if self._source_path and (child == self._source_path or child.startswith(self._source_path + '/')):
                continue
            children.add(child)
        return sorted(children)

    def _render(self):
        self._clear_list()
        self._last_activated_row = None
        display_path = '/' + self._current_path if self._current_path else '/'
        self.current_path_entry.set_text(display_path)

        if self._current_path:
            row = self._make_row('..', 'go-up-symbolic')
            self._row_paths[row] = '..'
            self.folder_list.append(row)
        else:
            row = self._make_row(_('(root)'), 'user-home-symbolic')
            self._row_paths[row] = ''
            self.folder_list.append(row)

        for child in self._get_direct_children(self._current_path):
            name = child.split('/')[-1]
            row = self._make_row(name, 'folder-symbolic')
            self._row_paths[row] = child
            self.folder_list.append(row)

    def _make_row(self, name, icon_name):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(6)
        box.set_margin_bottom(6)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        label = Gtk.Label(label=name)
        label.set_xalign(0)
        label.set_hexpand(True)

        box.append(icon)
        box.append(label)
        row.set_child(box)
        return row

    def _on_row_activated(self, listbox, row):
        path = self._row_paths.get(row)
        if path in ('..', ''):
            if path == '..':
                self._current_path = self._parent_path(self._current_path)
            else:
                self._current_path = ''
            self._last_activated_row = None
            self._render()
            return

        if self._source_path and (path == self._source_path or path.startswith(self._source_path + '/')):
            return

        if self._last_activated_row == row:
            if path and self._get_direct_children(path):
                self._current_path = path
                self._last_activated_row = None
                self._render()
        else:
            self._last_activated_row = row
            listbox.select_row(row)
            if path:
                self._current_path = path
            display_path = '/' + self._current_path if self._current_path else '/'
            self.current_path_entry.set_text(display_path)

    def _on_cancel_clicked(self, _button):
        self.window.destroy()

    def _on_select_clicked(self, _button):
        if self._on_select:
            self._on_select(self._current_path)
        self.window.destroy()
