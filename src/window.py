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

from gi.repository import Adw
from gi.repository import Gtk

@Gtk.Template(resource_path='/top/akizip/akizip/window.ui')
class AkizipWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'AkizipWindow'

    add_button =Gtk.Template.Child()

    @Gtk.Template.Callback()
    def butadd(self,button):
        result = subprocess.run(['/app/bin/7zz'], capture_output=True, text=True, check=False)
        output = (result.stdout + result.stderr).strip()
        print(output.split('\n')[0] if output else '7zz output empty')



    def __init__(self, **kwargs):
        super().__init__(**kwargs)
