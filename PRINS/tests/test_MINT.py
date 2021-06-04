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
import os
import tempfile
from src.utils.MINT import MINT


class TestMINT(unittest.TestCase):
    def test_MINT_run(self):
        system = 'test'
        input_file = os.path.join('tests', 'resources', 'MINT', 'test_mint_input.txt')
        with tempfile.TemporaryDirectory() as output_dir:
            extended_nfa = MINT.run(system=system, input_file=input_file, output_dir=output_dir)
            expected_nfa = {'accepting_states': {'0'},
                            'alphabet': {('d', None), ('e', None), ('a', None), ('c', None), ('b', None)},
                            'initial_state': '0',
                            'states': {'1', '0', '2'},
                            'transitions': {('0', ('a', None)): {'1', '2'},
                                            ('0', ('d', None)): {'0'},
                                            ('0', ('e', None)): {'0'},
                                            ('1', ('b', None)): {'0'},
                                            ('2', ('c', None)): {'0'}}}
            self.assertEqual(expected_nfa, extended_nfa)

    def test_MINT_run2(self):
        system = '[livetype]'
        input_file = os.path.join('tests', 'resources', 'MINT', f'{system}_mint_in.txt')
        with tempfile.TemporaryDirectory() as output_dir:
            MINT.run(system=system, input_file=input_file, output_dir=output_dir)

    def test_MINT_run3(self):
        system = 'Learner'
        input_file = os.path.join('tests', 'resources', 'MINT', f'{system}_mint_in.txt')
        with tempfile.TemporaryDirectory() as output_dir:
            extended_nfa = MINT.run(system=system, input_file=input_file, output_dir=output_dir)
            # ext_nfa = remove_end_marker(extended_nfa)
            # model = NFA(component, ext_nfa)
            # model.determinize()
            self.assertEqual({'accepting_states': {'3', '0', '1'},
                              'alphabet': {('E41', None), ('E20', None), ('__END__', None)},
                              'initial_state': '0',
                              'states': {'3', '2', '0', '1'},
                              'transitions': {('0', ('E20', None)): {'0'},
                                              ('0', ('E41', None)): {'2', '0'},
                                              ('0', ('__END__', None)): {'1'},
                                              ('2', ('__END__', None)): {'3'}}}, extended_nfa)
