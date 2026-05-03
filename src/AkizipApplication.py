
import sys
import gi
import gettext

try:
    _translation = gettext.translation('akizip', fallback=True)
    _ = _translation.gettext
except Exception:
    _ = lambda s: s

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import AkizipWindow


class AkizipApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='top.akizip.akizip',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
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

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(application_name='Akizip',
                                application_icon='top.akizip.akizip',
                                developer_name='akizip',
                                version='0.1.0',
                                # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
                                translator_credits = _('translator-credits'),
                                developers=['ckappgit','HungryNeko'],
                                copyright='© 2026 akizip',
                                license_type=Gtk.License.GPL_3_0)
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

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        group.set_title(_('Compression'))

        recommend_row = Adw.ActionRow()
        recommend_row.set_title(_('Use compression recommendations'))
        recommend_row.set_subtitle(_('Automatically choose 7-Zip parameters before compressing.'))
        recommend_switch = Gtk.Switch()
        recommend_switch.set_valign(Gtk.Align.CENTER)
        self.settings.bind(
            'use-compress-recommendation',
            recommend_switch,
            'active',
            Gio.SettingsBindFlags.DEFAULT,
        )
        recommend_row.add_suffix(recommend_switch)
        recommend_row.set_activatable_widget(recommend_switch)

        depth_row = Adw.ActionRow()
        depth_row.set_title(_('Scan depth'))
        depth_row.set_subtitle(_('Maximum folder levels to scan for recommendations.'))
        depth_spin = Gtk.SpinButton.new_with_range(0, 10, 1)
        depth_spin.set_valign(Gtk.Align.CENTER)
        depth_spin.set_value(self.settings.get_int('compress-scan-depth'))
        depth_spin.connect(
            'value-changed',
            lambda spin: self.settings.set_int('compress-scan-depth', spin.get_value_as_int()),
        )
        depth_row.add_suffix(depth_spin)
        depth_row.set_activatable_widget(depth_spin)

        group.add(recommend_row)
        group.add(depth_row)

        default_group = Adw.PreferencesGroup()
        default_group.set_title(_('Default compression parameters'))
        default_group.set_description(_('Used for normal compression and recommendation fallback.'))

        format_row = Adw.ActionRow()
        format_row.set_title(_('Format'))
        format_combo = Gtk.ComboBoxText()
        format_combo.append('7z', '7z')
        format_combo.append('zip', 'zip')
        default_format = self._settings_get_string('default-compress-format', '7z')
        format_combo.set_active_id(default_format if default_format in ('7z', 'zip') else '7z')
        format_combo.set_valign(Gtk.Align.CENTER)
        format_combo.connect(
            'changed',
            lambda combo: self._settings_set_string(
                'default-compress-format',
                combo.get_active_id() or '7z',
            ),
        )
        format_row.add_suffix(format_combo)
        format_row.set_activatable_widget(format_combo)

        level_row = Adw.ActionRow()
        level_row.set_title(_('Compression level'))
        level_combo = Gtk.ComboBoxText()
        for value, label in (
                ('0', _('Store')),
                ('1', _('Fastest')),
                ('3', _('Fast')),
                ('5', _('Normal')),
                ('7', _('Maximum')),
                ('9', _('Ultra'))):
            level_combo.append(value, label)
        default_level = str(self._settings_get_int('default-compress-level', 5))
        level_combo.set_active_id(default_level if default_level in ('0', '1', '3', '5', '7', '9') else '5')
        level_combo.set_valign(Gtk.Align.CENTER)
        level_combo.connect(
            'changed',
            lambda combo: self._settings_set_int(
                'default-compress-level',
                int(combo.get_active_id() or '5'),
            ),
        )
        level_row.add_suffix(level_combo)
        level_row.set_activatable_widget(level_combo)

        method_row = Adw.ActionRow()
        method_row.set_title(_('Algorithm'))
        method_combo = Gtk.ComboBoxText()
        for value, label in (
                ('default', _('Default')),
                ('LZMA', 'LZMA'),
                ('PPMd', 'PPMd'),
                ('BZip2', 'BZip2')):
            method_combo.append(value, label)
        default_method = self._settings_get_string('default-compress-method', 'default')
        method_combo.set_active_id(default_method if default_method in ('default', 'LZMA', 'PPMd', 'BZip2') else 'default')
        method_combo.set_valign(Gtk.Align.CENTER)
        method_combo.connect(
            'changed',
            lambda combo: self._settings_set_string(
                'default-compress-method',
                combo.get_active_id() or 'default',
            ),
        )
        method_row.add_suffix(method_combo)
        method_row.set_activatable_widget(method_combo)

        dictionary_row = Adw.ActionRow()
        dictionary_row.set_title(_('Dictionary size (MB)'))
        dictionary_row.set_subtitle(_('0 uses the 7-Zip default.'))
        dictionary_spin = Gtk.SpinButton.new_with_range(0, 1024, 1)
        dictionary_spin.set_valign(Gtk.Align.CENTER)
        dictionary_spin.set_value(self._settings_get_int('default-compress-dictionary-size', 0))
        dictionary_spin.connect(
            'value-changed',
            lambda spin: self._settings_set_int(
                'default-compress-dictionary-size',
                spin.get_value_as_int(),
            ),
        )
        dictionary_row.add_suffix(dictionary_spin)
        dictionary_row.set_activatable_widget(dictionary_spin)

        threads_row = Adw.ActionRow()
        threads_row.set_title(_('Threads'))
        threads_row.set_subtitle(_('0 uses the 7-Zip default.'))
        threads_spin = Gtk.SpinButton.new_with_range(0, 64, 1)
        threads_spin.set_valign(Gtk.Align.CENTER)
        threads_spin.set_value(self._settings_get_int('default-compress-threads', 0))
        threads_spin.connect(
            'value-changed',
            lambda spin: self._settings_set_int(
                'default-compress-threads',
                spin.get_value_as_int(),
            ),
        )
        threads_row.add_suffix(threads_spin)
        threads_row.set_activatable_widget(threads_spin)

        default_group.add(format_row)
        default_group.add(level_row)
        default_group.add(method_row)
        default_group.add(dictionary_row)
        default_group.add(threads_row)

        page.add(group)
        page.add(default_group)
        window.add(page)

        self._preferences_window = window
        window.present()

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
