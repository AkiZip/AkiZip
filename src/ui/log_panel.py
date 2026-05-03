from gettext import gettext as _

from gi.repository import Adw
from gi.repository import GLib
from gi.repository import Gtk

from ..plugins.status import _status


class LogPanelMixin:
    def _ensure_log_window(self):
        if getattr(self, 'log_window', None) is not None:
            return

        self.log_list = Gtk.ListBox()
        self.log_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.log_list.set_margin_start(6)
        self.log_list.set_margin_end(6)
        self.log_list.set_margin_top(6)
        self.log_list.set_margin_bottom(6)

        self.log_scroller = Gtk.ScrolledWindow()
        self.log_scroller.set_hexpand(True)
        self.log_scroller.set_vexpand(True)
        self.log_scroller.set_child(self.log_list)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        toolbar_view.set_content(self.log_scroller)

        self.log_window = Adw.Window()
        self.log_window.set_title(_('Logs'))
        self.log_window.set_transient_for(self)
        self.log_window.set_modal(False)
        self.log_window.set_destroy_with_parent(True)
        self.log_window.set_default_size(420, 520)
        self.log_window.set_hide_on_close(True)
        self.log_window.set_content(toolbar_view)

    def _show_log_window(self):
        self._ensure_log_window()
        self.log_window.present()

    def _append_log(self, summary, content=None, state=_status.PENDING, handle=None):
        self._ensure_log_window()

        expander = Gtk.Expander()
        expander.set_margin_top(8)
        expander.set_margin_bottom(8)
        expander.set_margin_start(10)
        expander.set_margin_end(10)
        expander.set_label_widget(self._log_header(summary, state, handle))

        if content:
            buffer = Gtk.TextBuffer()
            buffer.set_text(content)

            text_view = Gtk.TextView(buffer=buffer)
            text_view.set_editable(False)
            text_view.set_monospace(True)
            text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            text_view.set_top_margin(6)
            text_view.set_bottom_margin(6)
            text_view.set_left_margin(6)
            text_view.set_right_margin(6)

            expander.set_child(text_view)

        frame = Gtk.Frame()
        frame.set_child(expander)
        frame.set_margin_top(5)
        frame.set_margin_bottom(5)
        frame.set_margin_start(4)
        frame.set_margin_end(4)

        row = Gtk.ListBoxRow()
        row.set_child(frame)
        self.log_list.insert(row, 0)
        GLib.idle_add(self._scroll_log_to_top)
        return row

    def _log_header(self, summary, state, handle):
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        status_label = Gtk.Label()
        status_label.set_markup(self._status_markup(state))
        header.append(status_label)

        summary_label = Gtk.Label(label=summary)
        summary_label.set_xalign(0)
        summary_label.set_hexpand(True)
        header.append(summary_label)

        if handle is not None and state in (_status.PENDING, _status.WORKING):
            stop_button = Gtk.Button(icon_name='process-stop-symbolic')
            stop_button.set_tooltip_text(_('Cancel'))
            stop_button.connect('clicked', self._cancel_job, handle, summary_label)
            header.append(stop_button)

        return header

    def _cancel_job(self, button, handle, summary_label):
        handle.cancel()
        button.set_sensitive(False)
        summary_label.set_text(_('Cancelling...'))

    def _status_markup(self, state):
        labels = {
            _status.WORKING: (_('Running'), '#1c71d8'),
            _status.FINISHED: (_('Done'), '#2ec27e'),
            _status.WARNING: (_('Warning'), '#e5a50a'),
            _status.TIMEOUT: (_('Timeout'), '#e66100'),
            _status.ERROR: (_('Error'), '#c01c28'),
            _status.CANCELLED: (_('Cancelled'), '#77767b'),
            _status.PENDING: (_('Pending'), '#77767b'),
        }
        label, color = labels.get(state, (state.value, '#77767b'))
        return f'<span foreground="{color}" weight="bold">{GLib.markup_escape_text(label)}</span>'

    def _remove_pending_log(self, log_id):
        self._pending_handles.pop(log_id, None)
        row = self._pending_logs.pop(log_id, None)
        if row is not None:
            self.log_list.remove(row)
            return True
        return False

    def _scroll_log_to_top(self):
        adjustment = self.log_scroller.get_vadjustment()
        adjustment.set_value(adjustment.get_lower())
        return GLib.SOURCE_REMOVE
