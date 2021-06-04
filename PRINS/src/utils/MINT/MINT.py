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
import time
import subprocess
from natsort import natsorted
from PySimpleAutomata import automata_IO

import logging
logger = logging.getLogger(__name__)


def run(system: str, input_file: str, output_dir: str, k: int = 2, timeout: int = 3600):
    """
    Returns a "deterministic" extended NFA (i.e., NFA form but deterministic)
    :param system: system name
    :param input_file: mint input file
    :param output_dir: mint output directory
    :param k: mint parameter
    :param timeout: mint timeout (sec)
    :return: extended_nfa (dict)
    """
    # run MINT to infer the system model
    output_file = os.path.join(output_dir, f'{system}_mint_out.txt')
    mint_jar = os.path.join(os.path.dirname(__file__), 'mint-inference.jar')
    cmd = ['java', '-Xss64M', '-Xmx4G', '-jar', f'{mint_jar}', '-input', f'{input_file}',
           '-k', f'{k}', '-algorithm', 'AdaBoostDiscrete', '>', f'{output_file}', '2>&1']
    print(f'Running MINT: {system} (timeout={timeout})', flush=True)
    logger.info(f'Starting MINT for {system} (timeout={timeout})')

    start = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    p.check_returncode()
    end = time.time()
    logger.info(f'MINT ended for {system} [Time taken: {end - start:.3f} sec]')
    print(f'Inferring model for {system} done. [Time taken: {end-start:.3f} sec]')

    # read output_file and perform post-process
    dot_file_lines = list()
    is_read = False
    for line in p.stdout.decode("utf-8").split('\n'):
        logger.debug(line)
        if 'Error occurred during initialization of VM' in line:
            raise Exception(f'{os.getpid()}: FATAL - VM initialization error; {output_file}')

        if 'digraph Automaton {' == line.strip():
            is_read = True
        if is_read:
            if 'initial [shape=plaintext]' in line:
                continue
            elif 'initial -> 0' in line:
                continue
            elif '0 [label="0",shape=doublecircle]' in line:
                dot_file_lines.append('0 [root=true,label="0",shape=doublecircle];')
            else:
                dot_file_lines.append(line)
        if '}' == line.strip():
            is_read = False
    assert is_read is False

    if len(dot_file_lines) == 0:
        print(f'MINT execution error; input_file={input_file}, working_dir={os.getcwd()}')
        exit(-1)

    # save dot file
    model_dot = os.path.join(output_dir, system + '.dot')
    with open(model_dot, 'w') as f:
        for line in dot_file_lines:
            f.write(line + '\n')

    # load the machine as DFA using
    nfa = automata_IO.nfa_dot_importer(model_dot)

    # *post-process*: split multiple events (or guards) in a single transition
    extended_alphabet = set()  # tuple: (tid, gid)
    extended_transitions = dict()

    for word in natsorted(list(nfa['alphabet'])):  # must be sorted to be deterministic
        tokens = word.split('\\n')
        index = 0
        while index < len(tokens):
            # first token = tid
            tid = tokens[index]
            guard = None

            # check following guard
            if index+1 < len(tokens) and re.search(r'[=<>|&]', tokens[index+1]):
                guard = tokens[index+1]
                guard = guard.replace("&&", " and ")
                guard = guard.replace("||", " or ")
                guard = guard.replace("\'", "")
                guard = re.sub(r'(==|!=|<=|>=|<|>)([^\s]+)', r'\1"\2"', guard)
                index += 1

            # extent alphabet
            extended_alphabet.add((tid, guard))

            # extend transitions
            for src in nfa['states']:
                if (src, word) in nfa['transitions'].keys():
                    if (src, (tid, guard)) in extended_transitions.keys():
                        extended_transitions[(src, (tid, guard))] = \
                            extended_transitions[(src, (tid, guard))].union(nfa['transitions'][(src, word)])
                    else:
                        extended_transitions[(src, (tid, guard))] = nfa['transitions'][(src, word)]

            # end of one loop
            index += 1
        # end of while loop
    # end of for loop

    assert len(nfa['initial_states']) == 1

    extended_nfa = {
        'alphabet': extended_alphabet,
        'states': nfa['states'],
        'initial_state': list(nfa['initial_states'])[0],
        'accepting_states': nfa['accepting_states'],
        'transitions': extended_transitions
    }

    return extended_nfa
