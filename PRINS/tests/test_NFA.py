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

import os
import tempfile
import unittest
import copy
from src.automata.NFA import NFA
from src.main.mint_helper import run_mint_using_mint_input


class TestNFA(unittest.TestCase):

    def setUp(self) -> None:
        self.component = 'test'
        self.ext_nfa = {'alphabet': {('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)},
                        'states': {'0', '2', '1'}, 'initial_state': '0', 'accepting_states': {'0'},
                        'transitions': {
                            ('0', ('a', 'var0=="1"')): {'1'},
                            ('0', ('a', 'var0!="1"')): {'2'},
                            ('1', ('b', None)): {'0'},
                            ('2', ('c', None)): {'0'},
                            ('1', ('c', None)): {'1'}
                        }}
        self.ext_nfa2 = {
            'alphabet': {('a', None), ('b', None), ('c', None), ('d', None)},
            'states': {'s0', 's1', 's2', 's3'},
            'initial_state': 's0',
            'accepting_states': {'s3'},
            'transitions': {
                ('s0', ('a', None)): {'s1', 's2'},
                ('s1', ('b', None)): {'s3'},
                ('s2', ('b', None)): {'s2'},
                ('s2', ('c', None)): {'s3'}
            }
        }

    def test_check_acceptance1(self):
        model = NFA(self.component, self.ext_nfa)
        l_vector = [
            {'tid': 'a', 'values': "['1']"},
            {'tid': 'c', 'values': "[]"}
        ]
        self.assertEqual(False, model.nfa_check_acceptance(l_vector))

    def test_check_acceptance2(self):
        model = NFA(self.component, self.ext_nfa)
        l_vector = [
            {'tid': 'a', 'values': "['1']"},
            {'tid': 'c', 'values': "[]"},
            {'tid': 'b', 'values': "[]"}
        ]
        self.assertEqual(True, model.nfa_check_acceptance(l_vector))

    def test_init(self):
        model = NFA(self.component, self.ext_nfa)
        expected_nfa = copy.deepcopy(self.ext_nfa)
        del self.ext_nfa  # to check deepcopy
        self.assertEqual(expected_nfa['initial_state'], model.initial_state)
        self.assertEqual(expected_nfa['accepting_states'], model.accepting_states)
        self.assertEqual(expected_nfa['states'], model.states)
        self.assertEqual(expected_nfa['transitions'], model.transitions)

    def test_rename_states(self):
        model = NFA(self.component, self.ext_nfa)
        model.rename_states(padding=3)
        self.assertEqual('3', model.initial_state)
        self.assertEqual({'3'}, model.accepting_states)
        self.assertEqual({'3', '4', '5'}, model.states)
        self.assertEqual({('3', ('a', 'var0=="1"')): {'4'},
                          ('3', ('a', 'var0!="1"')): {'5'},
                          ('4', ('b', None)): {'3'},
                          ('5', ('c', None)): {'3'},
                          ('4', ('c', None)): {'4'}},
                         model.transitions)

    def test_merge_states_1(self):
        model = NFA(self.component, self.ext_nfa)
        model.merge_states({'1', '2'})
        self.assertEqual('0', model.initial_state)
        self.assertEqual({'0'}, model.accepting_states)
        self.assertEqual({'0', '1,2'}, model.states)
        self.assertEqual({('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)}, model.alphabet)
        self.assertEqual({
            ('0', ('a', 'var0=="1"')): {'1,2'},
            ('0', ('a', 'var0!="1"')): {'1,2'},
            ('1,2', ('b', None)): {'0'},
            ('1,2', ('c', None)): {'0', '1,2'}
        }, model.transitions)

    def test_merge_states_2(self):
        model = NFA(self.component, self.ext_nfa)
        model.merge_states({'0', '1'})
        self.assertEqual('0,1', model.initial_state)
        self.assertEqual({'0,1'}, model.accepting_states)
        self.assertEqual({'0,1', '2'}, model.states)
        self.assertEqual({('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)}, model.alphabet)
        self.assertEqual({
            ('0,1', ('a', 'var0=="1"')): {'0,1'},
            ('0,1', ('a', 'var0!="1"')): {'2'},
            ('0,1', ('b', None)): {'0,1'},
            ('2', ('c', None)): {'0,1'},
            ('0,1', ('c', None)): {'0,1'}
        }, model.transitions)

    def test_merge_states_3(self):
        model = NFA(self.component, self.ext_nfa)
        model.merge_states({'0', '2'})
        self.assertEqual('0,2', model.initial_state)
        self.assertEqual({'0,2'}, model.accepting_states)
        self.assertEqual({'0,2', '1'}, model.states)
        self.assertEqual({('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)}, model.alphabet)
        self.assertEqual({
            ('0,2', ('a', 'var0=="1"')): {'1'},
            ('0,2', ('a', 'var0!="1"')): {'0,2'},
            ('1', ('b', None)): {'0,2'},
            ('0,2', ('c', None)): {'0,2'},
            ('1', ('c', None)): {'1'}
        }, model.transitions)

    def test_merge_states_4(self):
        model = NFA(self.component, self.ext_nfa)
        model.merge_states({'0', '1'})
        model.merge_states({'0,1', '2'})
        self.assertEqual('0,1,2', model.initial_state)
        self.assertEqual({'0,1,2'}, model.accepting_states)
        self.assertEqual({'0,1,2'}, model.states)
        self.assertEqual({('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)}, model.alphabet)
        self.assertEqual({
            ('0,1,2', ('a', 'var0=="1"')): {'0,1,2'},
            ('0,1,2', ('a', 'var0!="1"')): {'0,1,2'},
            ('0,1,2', ('b', None)): {'0,1,2'},
            ('0,1,2', ('c', None)): {'0,1,2'}
        }, model.transitions)

    def test_merge_states_metamorphic(self):
        model1 = NFA(self.component, self.ext_nfa)
        model1.merge_states({'1', '2'})
        model2 = NFA(self.component, self.ext_nfa)
        model2.merge_states({'2', '1'})
        self.assertEqual(model1.initial_state, model2.initial_state)
        self.assertEqual(model1.states, model2.states)
        self.assertEqual(model1.accepting_states, model2.accepting_states)
        self.assertEqual(model1.transitions, model2.transitions)

    def test_append_1(self):
        model1 = NFA(self.component, self.ext_nfa)
        ext_nfa2 = {'alphabet': {('a', None)},
                    'states': {'0'}, 'initial_state': '0', 'accepting_states': {'0'},
                    'transitions': {
                        ('0', ('a', None)): {'0'}
                    }}
        model2 = NFA(self.component, ext_nfa2)
        model1.append(model2)
        self.assertEqual({'0,3', '1', '2'}, model1.states)
        self.assertEqual('0,3', model1.initial_state)
        self.assertEqual({'0,3'}, model1.accepting_states)
        self.assertEqual({('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None), ('a', None)},
                         model1.alphabet)
        self.assertEqual({
            ('0,3', ('a', 'var0=="1"')): {'1'},
            ('0,3', ('a', 'var0!="1"')): {'2'},
            ('1', ('b', None)): {'0,3'},
            ('2', ('c', None)): {'0,3'},
            ('1', ('c', None)): {'1'},
            ('0,3', ('a', None)): {'0,3'}
        }, model1.transitions)

    def test_append_2(self):
        model1 = NFA(self.component, self.ext_nfa)
        ext_nfa2 = {'alphabet': {('a', 'var0=="1"')},
                    'states': {'0', '1'}, 'initial_state': '0', 'accepting_states': {'1'},
                    'transitions': {
                        ('0', ('a', 'var0=="1"')): {'1'}
                    }}
        model2 = NFA(self.component, ext_nfa2)
        model1.append(model2)
        self.assertEqual({'0,3', '1', '2', '4'}, model1.states)
        self.assertEqual('0,3', model1.initial_state)
        self.assertEqual({'4'}, model1.accepting_states)
        self.assertEqual({('a', 'var0=="1"'), ('a', 'var0!="1"'), ('b', None), ('c', None)}, model1.alphabet)
        self.assertEqual({
            ('0,3', ('a', 'var0=="1"')): {'1', '4'},
            ('0,3', ('a', 'var0!="1"')): {'2'},
            ('1', ('b', None)): {'0,3'},
            ('2', ('c', None)): {'0,3'},
            ('1', ('c', None)): {'1'}
        }, model1.transitions)

    def test_find_non_deterministic_states(self):
        model = NFA(self.component, self.ext_nfa)
        self.assertEqual(None, model.find_non_deterministic_states())

        # add a non-deterministic transition
        self.ext_nfa['transitions'] = {
            ('0', ('a', 'var0=="1"')): {'1', '2', '3'},
            ('0', ('a', 'var0!="1"')): {'2'},
            ('1', ('b', None)): {'0'},
            ('2', ('c', None)): {'0'},
            ('1', ('c', None)): {'1'}
        }
        model = NFA(self.component, self.ext_nfa)
        self.assertEqual({'3', '2', '1'}, model.find_non_deterministic_states())

    def test_nfa_guarded_transition(self):
        model = NFA(self.component, self.ext_nfa)
        dst_states = model.nfa_guarded_transition('0', {'tid': 'a', 'values': "['1']"})
        self.assertEqual(({'1'}, ('a', 'var0=="1"')), dst_states)

        dst_states = model.nfa_guarded_transition('0', {'tid': 'a', 'values': "['10']"})
        self.assertEqual(({'2'}, ('a', 'var0!="1"')), dst_states)

        dst_states = model.nfa_guarded_transition('0', {'tid': 'b', 'values': "[]"})
        self.assertEqual((None, None), dst_states)

        dst_states = model.nfa_guarded_transition('1', {'tid': 'b', 'values': "[]"})
        self.assertEqual(({'0'}, ('b', None)), dst_states)

        dst_states = model.nfa_guarded_transition('2', {'tid': 'c', 'values': "['abc']"})
        self.assertEqual(({'0'}, ('c', None)), dst_states)

    def test_slice(self):
        model = NFA(self.component, self.ext_nfa)
        model_exp = copy.deepcopy(model)
        l_vector = [
            {'tid': 'a', 'values': "['1']"},
            {'tid': 'c', 'values': "[]"}
        ]
        slice_starting_states = {model: model.initial_state}
        sliced_model = model.slice(l_vector, slice_starting_states)
        self.assertEqual({('0', ('a', 'var0=="1"')): {'1'}, ('1', ('c', None)): {'1'}}, sliced_model.transitions)
        self.assertEqual('0', sliced_model.initial_state)
        self.assertEqual({'1'}, sliced_model.accepting_states)
        self.assertEqual({'0', '1'}, sliced_model.states)
        self.assertEqual({('a', 'var0=="1"'), ('c', None)}, sliced_model.alphabet)
        self.check_model_equivalence(model, model_exp)

    def test_slice2(self):
        # bug fix: slice()
        ext_nfa = {
            'initial_state': '73',
            'accepting_states': {'74'},
            'states': {'73', '74'},
            'alphabet': {('E66', None), ('E73', 'var0=="2" or var0=="1" or var0=="17" or var0=="10"')},
            'transitions': {
                ('73', ('E66', None)): {'74'},
                ('74', ('E73', 'var0=="2" or var0=="1" or var0=="17" or var0=="10"')): {'74'}
            }
        }
        model = NFA('test_component', ext_nfa)
        model_exp = copy.deepcopy(model)
        l_vector = [{'ts': 'Jun 10 11:31:46', 'tid': 'E66', 'values': "['0', '100']", 'component': 'kernel'},
                    {'ts': 'Jun 10 11:31:47', 'tid': 'E73', 'values': "['2']", 'component': 'kernel'},
                    {'ts': 'Jun 10 11:31:47', 'tid': 'E73', 'values': "['1']", 'component': 'kernel'},
                    {'ts': 'Jun 10 11:31:47', 'tid': 'E73', 'values': "['17']", 'component': 'kernel'},
                    {'ts': 'Jun 10 11:31:48', 'tid': 'E73', 'values': "['10']", 'component': 'kernel'},
                    {'ts': 'Jun 10 11:31:54', 'tid': 'E73', 'values': "['31']", 'component': 'kernel'}]
        slice_starting_states = {model: model.initial_state}
        sliced_model = model.slice(l_vector, slice_starting_states)
        print(sliced_model.transitions)
        self.assertEqual({('73', ('E66', None)): {'74'},
                          ('74', ('E73', 'var0=="2" or var0=="1" or var0=="17" or var0=="10"')): {'74'}},
                         sliced_model.transitions)
        self.check_model_equivalence(model, model_exp)

    def test_slice3(self):
        if os.system('java -version') != 0:
            print('No java installed: skip this test')
            pass
        else:
            system = 'syn'
            input_file = os.path.join('tests', 'resources', 'MINT', f'{system}_mint_in.txt')
            with tempfile.TemporaryDirectory() as output_dir:
                model = run_mint_using_mint_input(system, input_file, output_dir)
                model_exp = copy.deepcopy(model)
                l_vector = [
                    {'ts': '2020-03-09T00:29:15.601Z', 'tid': '32', 'values': "['Handling system sleep', '067C2E205C53F83E0A495E3C@AdobeID (SyncController.cpp.systemSleepHandler.861)']", 'component': 'syn:'},
                    {'ts': '2020-03-09T00:29:15.601Z', 'tid': '32', 'values': "['Stopping due to system_sleep', '067C2E205C53F83E0A495E3C@AdobeID (SyncController.cpp.stopHandler.813)']", 'component': 'syn:'},
                    {'ts': '2020-03-09T00:29:15.601Z', 'tid': '32', 'values': "['Stopping jobs', '067C2E205C53F83E0A495E3C@AdobeID (SyncController.cpp.stopJobsHandlerIf.1779)']", 'component': 'syn:'}]
                slice_starting_states = {model: model.initial_state}
                sliced_model = model.slice(l_vector, slice_starting_states)
                print(sliced_model.transitions)
                self.assertEqual({('0', ('32', None)): {'5'},
                                  ('23', ('32', None)): {'24'},
                                  ('5', ('32', None)): {'23'}}, sliced_model.transitions)
                self.check_model_equivalence(model, model_exp)

    def test_determinize_heuristic(self):
        model = NFA(self.component, self.ext_nfa2)
        model_dfa = model.heuristic_determinize()  # determinize internally calls merge_states, twice in this test example
        self.assertEqual('0', model_dfa.initial_state)
        self.assertEqual({'1'}, model_dfa.accepting_states)
        self.assertEqual({'0', '1'}, model_dfa.states)
        self.assertEqual(self.ext_nfa2['alphabet'], model_dfa.alphabet)
        self.assertEqual({('0', ('a', None)): '1',
                          ('1', ('b', None)): '1',
                          ('1', ('c', None)): '1'}, model_dfa.transitions)

    def test_determinize_standard(self):
        model = NFA(self.component, self.ext_nfa2)
        model_dfa = model.standard_determinize()
        self.assertEqual("0", model_dfa.initial_state)
        self.assertEqual(2, len(model_dfa.accepting_states))
        self.assertEqual(5, len(model_dfa.states))
        self.assertEqual(self.ext_nfa2['alphabet'], model_dfa.alphabet)
        self.assertEqual(7, len(model_dfa.transitions))

    def test_determinize_hybrid(self):
        ext_nfa = {
            'alphabet': {('a', None), ('b', None), ('c', None), ('d', None)},
            'states': {'s0', 's1', 's2', 's3'},
            'initial_state': 's0',
            'accepting_states': {'s3'},
            'transitions': {
                ('s0', ('a', None)): {'s0', 's1'},
                ('s1', ('b', None)): {'s2'},
                ('s2', ('c', None)): {'s0', 's3'},
            }
        }

        model = NFA(self.component, ext_nfa)
        model_dfa = model.hybrid_determinize()
        self.assertEqual('1', model_dfa.initial_state)
        self.assertEqual({'0'}, model_dfa.accepting_states)
        self.assertEqual({'0', '1', '2'}, model_dfa.states)
        self.assertEqual({('0', ('a', None)): '1',
                          ('0', ('b', None)): '2',
                          ('1', ('a', None)): '1',
                          ('1', ('b', None)): '2',
                          ('2', ('c', None)): '0'}, model_dfa.transitions)

    def test_save_pdf(self):
        if os.system('dot -V') != 0:
            print('No dot installed: skip this test')
            pass
        else:
            model = NFA(self.component, self.ext_nfa)
            with tempfile.TemporaryDirectory() as output_dir:
                model.save_pdf(output_dir=output_dir)
                self.assertTrue(os.path.isfile(os.path.join(output_dir, f'{model.component}.pdf')))

    def test_union_nfa_models(self):
        model1 = NFA(self.component, self.ext_nfa)
        ext_nfa = {'alphabet': {('X', None), ('Y', None)},
                   'states': {'s0', 's1'}, 'initial_state': 's0', 'accepting_states': {'s1'},
                   'transitions': {
                       ('s0', ('X', None)): {'s1'},
                       ('s1', ('Y', None)): {'s0'},
                   }}
        model2 = NFA(self.component, ext_nfa)
        model = NFA.union_nfa_models([model1, model2])
        self.assertEqual({'1', '2', '4', '0,3'}, model.states)
        self.assertEqual({('X', None),
                          ('Y', None),
                          ('a', 'var0!="1"'),
                          ('a', 'var0=="1"'),
                          ('b', None),
                          ('c', None)}, model.alphabet)
        self.assertEqual({'4', '0,3'}, model.accepting_states)
        self.assertEqual('0,3', model.initial_state)
        self.assertEqual({('0,3', ('X', None)): {'4'},
                          ('0,3', ('a', 'var0!="1"')): {'2'},
                          ('0,3', ('a', 'var0=="1"')): {'1'},
                          ('1', ('b', None)): {'0,3'},
                          ('1', ('c', None)): {'1'},
                          ('2', ('c', None)): {'0,3'},
                          ('4', ('Y', None)): {'0,3'}}, model.transitions)

    def check_model_equivalence(self, model, model_exp):
        self.assertEqual(model.transitions, model_exp.transitions)
        self.assertEqual(model.states, model_exp.states)
        self.assertEqual(model.initial_state, model_exp.initial_state)
        self.assertEqual(model.accepting_states, model_exp.accepting_states)
        self.assertEqual(model.alphabet, model_exp.alphabet)
