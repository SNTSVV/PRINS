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

# model inference experiment variables
DATASET = 'dataset'
SYSTEMS = ['Hadoop', 'HDFS', 'Linux', 'Spark', 'Zookeeper', 'CoreSync', 'NGLClient', 'Oobelib', 'PDApp']
MINT_PARAM = 2
IGNORE_VALUES = False
SAVE_PDF = False  # saving pdf is time consuming, especially for large models
MINT_TIMEOUT = 3600  # sec
PRINS_NUM_WORKERS = 4  # multiprocessing
