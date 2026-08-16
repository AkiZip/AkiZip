# context_menu.py
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
def context_menu_state(can_modify, can_extract, selected_count):
    """Compute the enabled state of each file list context menu action.

    Args:
        can_modify: The selected archive can be modified (full-feature
            format, not nested).
        can_extract: An archive is selected and supports extraction.
        selected_count: Number of selected entries. 0 means the click
            landed on blank space (or the '..' row), where only add-file
            and new-folder are allowed. 1 or more means entries selected.

    Returns:
        A dict mapping action name to enabled bool. When the format is not
        editable (can_modify is False), every modifying action is disabled.
    """
    has_selection = selected_count > 0
    return {
        'extract-selected': bool(has_selection and can_extract),
        'move-selected': bool(has_selection and can_modify),
        'rename-selected': bool(has_selection and can_modify),
        'delete-selected': bool(has_selection and can_modify),
        'add-file': bool(can_modify),
        'new-folder': bool(can_modify),
    }
