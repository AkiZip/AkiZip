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

import subprocess

from gettext import gettext as _

from gi.repository import Adw
from gi.repository import Gtk

@Gtk.Template(resource_path='/top/akizip/akizip/window.ui')
class AkizipWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'AkizipWindow'

    add_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def butadd(self, button):
        result = subprocess.run(['/app/bin/7zz'], capture_output=True, text=True, check=False)
        output = (result.stdout + result.stderr).strip()
        print(output.split('\n')[0] if output else '7zz output empty')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        app = self.get_application()
        if app is not None and hasattr(app, 'settings'):
            self._initial_language = app.settings.get_string('language')
            app.settings.connect('changed::language', self._on_language_changed)

    def _on_language_changed(self, settings, key):
        if settings.get_string(key) == self._initial_language:
            return
        toast = Adw.Toast.new(_('Restart the application to apply the new language.'))
        toast.set_timeout(5)
        self.toast_overlay.add_toast(toast)
