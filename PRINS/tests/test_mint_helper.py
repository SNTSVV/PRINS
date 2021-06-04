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
from src.main.mint_helper import *


class TestMINTHelper(unittest.TestCase):
    def setUp(self) -> None:
        self.component = 'test_component'
        self.l_vectors = {
            'log1': [
                {'ts': '01', 'tid': 'e1', 'values': "['X', 'A']"},
                {'ts': '02', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '03', 'tid': 'e0', 'values': "[]"},
                {'ts': '04', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '05', 'tid': 'e0', 'values': "[]"},
                {'ts': '06', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '07', 'tid': 'e0', 'values': "[]"},
                {'ts': '08', 'tid': 'e1', 'values': "['X', 'A']"},
            ],
            'log2': [
                {'ts': '01', 'tid': 'e1', 'values': "['X', 'A']"},
                {'ts': '02', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '03', 'tid': 'e0', 'values': "[]"},
                {'ts': '04', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '05', 'tid': 'e0', 'values': "[]"},
                {'ts': '06', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '07', 'tid': 'e0', 'values': "[]"},
                {'ts': '08', 'tid': 'e1', 'values': "['X', 'A']"},
            ],
            'log3': [
                {'ts': '01', 'tid': 'e1', 'values': "['X', 'A']"},
                {'ts': '02', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '03', 'tid': 'e0', 'values': "[]"},
                {'ts': '04', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '05', 'tid': 'e0', 'values': "[]"},
                {'ts': '06', 'tid': 'e1', 'values': "['Y', 'A']"},
                {'ts': '07', 'tid': 'e0', 'values': "[]"},
                {'ts': '08', 'tid': 'e1', 'values': "['X', 'A']"},
            ],
        }

    def test_prepare_mint_input_from_l_vectors(self):
        with tempfile.TemporaryDirectory() as output_dir:
            mint_input = prepare_mint_input_from_l_vectors(self.component, self.l_vectors, output_dir)
            contents = list()
            with open(mint_input, 'r') as f:
                for line in f:
                    contents.append(line)
            self.assertEqual(['types\n',
                              'e0\n',
                              'e1 var0:S var1:S\n',
                              '__END__\n',
                              'trace\n',
                              'e1 X A\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 X A\n',
                              '__END__\n',
                              'trace\n',
                              'e1 X A\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 X A\n',
                              '__END__\n',
                              'trace\n',
                              'e1 X A\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 Y A\n',
                              'e0\n',
                              'e1 X A\n',
                              '__END__\n'],
                             contents)

    def test_infer_model(self):
        if os.system('java -version') != 0:
            print('No java installed: skip this test')
            pass
        else:
            with tempfile.TemporaryDirectory() as output_dir:
                model = infer_model_by_mint(self.component, self.l_vectors, output_dir, k=2)
                self.assertEqual({'1', '0', '3', '4', '2'}, model.states)
                self.assertEqual(1, len(model.accepting_states))
                self.assertEqual('0', model.initial_state)
                self.assertEqual({('e1', None), ('e0', None)}, model.alphabet)
                self.assertEqual(5, len(model.transitions))

    def test_infer_model2(self):
        if os.system('java -version') != 0:
            print('No java installed: skip this test')
            pass
        else:
            system = 'Learner'
            input_file = os.path.join('tests', 'resources', 'MINT', f'{system}_mint_in.txt')
            with tempfile.TemporaryDirectory() as output_dir:
                extended_nfa = MINT.run(system=system, input_file=input_file, output_dir=output_dir)
                ext_nfa = remove_end_marker(extended_nfa)
                model = NFA(system, ext_nfa)
                model = model.heuristic_determinize()
                self.assertEqual('0', model.initial_state)
                self.assertEqual({'0'}, model.states)
                self.assertEqual({'0'}, model.accepting_states)
                self.assertEqual({('E20', None), ('E41', None)}, model.alphabet)
                self.assertEqual({('0', ('E20', None)): '0', ('0', ('E41', None)): '0'}, model.transitions)
