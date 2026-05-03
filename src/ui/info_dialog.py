from gettext import gettext as _

from gi.repository import Gtk

from ..plugins.status import _status


class InfoDialogMixin:
    def _show_info_dialog(self, selected):
        app = self.get_application()
        if app is None or not hasattr(app, 'system'):
            self._append_log(_('System state not found'), str(selected), _status.ERROR)
            return

        info = app.system.info()
        dialog, grid = self._create_info_dialog(info)
        dialog.present()

        if not info['is_archive']:
            return

        command = getattr(app, 'commands', {}).get('archive.info')
        job_queue = getattr(app, 'job_queue', None)
        if command is None or job_queue is None:
            self._add_info_row(grid, _('Archive'), _('Archive information is unavailable.'))
            return

        loading_row = self._add_info_row(grid, _('Archive'), _('Reading...'))
        job_queue.submit(
            command,
            (selected,),
            on_success=lambda output: self._update_archive_info(grid, loading_row, output),
            on_error=lambda error: self._update_info_row(loading_row, str(error)),
            timeout=60,
            task_id='archive.info',
            msg=_('Read archive information from ') + selected.name,
        )

    def _create_info_dialog(self, info):
        dialog = Gtk.Window()
        dialog.set_title(_('Info'))
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        dialog.set_default_size(720, 520)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)

        title = Gtk.Label(label=info['name'] or _('Info'))
        title.set_xalign(0)
        title.set_wrap(True)
        title.set_max_width_chars(50)
        title.add_css_class('title-3')
        root.append(title)

        grid = Gtk.Grid(column_spacing=12, row_spacing=8)
        grid._akizip_next_row = 0
        grid.set_vexpand(True)

        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True)
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(grid)
        root.append(scroller)

        close_button = Gtk.Button(label=_('Close'))
        close_button.set_halign(Gtk.Align.END)
        close_button.connect('clicked', lambda *_: dialog.close())
        root.append(close_button)

        dialog.set_child(root)

        self._add_info_row(grid, _('Name'), info['name'], copy_value=info['name'])
        self._add_info_row(grid, _('Path'), info['path'], copy_value=info['path'])
        self._add_info_row(grid, _('Type'), self._system_kind_label(info))
        if info['is_file']:
            self._add_info_row(grid, _('Size'), self._format_size(info['size']))
        self._add_info_row(grid, _('Can compress'), self._yes_no(info['can_compress']))
        self._add_info_row(grid, _('Can extract'), self._yes_no(info['can_extract']))

        return dialog, grid

    def _add_info_row(self, grid, name, value, copy_value=None):
        row = grid._akizip_next_row
        grid._akizip_next_row += 1

        name_label = Gtk.Label(label=name)
        name_label.set_xalign(0)
        name_label.add_css_class('dim-label')

        value_label = Gtk.Label(label=str(value))
        value_label.set_xalign(0)
        value_label.set_wrap(True)
        value_label.set_max_width_chars(50)
        value_label.set_selectable(True)
        value_label.set_hexpand(True)

        value_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        value_box.set_hexpand(True)
        value_box.append(value_label)

        if copy_value is not None:
            copy_button = Gtk.Button()
            copy_button.set_icon_name('edit-copy-symbolic')
            copy_button.set_tooltip_text(_('Copy'))
            copy_button.set_valign(Gtk.Align.CENTER)
            copy_button.connect('clicked', lambda *_: self._copy_info_value(copy_value))
            value_box.append(copy_button)

        grid.attach(name_label, 0, row, 1, 1)
        grid.attach(value_box, 1, row, 1, 1)
        return value_label

    def _copy_info_value(self, value):
        self.get_clipboard().set(str(value))
        if hasattr(self, '_show_notification'):
            self._show_notification(_('Copied to clipboard'), _status.FINISHED)

    def _update_info_row(self, value_label, value):
        value_label.set_text(str(value))

    def _update_archive_info(self, grid, loading_row, output):
        archive_info = self._parse_archive_info(output)
        if not archive_info:
            self._update_info_row(loading_row, _('No archive information found.'))
            return

        self._update_info_row(loading_row, _('Loaded'))
        for key, label in (
            ('Type', _('Archive type')),
            ('Physical Size', _('Archive size')),
            ('Headers Size', _('Headers size')),
            ('Method', _('Method')),
            ('Solid', _('Solid')),
            ('Blocks', _('Blocks')),
        ):
            if key in archive_info:
                self._add_info_row(grid, label, archive_info[key])

    def _parse_archive_info(self, output):
        info = {}
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith('-'):
                if info:
                    break
                continue
            if ' = ' not in line:
                continue

            key, value = line.split(' = ', 1)
            if key == 'Path' and info:
                break
            info[key] = value
        return info

    def _system_kind_label(self, info):
        if info['is_archive']:
            return _('Archive file')
        if info['is_folder']:
            return _('Folder')
        if info['is_file']:
            return _('File')
        return _('Unknown')

    def _format_size(self, size):
        units = (_('B'), _('KB'), _('MB'), _('GB'))
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == units[0]:
                    return f'{int(value)} {unit}'
                return f'{value:.1f} {unit}'
            value /= 1024
        return str(size)

    def _yes_no(self, value):
        return _('Yes') if value else _('No')
