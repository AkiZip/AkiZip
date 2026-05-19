from gettext import gettext as _
from pathlib import PurePosixPath

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango


_CSS_PROVIDER = None


def _ensure_css():
    global _CSS_PROVIDER
    if _CSS_PROVIDER is not None:
        return

    _CSS_PROVIDER = Gtk.CssProvider()
    _CSS_PROVIDER.load_from_data(b"""
    dropdown.conflict-skip {
      color: #2f5f91;
      background-color: rgba(47, 95, 145, 0.12);
    }
    dropdown.conflict-overwrite {
      color: #9b4a4a;
      background-color: rgba(155, 74, 74, 0.12);
    }
    """)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        _CSS_PROVIDER,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class ExtractConflictDialog:
    def __init__(self, conflicts):
        _ensure_css()
        self._conflicts = {
            PurePosixPath(str(path).replace('\\', '/')): value
            for path, value in conflicts.items()
        }
        self._rows = []
        self._updating_checks = False
        self._window = Gtk.Window()
        self._window.set_title(_('Existing Files'))
        self._window.set_modal(True)
        self._window.set_default_size(720, 460)
        self._build()

    def present(self, parent, on_confirm):
        self._on_confirm = on_confirm
        self._window.set_transient_for(parent)
        self._window.present()

    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)
        self._window.set_child(root)

        title = Gtk.Label(xalign=0)
        title.set_markup('<b>{}</b>'.format(_('Some extracted items already exist.')))
        root.append(title)

        subtitle = Gtk.Label(xalign=0)
        subtitle.set_wrap(True)
        subtitle.set_label(_('Choose which existing files should be overwritten or skipped before extracting.'))
        root.append(subtitle)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        root.append(scroller)

        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class('boxed-list')
        scroller.set_child(self._list)

        for item in self._build_items():
            self._append_row(item)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        root.append(buttons)

        replace_btn = Gtk.Button(label=_('Overwrite Selected'))
        ignore_btn = Gtk.Button(label=_('Skip Selected'))
        cancel_btn = Gtk.Button(label=_('Cancel'))
        confirm_btn = Gtk.Button(label=_('Confirm'))
        confirm_btn.add_css_class('suggested-action')

        replace_btn.connect('clicked', lambda _btn: self._set_selected_action('overwrite'))
        ignore_btn.connect('clicked', lambda _btn: self._set_selected_action('skip'))
        cancel_btn.connect('clicked', lambda _btn: self._window.close())
        confirm_btn.connect('clicked', self._confirm)

        buttons.append(replace_btn)
        buttons.append(ignore_btn)
        buttons.append(cancel_btn)
        buttons.append(confirm_btn)

    def _build_items(self):
        items = {}
        for path, value in self._conflicts.items():
            isFile = value[0]
            parts = path.parts
            current = PurePosixPath()
            for part in parts[:-1]:
                current = current / part
                items.setdefault(current, {
                    'path': current,
                    'is_file': False,
                    'name': current.name,
                    'depth': len(current.parts) - 1,
                    'action': 'skip',
                    'real_conflict': current in self._conflicts,
                })
            items[path] = {
                'path': path,
                'is_file': isFile,
                'name': value[1],
                'depth': len(parts) - 1,
                'action': 'skip',
                'real_conflict': True,
            }

        return [
            items[path]
            for path in sorted(items, key=lambda item: str(item).lower())
        ]

    def _append_row(self, item):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(6 + item['depth'] * 18)
        box.set_margin_end(6)
        row.set_child(box)

        check = Gtk.CheckButton()
        check.connect('toggled', self._on_check_toggled, item)
        box.append(check)

        icon_name = 'text-x-generic-symbolic' if item['is_file'] else 'folder-symbolic'
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        box.append(icon)

        label = Gtk.Label(xalign=0)
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_label(str(item['path']))
        box.append(label)

        action_combo = Gtk.DropDown.new_from_strings([
            _('Overwrite'),
            _('Skip'),
        ])
        action_combo.set_size_request(140, -1)
        action_combo.connect('notify::selected', self._on_action_selected, item)
        box.append(action_combo)

        item['check'] = check
        item['action_combo'] = action_combo
        self._rows.append(item)
        self._update_action_combo(item)
        self._list.append(row)

    def _on_check_toggled(self, check, item):
        if self._updating_checks or item['is_file']:
            return

        self._updating_checks = True
        try:
            for child in self._descendants(item):
                child['check'].set_active(check.get_active())
        finally:
            self._updating_checks = False

    def _descendants(self, item):
        prefix = str(item['path']).rstrip('/') + '/'
        return [
            child for child in self._rows
            if str(child['path']).startswith(prefix)
        ]

    def _set_selected_action(self, action):
        for item in self._rows:
            if item['check'].get_active():
                self._set_action(item, action)

    def _set_action(self, item, action):
        item['action'] = action
        self._update_action_combo(item)
        if not item['is_file']:
            for child in self._descendants(item):
                child['action'] = action
                self._update_action_combo(child)

    def _update_action_combo(self, item):
        index = 0 if item['action'] == 'overwrite' else 1
        combo = item.get('action_combo')
        if combo is None:
            return
        if combo.get_selected() != index:
            combo.set_selected(index)
        if item['action'] == 'overwrite':
            combo.remove_css_class('conflict-skip')
            combo.add_css_class('conflict-overwrite')
        else:
            combo.remove_css_class('conflict-overwrite')
            combo.add_css_class('conflict-skip')

    def _on_action_selected(self, combo, _pspec, item):
        action = 'skip' if combo.get_selected() == 1 else 'overwrite'
        if item['action'] == action:
            return
        self._set_action(item, action)

    def _confirm(self, _button):
        ignored = []
        for item in self._rows:
            if item['action'] != 'skip' or not item['is_file']:
                continue
            if item['path'] in self._conflicts:
                ignored.append(str(item['path']))

        self._window.close()
        if hasattr(self, '_on_confirm') and self._on_confirm is not None:
            self._on_confirm(ignored)
