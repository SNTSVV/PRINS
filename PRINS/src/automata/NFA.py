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

import time
import copy
from natsort import natsorted
from typing import Set, Dict, List
from src.automata.DFA import DFA
from src.automata.automata_utils import evaluate, save_pdf
from PySimpleAutomata.NFA import nfa_determinization

from config import STD_TIMEOUT
from func_timeout import func_timeout

import logging
logger = logging.getLogger(__name__)


class NFA:
    """
    A Guarded Finite State Machine (gFSM) model in the form of Non-deterministic Finite Automaton (NFA).
    """
    alphabet: Set[str]
    states: Set[str]
    initial_state: str
    accepting_states: Set[str]
    transitions: Dict  # (state, (tid, guard)) -> Set of states

    def __init__(self, component: str, ext_nfa: dict):
        # basic info
        self.component = component

        # guarded FSM
        ext_nfa = copy.deepcopy(ext_nfa)
        self.alphabet = ext_nfa['alphabet']
        self.states = ext_nfa['states']
        self.initial_state = ext_nfa['initial_state']
        self.accepting_states = ext_nfa['accepting_states']
        self.transitions = ext_nfa['transitions']

    def __str__(self):
        return f'alphabet={self.alphabet}\n' \
               f'states={self.states}\n' \
               f'initial_state={self.initial_state}\n' \
               f'accepting_states={self.accepting_states}\n' \
               f'transitions={self.transitions}'

    def nfa_guarded_transition(self, source_state: str, log_entry: dict, ignore_guard=False):
        """
        Make a guarded transition from `source_state` using `log_entry`.
        NOTE: this function makes deterministic transitions only.

        :param source_state: source state
        :param log_entry: log entry
        :param ignore_guard: (optional) Specify whether to ignore guard condition or not
        :return: destination state and alphabet (i.e., tid and guard); None if there is no available destination state
        """

        # get the next state with the caused label and guards
        for (state, (tid, guard)) in self.transitions.keys():
            if state == source_state and log_entry['tid'] == tid:
                if guard is None or ignore_guard or evaluate(guard, log_entry['values']):
                    return self.transitions[(state, (tid, guard))], (tid, guard)
        return None, None

    def slice(self, l_vector: list, slice_starting_states: dict) -> 'NFA':
        """
        Slice a model with respect to the given l_vector.
        NOTE: The slicing is deterministic because it is only performed on the models inferred by MINT.
        ASSERT: This function should not change anything in 'self'.

        :param l_vector: a sequence of log entries
        :param slice_starting_states: a dict for tracking the slice_starting_states (k: model, v: slice_starting_state)
        :return: a sliced NFA
        """

        logger.debug(f'slice(l_vector={l_vector})')
        logger.debug(f'initial_state_slice={slice_starting_states[self]}')

        assert self.find_non_deterministic_states() is None

        # initialize
        sliced_nfa = {
            'alphabet': set(),
            'states': set(),
            'initial_state': slice_starting_states[self],
            'accepting_states': set(),
            'transitions': dict()
        }

        # do the slice
        curr_state = slice_starting_states[self]
        sliced_nfa['states'].add(curr_state)
        for e in l_vector:
            next_states, word = self.nfa_guarded_transition(curr_state, e)

            if next_states is None:
                # second try with ignore_guard=True (to bypass the bug of MINT)
                next_states, word = self.nfa_guarded_transition(curr_state, e, ignore_guard=True)

                if next_states is None:
                    logger.error(f'No more next state: curr_state={curr_state}, log_entry={e}')
                    print(f'No more next state: curr_state={curr_state}, log_entry={e}')
                    # raise an error only if next_state == None even though ignore_guard=True
                    raise ValueError('NFA.slice()')
                else:
                    logger.warning(f'NFA.slice() with ignore_guard=True; bypassing the bug of MINT')
                    print(f'WARNING: NFA.slice() with ignore_guard=True; bypassing the bug of MINT')

            assert len(next_states) < 2  # this is because MINT's output is DFA in principle
            next_state = natsorted(next_states)[0]

            sliced_nfa['states'].add(next_state)
            sliced_nfa['alphabet'].add(word)
            if (curr_state, word) in sliced_nfa['transitions'].keys():
                sliced_nfa['transitions'][(curr_state, word)].add(next_state)
            else:
                sliced_nfa['transitions'][(curr_state, word)] = {next_state}
            curr_state = next_state

        sliced_nfa['accepting_states'].add(curr_state)
        slice_starting_states[self] = curr_state
        return NFA(component=self.component, ext_nfa=sliced_nfa)

    def append(self, nfa: 'NFA'):
        """
        Append a given nfa to self.

        NOTE1: |self.accepting_states| == 1 because it is a sliced model.
        NOTE2: This function may yield non-determinism.

        :param nfa: a model to be appended at the end of self
        :return: (update self)
        """

        logger.debug(f'append(nfa={nfa})')

        # accepting_states check
        assert len(self.accepting_states) == 1
        s_x = self.accepting_states.pop()

        # state redundancy check
        self.check_and_remove_redundant_states(nfa)

        # initial_state: nothing to do
        # initial_state_slice: nothing to do

        # accepting_state
        self.accepting_states = nfa.accepting_states

        # states
        self.states = self.states.union(nfa.states)

        # alphabet
        self.alphabet = self.alphabet.union(nfa.alphabet)

        # transitions
        self.transitions = {**self.transitions, **nfa.transitions}

        # merge s_x (self.accepting_states) and s_y (model.initial_state)
        self.merge_states({s_x, nfa.initial_state})

        # update component
        self.component = "appended"

    def merge_states(self, merge_states: set):
        """
        Merge multiple states at once.

        :param merge_states: a set of states to be merged
        :return: a merged state (s_m)
        """

        assert len(merge_states) > 1
        for s in merge_states:
            assert s in self.states

        logger.debug(f'merge_states: {merge_states}')

        s_m = ','.join(natsorted(merge_states))  # TODO: how to shorten this?

        # check initial_state
        if any(s == self.initial_state for s in merge_states):
            self.initial_state = s_m

        # check accepting_states
        for s in merge_states:
            if s in self.accepting_states:
                self.accepting_states.remove(s)
                self.accepting_states.add(s_m)
            # update states
            self.states.remove(s)
        self.states.add(s_m)

        # redirect transitions
        new_transitions = dict()
        for (src, word), dst_set in self.transitions.items():  # for each transition
            if src in merge_states:  # update source state
                src = s_m
            if merge_states.intersection(dst_set):  # update destination state
                dst_set = dst_set - merge_states
                dst_set.add(s_m)

            # update new_transitions
            if (src, word) in new_transitions.keys():
                new_transitions[(src, word)] = new_transitions[(src, word)].union(dst_set)
            else:
                new_transitions[(src, word)] = dst_set
        # end of for loop
        self.transitions = new_transitions

        # return the merged_state
        return s_m

    def rename_states(self, padding: int):
        """
        Rename all states starting from int(padding).
        For example, if padding=3, then all states are renamed by 3, 4, 5, and so on.

        :param padding: padding number (int) to be added on all states
        :return:
        """
        assert type(padding) == int

        # build rename map
        states_list = natsorted(self.states)
        rename_map = dict()
        for i in range(len(states_list)):
            rename_map[states_list[i]] = str(i + padding)

        new_states = set()
        new_accepting_states = set()
        new_transitions = dict()
        new_initial_state = rename_map[self.initial_state]

        for state in self.states:
            new_states.add(rename_map[state])

        for state in self.accepting_states:
            new_accepting_states.add(rename_map[state])

        for (src, (tid, gid)), dst_set in self.transitions.items():
            for dst in dst_set:
                if (rename_map[src], (tid, gid)) in new_transitions.keys():
                    new_transitions[(rename_map[src], (tid, gid))].add(rename_map[dst])
                else:
                    new_transitions[(rename_map[src], (tid, gid))] = {rename_map[dst]}

        logger.debug(f'rename_states (from={self.initial_state}, to={new_initial_state}), component={self.component}')
        self.states = new_states
        self.accepting_states = new_accepting_states
        self.initial_state = new_initial_state
        self.transitions = new_transitions

    def save_pdf(self, output_dir: str = './', label_dict: dict = None):
        """
        Save the model into a pdf file.

        :param output_dir: output directory
        :param label_dict: to change label - from tid to SOMETHING
        :return: None (save a pdf file)
        """
        save_pdf(self, 'NFA', output_dir, label_dict=label_dict)

    def check_and_remove_redundant_states(self, nfa: 'NFA'):
        """
        Check and remove redundant states between new_states and self.states, by renaming nfa.

        :param nfa: a NFA model to be checked and updated
        :return: (Internally update nfa)
        """

        logger.debug(f'check_and_remove_redundant_states(nfa={nfa})')

        if self.states.intersection(nfa.states):
            max_state = natsorted(list(self.states))[-1].split(',')[-1]  # guaranteed max_state in self
            nfa.rename_states(int(max_state) + 1)
        assert not self.states.intersection(nfa.states)  # assert: no intersection

    @staticmethod
    def union_nfa_models(models: List['NFA'], system: str = None) -> 'NFA':
        """
        Standard NFA union over a set of NFAs.

        :param models: a list of NFAs
        :param system: (optional) the system name
        :return: a model that is the result of the union of given NFAs
        """

        if system is None:
            system = 'union'

        print(f'Performing union ...', end=' ', flush=True)
        logger.info(f'Performing union ...')
        logger.debug(f'union_nfa_models(len(models)={len(models)}, system={system})')
        start_time = time.time()

        # rename states per model
        starting_state_index = 0
        for model in models:
            model.rename_states(padding=starting_state_index)
            starting_state_index += len(model.states)

        # initialize output model
        nfa = {
            'alphabet': set(),
            'states': set(),
            'initial_state': None,
            'accepting_states': set(),
            'transitions': dict()
        }
        resulting_model = NFA(component=system, ext_nfa=nfa)

        initial_states = set()
        for model in models:
            # alphabet
            resulting_model.alphabet = resulting_model.alphabet.union(model.alphabet)

            # states
            resulting_model.states = resulting_model.states.union(model.states)

            # initial states (collect all initial states)
            initial_states.add(model.initial_state)

            # accepting states
            resulting_model.accepting_states = resulting_model.accepting_states.union(model.accepting_states)

            # transitions
            resulting_model.transitions = {**resulting_model.transitions, **model.transitions}

        # merge all initial states
        resulting_model.initial_state = resulting_model.merge_states(initial_states)

        # slice_starting_state (to be complete ...)
        resulting_model.slice_starting_state = resulting_model.initial_state

        print('done. [Time taken: %.3f sec]' % (time.time() - start_time))

        return resulting_model

    def nfa_check_acceptance(self, l_vector: list):
        """
        Check if the given sequence of log entries are acceptable for a model or not.

        :param l_vector: a sequence of log entries, each of which is composed of 'ts', 'tid', and 'values'
        :return: True if the given l_vector is accepted; False otherwise
        """

        logger.debug('NFA.check_acceptance()')

        current_level = {self.initial_state}
        next_level = set()
        for e in l_vector:
            for src_state in current_level:
                dst_states, _ = self.nfa_guarded_transition(src_state, e)
                if dst_states:
                    next_level.update(dst_states)
            if len(next_level) < 1:
                return False
            current_level = next_level
            next_level = set()

        if current_level.intersection(self.accepting_states):
            return True
        else:
            return False

    def find_non_deterministic_states(self, merge_count_per_state: dict = None, per_state_merge_limit: int = None):
        """
        Find a set of non-deterministic dst_states (NOTE: not necessarily starting from the initial state).

        :param merge_count_per_state: (only for hybrid det) state merge count per state
        :param per_state_merge_limit: (only for hybrid det) threshold for finding the target states of non-det
        :return: dst_states
        """

        excluding_dst_states = set()
        if merge_count_per_state and per_state_merge_limit:
            for state, count in merge_count_per_state.items():
                if count >= per_state_merge_limit:
                    excluding_dst_states.add(state)

        for k in self.transitions.keys():
            dst_states = self.transitions[k]
            if len(dst_states - excluding_dst_states) > 1:
                return dst_states - excluding_dst_states
            elif len(dst_states) == 0:
                logger.error(f'Empty Transition: from {k} to {dst_states}.')
                exit(-1)

        return None

    def heuristic_determinize(self) -> 'DFA':
        """
        Heuristic NFA->DFA function (using state merges without considering transition order).

        :return: DFA
        """

        print(f'heuristic_determinize() ...', end=' ', flush=True)
        logger.debug(f'heuristic_determinize() ...')
        start_time = time.time()

        count_merged_states = 0
        while True:
            non_det_states = self.find_non_deterministic_states()
            if non_det_states is None:
                break
            else:
                self.merge_states(non_det_states)
                count_merged_states += len(non_det_states)
                logger.debug(f'count_merged_states={count_merged_states}')

        # build an instance of DFA
        ext_dfa = {
            'alphabet': copy.deepcopy(self.alphabet),
            'states': copy.deepcopy(self.states),
            'initial_state': self.initial_state,
            'accepting_states': copy.deepcopy(self.accepting_states),
            'transitions': {}
        }
        for k, dst_states in self.transitions.items():
            ext_dfa['transitions'][k] = dst_states.pop()
        dfa = DFA(component=self.component, ext_dfa=ext_dfa)
        dfa.shorten_states(consider_set_names=False)

        execution_time = time.time() - start_time
        logger.debug(f'heuristic_determinize(): '
                     f'Time taken: {execution_time:.3f} sec'
                     f'alphabet={len(dfa.alphabet)}, '
                     f'states={len(dfa.states)}, '
                     f'transitions={len(dfa.transitions)}')
        print(f'done. [Time taken: {execution_time:.3f} sec]')
        return dfa

    def hybrid_determinize(self, per_state_merge_limit: int = 1) -> 'DFA':
        """
        Hybrid determinization (i.e., searching from the initial state, excluding already merged states).

        :param per_state_merge_limit: the parameter of hybrid determinization
        :return: DFA
        """
        print(f'hybrid_determinize(k={per_state_merge_limit}) ...', end=' ', flush=True)
        logger.debug(f'hybrid_determinize(k={per_state_merge_limit}) ...')
        start_time = time.time()

        if per_state_merge_limit == 0:
            # no state merge using heuristic; simply move on to the standard determinization
            return self.standard_determinize()

        # initialize merge count per state
        merge_count_per_state = {}
        for state in self.states:
            merge_count_per_state[state] = 0

        # start determinization from the initial state (using BFS-style)
        working_set = [self.initial_state]
        visited = set()
        excluding_dst_states = set()

        while working_set:
            curr = working_set.pop(0)
            visited.add(curr)

            for word in natsorted(self.alphabet):
                if (curr, word) in self.transitions.keys():
                    # for each transition determined by (curr, word) from curr
                    dst_states = self.transitions[(curr, word)]

                    if len(dst_states - excluding_dst_states) > 1:
                        # merge states
                        non_det_states = dst_states - excluding_dst_states
                        s_m = self.merge_states(non_det_states)

                        # calculate merge count for s_m and update merge_count_per_state
                        max_merged_count = 0
                        for merged_state in non_det_states:
                            max_merged_count = max(merge_count_per_state.pop(merged_state) + 1, max_merged_count)

                            # remove merged_state previously added into working_set
                            if merged_state in working_set:
                                working_set.remove(merged_state)
                        merge_count_per_state[s_m] = max_merged_count

                        # update excluding_dst_states
                        if max_merged_count >= per_state_merge_limit:
                            excluding_dst_states.add(s_m)

                        # update working_set
                        for dst_state in natsorted(dst_states.union({s_m}) - non_det_states):
                            if dst_state not in visited and dst_state not in working_set:
                                working_set.append(dst_state)

                    else:  # when len(dst_states - excluding_dst_states) <= 1
                        for dst_state in natsorted(dst_states):
                            if dst_state not in visited and dst_state not in working_set:
                                working_set.append(dst_state)

        print(f'(hybrid) heuristic part done. [Time taken: {time.time() - start_time:.3f} sec]')
        logger.info(f'(hybrid) heuristic part done. [Time taken: {time.time() - start_time:.3f} sec]')
        logger.info(f'maximum merge count per state: {max([v for k, v in merge_count_per_state.items()])}')
        return self.standard_determinize()

    def standard_determinize(self):
        return func_timeout(STD_TIMEOUT, self.standard_determinize_core)

    def standard_determinize_core(self) -> 'DFA':
        """
        Standard NFA->DFA function (using subset construction).

        :return: DFA
        """
        print(f'standard_determinize() ...', end=' ', flush=True)
        logger.debug(f'standard_determinize() ...')
        start_time = time.time()

        ext_nfa = {
            'alphabet': self.alphabet,
            'states': self.states,
            'initial_states': {self.initial_state},
            'accepting_states': self.accepting_states,
            'transitions': self.transitions
        }
        ext_dfa = nfa_determinization(ext_nfa)  # NOTE: state names (orders) can vary randomly due to this function
        dfa = DFA(component=self.component, ext_dfa=ext_dfa)
        dfa.shorten_states(consider_set_names=True)

        execution_time = time.time() - start_time
        logger.info(f'standard_determinize(): '
                    f'Time taken: {execution_time:.3f} sec'
                    f'alphabet={len(dfa.alphabet)}, '
                    f'states={len(dfa.states)}, '
                    f'transitions={len(dfa.transitions)}')
        print(f'done. [Time taken: {execution_time:.3f} sec]')
        return dfa
