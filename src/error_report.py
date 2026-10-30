# error_report.py
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
import base64
import json
import sys
import traceback

from gettext import gettext as _

from gi.repository import Adw, Gtk

# This error report upload method has been reviewed with Flathub
# administrator barthalion and confirmed to comply with Flathub's requirements.

REPORT_URL = 'https://debug.akizip.top/upload'
_ERROR_LIMIT = 4000


def _build_payload(version, error):
    """Build the diagnostic report JSON payload."""
    return json.dumps(
        {'version': version, 'error': error},
        ensure_ascii=False,
        indent=2,
    )


def build_report_url(version, error):
    """Build the upload URL with the report payload encoded as base64url.

    The JSON payload is base64-encoded with the URL-safe alphabet so it can
    be carried in a query parameter; the server turns it back into standard
    base64 with data.replace('-', '+').replace('_', '/').
    """
    encoded = base64.urlsafe_b64encode(
        _build_payload(version, error).encode('utf-8')
    ).decode('ascii')
    return '{}?data={}'.format(REPORT_URL, encoded)


def install_excepthook(version):
    """Install an excepthook that offers to upload uncaught tracebacks."""
    original_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        original_hook(exc_type, exc_value, exc_tb)
        try:
            _offer_report(version, exc_type, exc_value, exc_tb)
        except Exception:
            pass

    sys.excepthook = _hook


def _offer_report(version, exc_type, exc_value, exc_tb):
    app = Gtk.Application.get_default()
    window = app.get_active_window() if app is not None else None
    if window is None:
        return

    stack = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    error = stack if len(stack) <= _ERROR_LIMIT else '...[truncated]...\n' + stack[-_ERROR_LIMIT:]

    payload = _build_payload(version, error)

    body = _(
        'akizip encountered an unexpected error. Sending this diagnostic '
        'report helps us fix it. Reports are designed to be anonymous and '
        'are only accessible to core developers. They rarely contain '
        'sensitive data, but you can review the details before sending.'
    )

    dialog = Adw.AlertDialog.new(_('Send Error Report?'), None)

    scrolled = Gtk.ScrolledWindow(
        hscrollbar_policy=Gtk.PolicyType.NEVER,
        max_content_height=200,
        propagate_natural_height=True,
        hexpand=True,
        vexpand=True,
    )
    text_view = Gtk.TextView(
        buffer=Gtk.TextBuffer(text=payload),
        editable=False,
        cursor_visible=False,
        monospace=True,
        wrap_mode=Gtk.WrapMode.WORD_CHAR,
        top_margin=6,
        bottom_margin=6,
        left_margin=6,
        right_margin=6,
    )
    scrolled.set_child(text_view)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.append(Gtk.Label(label=body, wrap=True, xalign=0))
    box.append(scrolled)
    dialog.set_extra_child(box)

    dialog.add_response('close', _('_Close'))
    dialog.add_response('upload', _('_Upload Error Report'))
    dialog.set_response_appearance('upload', Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response('upload')
    dialog.set_close_response('close')

    def on_response(_dialog, response):
        if response == 'upload':
            _open_url(build_report_url(version, error))

    dialog.connect('response', on_response)
    dialog.present(window)


def _open_url(url):
    Gtk.UriLauncher.new(url).launch(None, None, None)
