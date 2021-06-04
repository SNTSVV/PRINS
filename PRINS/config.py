"""
This file is part of PRINS.

Copyright (C) 2021 University of Luxembourg

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

SPDX-FileType: SOURCE
SPDX-FileCopyrightText: 2021 University of Luxembourg
SPDX-License-Identifier: GPL-3.0-or-later
"""

settings = {
    'Hadoop': {
        # mandatory
        'log_format': r'<date> <time> <level> \[<module>\] <component>: <message>',
        'log_dir': 'dataset_example/Hadoop/logs',
        'template_dir': 'dataset_example/Hadoop/templates',
        'output_dir': './output/Hadoop',

        # optional
        'parser': 'Drain',
        'pre_patterns': [r'(\d+\.){3}\d+'],
        'file_ext': '.log',
        'module_filtering': 'main'
    },
}

STD_TIMEOUT = 1800
