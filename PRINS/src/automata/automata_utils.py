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

import re
import os
import time
import graphviz

import logging
logger = logging.getLogger(__name__)


def evaluate(guard: str, values: str):
    """
    Return the evaluation result of the guard for the values

    :param guard: guard condition (e.g., 'val0=="ok"')
    :param values: values to be inserted in the guard (e.g., "['ok']")
    :return: True if the values satisfy the guard condition; False otherwise
    """

    if guard is None:
        return True

    # convert str into list; the list format is determined in _find_matching_template@LogParser.py
    values = eval(values)  # values become a list
    if len(values) == 0:
        return False

    # prepare dict as an input of eval()
    values_dict = dict()
    for i in range(len(values)):
        value = re.sub(r'\(|\)', '', values[i])
        values_dict[f'var{i}'] = re.sub(r'\s+', '', value)  # mint's value must not include whitespace

    # evaluate the guard condition using values_dict
    try:
        return eval(guard, values_dict)
    except (NameError, TypeError):
        # not enough values in values_dict
        logger.error(f'evaluate(guard={guard}, values={values})')
        print(f'evaluate(guard={guard}, values={values})')
        exit(-1)


def save_pdf(model, model_type: str, output_dir: str = './', label_dict: dict = None):
    """
    Save the model into a pdf file.

    :param model: a model to be saved as a pdf
    :param model_type: DFA or NFA
    :param output_dir: output directory
    :param label_dict: to change label - from tid to SOMETHING
    :return: None (save a pdf file)
    """

    print('Saving pdf ...', end=' ')
    start_time = time.time()
    g = graphviz.Digraph(format='pdf')

    # nodes
    g.node('fake', style='invisible')
    for state in model.states:
        if state == model.initial_state:
            if state in model.accepting_states:
                g.node(str(state), root='true', shape='doublecircle')
            else:
                g.node(str(state), root='true')
        elif state in model.accepting_states:
            g.node(str(state), shape='doublecircle')
        else:
            g.node(str(state))

    # edges
    g.edge('fake', model.initial_state, style='bold')
    if model_type == 'DFA':
        for (source, (tid, guard)), dst in model.transitions.items():
            if label_dict:
                g.edge(source, dst, label=f'{label_dict[tid]}')
            else:
                if guard is None:
                    g.edge(source, dst, label=f'{tid}')
                else:
                    g.edge(source, dst, label=f'{tid} ({guard})')
    elif model_type == 'NFA':
        for (source, (tid, guard)), dst_states in model.transitions.items():
            for dst in dst_states:
                if label_dict:
                    g.edge(source, dst, label=f'{label_dict[tid]}')
                else:
                    if guard is None:
                        g.edge(source, dst, label=f'{tid}')
                    else:
                        g.edge(source, dst, label=f'{tid} ({guard})')

    # save the pdf file
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        g.render(filename=os.path.join(output_dir, model.component), cleanup=False)
    except graphviz.backend.CalledProcessError:
        print(f'too large edge length; skip rendering pdf')
        logger.warning(f'Too large edge length; skip rendering dot')
        return False

    print('done. [Time taken: %.3f sec]' % (time.time() - start_time))
    logger.debug('Saving pdf done. [Time taken: %.3f sec]' % (time.time() - start_time))
    return True
