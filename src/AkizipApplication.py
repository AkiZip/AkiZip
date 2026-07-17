# AkizipApplication.py
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
import gi

from gettext import gettext as _

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import AkizipWindow
from .ui.window import _host_path


class AkizipApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='top.akizip.akizip',
                         flags=Gio.ApplicationFlags.HANDLES_OPEN,
                         resource_base_path='/top/akizip/akizip')
        self.settings = Gio.Settings.new('top.akizip.akizip')
        self.add_action(self.settings.create_action('language'))

        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action)
        self.create_action('logs', self.on_logs_action)

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = AkizipWindow(application=self)
        win.present()

    def do_open(self, files, n_files, hint):
        """Called when files are opened from the desktop or file manager."""
        self.do_activate()
        win = self.props.active_window
        if win is None:
            return
        for i in range(n_files):
            file = files[i]
            path = file.get_path()
            if path is None:
                continue
            display_path = _host_path(path)
            if win._select_path(path, display_path):
                win._refresh_file_list()
                win._update_title()
                win._sync_address_bar()
            break

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(application_name='Akizip',
                                application_icon='top.akizip.akizip',
                                developer_name='akizip',
                                version='0.2.7',
                                # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
                                translator_credits = "weblate https://hosted.weblate.org/engage/akizip/",
                                developers=['ckappgit','HungryNeko'],
                                copyright='© 2026 akizip',
                                license_type=Gtk.License.GPL_3_0,
                                issue_url='https://github.com/AkiZip/AkiZip/issues')
        about.present(self.props.active_window)

    def on_preferences_action(self, widget, parameter):
        """Callback for the app.preferences action."""
        if getattr(self, '_preferences_window', None) is not None:
            self._preferences_window.present()
            return

        window = Adw.PreferencesWindow()
        window.set_title(_('Preferences'))
        active = self.props.active_window
        if active is not None:
            window.set_transient_for(active)
        window.set_modal(True)
        window.connect('close-request', self._on_preferences_closed)

        builder = Gtk.Builder.new_from_resource('/top/akizip/akizip/preferences.ui')
        page = builder.get_object('page')
        depth_spin = builder.get_object('depth_spin')
        format_combo = builder.get_object('format_combo')
        level_combo = builder.get_object('level_combo')
        method_combo = builder.get_object('method_combo')
        dictionary_spin = builder.get_object('dictionary_spin')
        threads_spin = builder.get_object('threads_spin')
        encrypt_names_switch = builder.get_object('encrypt_names_switch')
        timeout_spin = builder.get_object('timeout_spin')

        timeout_spin.set_value(self._settings_get_int('default-timeout', -1))
        timeout_spin.connect(
            'value-changed',
            lambda spin: self._on_timeout_changed(spin.get_value_as_int()),
        )

        depth_spin.set_value(self.settings.get_int('compress-scan-depth'))
        depth_spin.connect(
            'value-changed',
            lambda spin: self.settings.set_int('compress-scan-depth', spin.get_value_as_int()),
        )

        def _update_prefs_method_combo(fmt, method_combo):
            method_combo.remove_all()
            if fmt == '7z':
                items = [('default', _('Default')), ('LZMA2', 'LZMA2'), ('LZMA', 'LZMA'), ('PPMd', 'PPMd'), ('BZip2', 'BZip2')]
            elif fmt == 'tar':
                items = [('GNU', 'GNU'), ('POSIX', 'POSIX')]
            elif fmt == 'zip':
                items = [('Deflate', 'Deflate'), ('Deflate64', 'Deflate64'), ('BZip2', 'BZip2'), ('LZMA', 'LZMA'), ('PPMd', 'PPMd')]
            else:
                items = []
            for item_id, label in items:
                method_combo.append(item_id, label)
            return items

        def on_prefs_format_changed(combo):
            fmt = combo.get_active_id() or '7z'
            self._settings_set_string('default-compress-format', fmt)
            current_id = method_combo.get_active_id()
            items = _update_prefs_method_combo(fmt, method_combo)
            if current_id and any(i[0] == current_id for i in items):
                method_combo.set_active_id(current_id)
            elif items:
                method_combo.set_active_id(items[0][0])
            level_combo.set_sensitive(fmt in ('7z', 'zip'))
            method_combo.set_sensitive(fmt in ('7z', 'tar', 'zip'))
            dictionary_spin.set_sensitive(fmt == '7z')
            threads_spin.set_sensitive(fmt in ('7z', 'zip'))
            encrypt_names_switch.set_sensitive(fmt == '7z')
            if fmt != '7z':
                encrypt_names_switch.set_active(False)

        default_format = self._settings_get_string('default-compress-format', '7z')
        _VALID_FORMATS = ('7z', 'tar', 'zip')
        format_combo.set_active_id(default_format if default_format in _VALID_FORMATS else '7z')
        format_combo.connect('changed', on_prefs_format_changed)

        default_level = str(self._settings_get_int('default-compress-level', 5))
        level_combo.set_active_id(default_level if default_level in ('0', '1', '3', '5', '7', '9') else '5')
        level_combo.connect(
            'changed',
            lambda combo: self._settings_set_int(
                'default-compress-level',
                int(combo.get_active_id() or '5'),
            ),
        )

        on_prefs_format_changed(format_combo)
        default_method = self._settings_get_string('default-compress-method', 'default')
        fmt = format_combo.get_active_id() or '7z'
        valid_methods = {
            '7z': ('default', 'LZMA2', 'LZMA', 'PPMd', 'BZip2'),
            'tar': ('GNU', 'POSIX'),
            'zip': ('Deflate', 'Deflate64', 'BZip2', 'LZMA', 'PPMd'),
        }
        if default_method in valid_methods.get(fmt, ()):
            method_combo.set_active_id(default_method)
        method_combo.connect(
            'changed',
            lambda combo: self._settings_set_string(
                'default-compress-method',
                combo.get_active_id() or 'default',
            ),
        )

        dictionary_spin.set_value(self._settings_get_int('default-compress-dictionary-size', 0))
        dictionary_spin.connect(
            'value-changed',
            lambda spin: self._settings_set_int(
                'default-compress-dictionary-size',
                spin.get_value_as_int(),
            ),
        )

        threads_spin.set_value(self._settings_get_int('default-compress-threads', 0))
        threads_spin.connect(
            'value-changed',
            lambda spin: self._settings_set_int(
                'default-compress-threads',
                spin.get_value_as_int(),
            ),
        )

        encrypt_names_switch.set_active(self._settings_get_boolean('default-compress-encrypt-names', False))
        encrypt_names_switch.connect(
            'notify::active',
            lambda switch, pspec: self._settings_set_boolean(
                'default-compress-encrypt-names',
                switch.get_active(),
            ),
        )

        window.add(page)

        self._preferences_window = window
        window.present()

    def _on_timeout_changed(self, value):
        self._settings_set_int('default-timeout', value)
        if hasattr(self, 'job_queue'):
            self.job_queue.default_timeout = value

    def _on_preferences_closed(self, window):
        self._preferences_window = None
        return False

    def _settings_get_string(self, key, fallback):
        try:
            return self.settings.get_string(key)
        except Exception:
            return fallback

    def _settings_get_int(self, key, fallback):
        try:
            return self.settings.get_int(key)
        except Exception:
            return fallback

    def _settings_set_string(self, key, value):
        try:
            self.settings.set_string(key, value)
        except Exception:
            pass

    def _settings_set_int(self, key, value):
        try:
            self.settings.set_int(key, value)
        except Exception:
            pass

    def _settings_get_boolean(self, key, fallback):
        try:
            return self.settings.get_boolean(key)
        except Exception:
            return fallback

    def _settings_set_boolean(self, key, value):
        try:
            self.settings.set_boolean(key, value)
        except Exception:
            pass

    def on_logs_action(self, *args):
        """Callback for the app.logs action."""
        win = self.props.active_window
        if win is not None and hasattr(win, '_show_log_window'):
            win._show_log_window()

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)
