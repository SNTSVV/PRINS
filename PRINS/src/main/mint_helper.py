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
import re
import copy
from natsort import natsorted
from src.utils.MINT import MINT
from src.automata.NFA import NFA

import logging
logger = logging.getLogger(__name__)

END_MARKER = '__END__'


def infer_model_by_mint(component: str, l_vectors: dict, output_dir: str, allow_non_det: bool = False,
                        k: int = 2, ignore_values: bool = False, timeout: int = 3600) -> 'NFA':
    """
    Infer a model (type=NFA) from l_vectors.

    :param component: component name
    :param l_vectors: logs (each entry in l_vector must have 'tid' and 'values' at least)
    :param output_dir: output directory
    :param allow_non_det: allow non-determinism in the resulting model (default=False)
    :param k: mint parameter (default=2)
    :param ignore_values: Specify whether to ignore values in generating a model (default=False)
    :param timeout: mint inference timeout (sec) (default=3600)
    :return: a deterministic model (type=NFA)
    """
    mint_input = prepare_mint_input_from_l_vectors(component, l_vectors, output_dir, ignore_values)
    nfa = run_mint_using_mint_input(component, mint_input, output_dir, k, timeout, allow_non_det)
    return nfa


def run_mint_using_mint_input(component: str, mint_input: str, output_dir: str,
                              k: int = 2, timeout: int = 3600, allow_non_det: bool = False) -> 'NFA':
    """
    Infer a model (type=NFA) from mint_input.

    :param component: component name
    :param mint_input: a file for mint input
    :param output_dir: output directory
    :param k: mint parameter (default=2)
    :param timeout: mint inference timeout (sec) (default=3600)
    :param allow_non_det: allow non-determinism in the resulting model (default=False)
    :return: a deterministic model (type=NFA)
    """
    ext_nfa = MINT.run(component, mint_input, output_dir, k=k, timeout=timeout)
    ext_nfa = remove_end_marker(ext_nfa)
    nfa = NFA(component, ext_nfa)

    if allow_non_det:
        return nfa
    else:
        # remove non-determinism
        dfa = nfa.standard_determinize()  # NOTE: this may take much time ...

        # reform DFA into NFA
        new_nfa = {
            'alphabet': dfa.alphabet,
            'states': dfa.states,
            'initial_state': dfa.initial_state,
            'accepting_states': dfa.accepting_states,
            'transitions': dict()
        }
        for (src, word), dst in dfa.transitions.items():
            new_nfa['transitions'][(src, word)] = {dst}
        return NFA(component, new_nfa)


def prepare_mint_input_from_l_vectors(component: str, l_vectors: dict, output_dir: str, ignore_values=False):
    """
    This is a wrapper function to convert l_vectors to a mint_input file

    :param component: component name
    :param l_vectors: logs (each entry in l_vector must have 'tid' and 'values' at least)
    :param output_dir: output directory
    :param ignore_values: Specify whether to ignore values in generating a model (default=False)
    :return: mint input artifacts (mint types and mint traces)
    """
    # initialize
    mint_types = set()  # (ex) {template} var1:S ...
    mint_traces = []

    # for each trace (log), collect templates and values
    for execution_id in natsorted(l_vectors.keys()):

        # build a trace from log
        mint_trace = []
        for log_entry in l_vectors[execution_id]:
            # init
            template_id = str(log_entry['tid'])  # to make sure
            if template_id == '_init_' or template_id == '_fin_':  # DEBUG
                print(f"Instrumented templates remaining: {template_id}")
                exit(-1)

            # for types
            type_line = template_id

            # if there are values, both type_line and trace_line should be updated
            values = ""
            if (not ignore_values) and log_entry['values']:
                i = 0
                for value in eval(log_entry['values']):
                    # add the values to trace
                    values += " " + re.sub(r'\s+', '', str(value))  # mint's value must not include whitespace
                    type_line += f" var{i}:S"
                    i += 1

            # build one line (single event) of trace
            trace_line = template_id + str(values)

            # add type_line and trace_line
            mint_types.add(type_line)
            mint_trace.append(trace_line)

        # add END_MARKER event at the end of each trace; to bypass MINT's bug
        mint_trace.append(END_MARKER)

        # add trace
        mint_traces.append(mint_trace)

    # sort types (for easy view)
    mint_types = natsorted(list(mint_types))

    # add END_MARKER event at the end of types; to bypass MINT's bug
    mint_types.append(END_MARKER)

    # make dir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # create the MINT input file
    mint_input = os.path.join(output_dir, f'{component}_mint_in.txt')
    with open(mint_input, 'w') as f:
        f.write('types\n')
        for line in mint_types:
            f.write(line+'\n')
        for line in mint_traces:
            f.write('trace\n')
            for event in line:
                f.write(event+'\n')

    return mint_input


def remove_end_marker(deterministic_ext_nfa: dict):

    # initialize
    new_ext_nfa = {
        'alphabet': set(),
        'states': set(),
        'initial_state': deterministic_ext_nfa['initial_state'],
        'accepting_states': set(),
        'transitions': dict()
    }

    end_states = set()
    for (src, word), dst_set in deterministic_ext_nfa['transitions'].items():
        new_ext_nfa['states'].add(src)
        if word[0] == END_MARKER:  # tid (label) == END_marker
            new_ext_nfa['accepting_states'].add(src)
            for dst in dst_set:
                end_states.add(dst)
        else:
            new_ext_nfa['states'] = new_ext_nfa['states'].union(dst_set)
            new_ext_nfa['transitions'][(src, word)] = dst_set
            new_ext_nfa['alphabet'].add(word)

    # asserts
    for (src, word), dst_set in deterministic_ext_nfa['transitions'].items():
        # all end_states should not have outgoing edges
        assert src not in end_states

        # all end_states should not have incoming edges other then END_MARKER
        if end_states.intersection(dst_set):
            assert word[0] == END_MARKER

    return new_ext_nfa
