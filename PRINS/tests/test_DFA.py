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
from src.automata.DFA import DFA


class TestDFA(unittest.TestCase):
    def setUp(self) -> None:
        self.component = 'test'
        self.ext_dfa = {'alphabet': {('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)},
                        'states': {'s0', 's1', 's2'}, 'initial_state': 's0', 'accepting_states': {'s0'},
                        'transitions': {
                            ('s0', ('a', 'var0=="1"')): 's1',
                            ('s0', ('a', 'var0!="1"')): 's2',
                            ('s1', ('b', None)): 's0',
                            ('s2', ('c', None)): 's0',
                            ('s1', ('c', None)): 's1'
                        }}

    def test_check_acceptance1(self):
        model = DFA(self.component, self.ext_dfa)
        l_vector = [
            {'ts': 1, 'tid': 'a', 'values': "['1']"},
            {'ts': 2, 'tid': 'b', 'values': "[]"},
        ]
        self.assertEqual(True, model.dfa_check_acceptance(l_vector))

        l_vector = [
            {'ts': 1, 'tid': 'a', 'values': "['2']"},
            {'ts': 2, 'tid': 'c', 'values': "[]"},
        ]
        self.assertEqual(True, model.dfa_check_acceptance(l_vector))

    def test_check_acceptance2(self):
        model = DFA(self.component, self.ext_dfa)
        l_vector = [
            {'ts': 1, 'tid': 'a', 'values': "['2']"}  # ends with a non-accepting state
        ]
        self.assertEqual(False, model.dfa_check_acceptance(l_vector))

    def test_check_acceptance3(self):
        model = DFA(self.component, self.ext_dfa)
        l_vector = [
            {'ts': 1, 'tid': 'c', 'values': "['2']"}  # no such transition from the initial state
        ]
        self.assertEqual(False, model.dfa_check_acceptance(l_vector))

    def test_make_guarded_transition(self):
        model = DFA(self.component, self.ext_dfa)
        self.assertEqual('s1', model.make_guarded_transition('s0', {'ts': None, 'tid': 'a', 'values': "['1']"}))
        self.assertEqual('s2', model.make_guarded_transition('s0', {'ts': None, 'tid': 'a', 'values': "['2']"}))
        self.assertEqual(None, model.make_guarded_transition('s0', {'ts': None, 'tid': 'b', 'values': "[]"}))
        self.assertEqual('s1', model.make_guarded_transition('s1', {'ts': None, 'tid': 'c', 'values': "[]"}))

    def test_shorten_states(self):
        model = DFA(self.component, self.ext_dfa)
        model.shorten_states()
        self.assertEqual({'0', '1', '2'}, model.states)
        self.assertEqual('0', model.initial_state)
        self.assertEqual({'0'}, model.accepting_states)
        self.assertEqual({('0', ('a', 'var0!="1"')): '2',
                          ('0', ('a', 'var0=="1"')): '1',
                          ('1', ('b', None)): '0',
                          ('1', ('c', None)): '1',
                          ('2', ('c', None)): '0'}, model.transitions)
        self.assertEqual(self.ext_dfa['alphabet'], model.alphabet)

    def test_shorten_states_consider_set_names(self):
        ext_dfa = {'alphabet': {('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)},
                   'states': {'{"s0"}', '{"s1"}', '{"s2","s3"}'}, 'initial_state': '{"s0"}', 'accepting_states': {'{"s0"}'},
                   'transitions': {
                       ('{"s0"}', ('a', 'var0=="1"')): '{"s1"}',
                       ('{"s0"}', ('a', 'var0!="1"')): '{"s2","s3"}',
                       ('{"s1"}', ('b', None)): '{"s0"}',
                       ('{"s2","s3"}', ('c', None)): '{"s0"}',
                       ('{"s1"}', ('c', None)): '{"s1"}'
                   }}
        model = DFA(self.component, ext_dfa)
        model.shorten_states(consider_set_names=True)
        self.assertEqual({'1', '2', '0'}, model.states)
        self.assertEqual('0', model.initial_state)
        self.assertEqual({'0'}, model.accepting_states)
        self.assertEqual({('0', ('a', 'var0!="1"')): '2',
                          ('0', ('a', 'var0=="1"')): '1',
                          ('1', ('b', None)): '0',
                          ('1', ('c', None)): '1',
                          ('2', ('c', None)): '0'}, model.transitions)
        self.assertEqual({('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)}, model.alphabet)
