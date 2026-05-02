from gettext import gettext as _

from gi.repository import GLib
from gi.repository import Gtk

from ..plugins.status import _status


class LogPanelMixin:
    def _append_log(self, summary, content=None, state=_status.PENDING, handle=None):
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
