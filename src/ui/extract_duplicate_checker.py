# extract_duplicate_checker.py
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
from gi.repository import GLib, Adw


class ExtractDuplicateChecker:
    """Check destination files for duplicates before extraction.

    Runs single-threaded on the GTK main thread. For each existing file,
    presents a dialog with Skip / Overwrite / Skip All / Overwrite All.
    The final skip list is delivered via on_finished.
    """

    def __init__(self, parent_window, output_dir, file_list, on_finished):
        self.parent = parent_window
        self.output_dir = Path(output_dir)
        self.file_list = file_list
        self.on_finished = on_finished
        self.skip_list = []
        self.auto_skip = False
        self.auto_overwrite = False
        self.index = 0
        self.dialog = None
        self.current_path = None

    def start(self):
        if not self.file_list:
            self._finish()
            return
        GLib.idle_add(self._check_next)

    def _check_next(self):
        while self.index < len(self.file_list):
            internal_path = self.file_list[self.index]
            self.index += 1
            dest_path = self.output_dir / internal_path.replace('\\', '/')
            if os.path.exists(str(dest_path)):
                if self.auto_skip:
                    self.skip_list.append(internal_path)
                    continue
                if self.auto_overwrite:
                    continue
                self.current_path = internal_path
                self._ensure_dialog()
                self._update_dialog(dest_path)
                self.dialog.present(self.parent)
                return False
        self._finish()
        return False

    def _ensure_dialog(self):
        if self.dialog is not None:
            return
        self.dialog = Adw.AlertDialog.new('', None)
        self.dialog.add_response('skip_all', _('Skip _All'))
        self.dialog.add_response('overwrite_all', _('O_verwrite All'))
        self.dialog.add_response('skip', _('_Skip'))
        self.dialog.add_response('overwrite', _('_Overwrite'))
        self.dialog.set_default_response('overwrite')
        self.dialog.set_close_response('skip')
        self.dialog.set_response_appearance(
            'overwrite', Adw.ResponseAppearance.SUGGESTED
        )
        self.dialog.connect('response', self._on_response)

    def _update_dialog(self, dest_path):
        self.dialog.set_heading(_('Conflict handling'))
        self.dialog.set_body(
            _('The file "{file}" already exists in the destination.').format(
                file=dest_path.name
            )
        )

    def _on_response(self, _dialog, response):
        if response == 'skip':
            self.skip_list.append(self.current_path)
        elif response == 'skip_all':
            self.auto_skip = True
            self.skip_list.append(self.current_path)
        elif response == 'overwrite_all':
            self.auto_overwrite = True
        # 'overwrite': do nothing for the current file.
        GLib.idle_add(self._check_next)

    def _finish(self):
        if self.dialog is not None:
            self.dialog.close()
        self.on_finished(self.skip_list or None)
