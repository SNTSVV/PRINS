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

import unittest
import tempfile
import pandas as pd
from src.main.PRINS import PRINS
from src.utils.common import convert_df_into_l_vectors


class TestPRINS(unittest.TestCase):
    def setUp(self) -> None:
        self.system = 'test_system'
        self.logs_csv = 'tests/resources/test_PRINS_logs.csv'

    def test_project(self):
        with tempfile.TemporaryDirectory() as output_dir:
            instance = PRINS(self.system, self.logs_csv, output_dir)
            component_logs = instance.project()
            self.assertEqual({'comp1': {1: [{'ts': 1, 'tid': 'E1', 'values': "['x']", 'component': 'comp1'},
                                            {'ts': 3, 'tid': 'E1', 'values': "['y']", 'component': 'comp1'},
                                            {'ts': 4, 'tid': 'E3', 'values': '[]', 'component': 'comp1'}],
                                        2: [{'ts': 1, 'tid': 'E1', 'values': "['z']", 'component': 'comp1'}]},
                              'comp2': {1: [{'ts': 2, 'tid': 'E2', 'values': '[]', 'component': 'comp2'}],
                                        2: [{'ts': 3, 'tid': 'E2', 'values': '[]', 'component': 'comp2'}]},
                              'comp3': {2: [{'ts': 2, 'tid': 'E4', 'values': '[]', 'component': 'comp3'}]}},
                             component_logs)

    def test_partition_log_by_component(self):
        logs_df = pd.read_csv(self.logs_csv, dtype={'tid': str})
        l_vectors = convert_df_into_l_vectors(logs_df, include_component=True)
        partitioned_log = PRINS.partition_log_by_component(l_vectors[1])
        self.assertEqual([
            ('comp1', [{'ts': 1, 'tid': 'E1', 'values': "['x']", 'component': 'comp1'}]),
            ('comp2', [{'ts': 2, 'tid': 'E2', 'values': '[]', 'component': 'comp2'}]),
            ('comp1', [{'ts': 3, 'tid': 'E1', 'values': "['y']", 'component': 'comp1'},
                       {'ts': 4, 'tid': 'E3', 'values': '[]', 'component': 'comp1'}])], partitioned_log)
        partitioned_log = PRINS.partition_log_by_component(l_vectors[2])
        self.assertEqual([
            ('comp1', [{'component': 'comp1', 'tid': 'E1', 'ts': 1, 'values': "['z']"}]),
            ('comp3', [{'component': 'comp3', 'tid': 'E4', 'ts': 2, 'values': '[]'}]),
            ('comp2', [{'component': 'comp2', 'tid': 'E2', 'ts': 3, 'values': '[]'}])], partitioned_log)

    def test_partition_log_by_component_empty(self):
        self.assertEqual([], PRINS.partition_log_by_component([]))

    def test_run(self):
        with tempfile.TemporaryDirectory() as output_dir:
            instance = PRINS(self.system, self.logs_csv, output_dir)
            instance.run(save_pdf=False)  # should be completed without errors
