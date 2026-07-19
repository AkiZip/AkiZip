# password.py
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
def is_password_error(error):
    """Check if a 7zz error is password-related.

    Args:
        error: An exception or string containing the error message.

    Returns:
        True if the error indicates a missing or wrong password.
    """
    error_str = str(error)
    return (
        'Wrong password' in error_str
        or 'Data Error in encrypted file' in error_str
        or 'Enter password' in error_str
        or 'Break signaled' in error_str
    )
