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

import copy
from typing import Set, Dict
from natsort import natsorted
from src.automata.automata_utils import save_pdf, evaluate

import logging
logger = logging.getLogger(__name__)


class DFA:
    """
    A Guarded Finite State Machine (gFSM) model in the form of Deterministic Finite Automaton (DFA).
    """
    alphabet: Set[str]
    states: Set[str]
    initial_state: str
    accepting_states: Set[str]
    transitions: Dict  # (state, (tid, gid)) -> state

    def __init__(self, component: str, ext_dfa: Dict):
        # basic info
        self.component = component

        # guarded FSM
        ext_dfa = copy.deepcopy(ext_dfa)
        self.alphabet = ext_dfa['alphabet']
        self.states = ext_dfa['states']
        self.initial_state = ext_dfa['initial_state']
        self.accepting_states = ext_dfa['accepting_states']
        self.transitions = ext_dfa['transitions']

    def dfa_check_acceptance(self, l_vector: list):
        """
        Check if the given sequence of log entries are acceptable for a model or not.
        NOTE: ignore_guard=True only for bypassing the bug of MINT

        :param l_vector: a sequence of log entries, each of which is composed of 'ts', 'tid', and 'values'
        :return: True if the given l_vector is accepted; False otherwise
        """

        logger.debug('DFA.check_acceptance()')

        curr_state = self.initial_state
        for e in l_vector:
            next_state = self.make_guarded_transition(curr_state, e)
            if next_state is None:
                next_state = self.make_guarded_transition(curr_state, e, ignore_guard=True)
                if next_state is None:
                    return False
                else:
                    logger.warning(f'DFA.check_acceptance() with ignore_guard=True; bypassing the bug of MINT')
                    print(f'WARNING: DFA.check_acceptance() with ignore_guard=True; bypassing the bug of MINT')
            curr_state = next_state
        return curr_state in self.accepting_states

    def make_guarded_transition(self, source_state: str, log_entry: dict, ignore_guard=False):
        """
        Make a guarded transition from `source_state` using `log_entry`.

        :param source_state: source state
        :param log_entry: log entry
        :param ignore_guard: (optional, default=False) Specify whether to ignore guard conditions or not
        :return: destination state; None if there is no available destination state
        """
        # get the next state with the caused label and guards
        for (state, (tid, guard)) in self.transitions.keys():
            if state == source_state and log_entry['tid'] == tid:
                if guard is None or ignore_guard or evaluate(guard, log_entry['values']):
                    return self.transitions[(state, (tid, guard))]
        return None

    def shorten_states(self, consider_set_names=False):
        """
        Shorten state names, similar to NFA.rename_states().

        :return:
        """

        logger.debug('shorten_states()')

        # reorder states when consider_set_names==True
        if consider_set_names:
            states = set()
            for state in self.states:
                state = natsorted(eval(state))
                states.add(str(state))
        else:
            states = self.states

        # build rename map
        states_list = natsorted(states)
        rename_map = dict()
        for i in range(len(states_list)):
            if consider_set_names:
                state = frozenset(eval(states_list[i]))
            else:
                state = states_list[i]
            rename_map[state] = str(i)

        # NOTE: similar to `rename_states()` in NFA.py
        new_states = set()
        new_accepting_states = set()
        new_transitions = dict()
        if consider_set_names:
            initial_state = frozenset(eval(self.initial_state))
        else:
            initial_state = self.initial_state
        new_initial_state = rename_map[initial_state]

        for state in self.states:
            if consider_set_names:
                state = frozenset(eval(state))
            new_states.add(rename_map[state])

        for state in self.accepting_states:
            if consider_set_names:
                state = frozenset(eval(state))
            new_accepting_states.add(rename_map[state])

        for (src, (tid, gid)), dst in self.transitions.items():
            if consider_set_names:
                src = frozenset(eval(src))
                dst = frozenset(eval(dst))
            new_transitions[(rename_map[src], (tid, gid))] = rename_map[dst]

        logger.debug(f'rename_states (from={self.initial_state}, to={new_initial_state}), component={self.component}')
        self.states = new_states
        self.accepting_states = new_accepting_states
        self.initial_state = new_initial_state
        self.transitions = new_transitions

    def save_pdf(self, output_dir: str = './'):
        """
        Save the model into a pdf file
        :param output_dir: output directory
        :return: None (save a pdf file)
        """
        save_pdf(self, 'DFA', output_dir)
