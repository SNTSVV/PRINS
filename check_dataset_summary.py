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

import path_PRINS
import os
import math
import pandas as pd
from scipy.stats import entropy
from src.main.PRINS import PRINS
from expr_config import *
from src.utils.common import convert_df_into_l_vectors
from natsort import natsorted


def check_subsequence(s: list, org: list) -> bool:
    """Check if a given sequence is a subsequence of another sequence.

    :param s: sub-sequence to check
    :param org: an original sequence
    :return: True if s is in org; False otherwise
    """

    for i in range(len(org)):
        if org[i] == s[0]:
            is_subsequence = True
            for j in range(len(s)):
                if i+j < len(org) and org[i+j] != s[j]:
                    is_subsequence = False
            if is_subsequence:
                return True
    return False

def calculate_log_confidence(l_vectors: dict, component: str = None, k: int = 2) -> float:
    """Calculate the log confidence value of a given set of logs (l_vector).

    :param l_vectors: a set of logs [key: log_id, value: a log (list of log entries)]
    :param component: a component name to limit the scope of analysis (default=None)
    :param k: the length of message sequences to be used for log property checking (default=2)
    :return: log confidence score
    """

    all_templates = set()
    tid_sequences = []
    for log_id, l_vector in l_vectors.items():
        if component:
            tid_sequence = [e['tid'] for e in l_vector if e['component'] == component]
        else:
            tid_sequence = [e['tid'] for e in l_vector]
        tid_sequences.append(tid_sequence)
        all_templates = all_templates.union(set(tid_sequence))
    all_templates = natsorted(all_templates)

    from itertools import product
    S = product(all_templates, repeat=k)
    s_sum = 0
    s_count = 0
    for s in S:
        count = 0
        for tid_sequence in tid_sequences:
            if check_subsequence(s, tid_sequence):
                count += 1
        if count > 0:
            q_s = count / len(tid_sequences)
            s_sum += pow(1 - q_s, len(tid_sequences))
            s_count += 1
    return 1 - s_sum / s_count

def main():
    print('Analyze log diversity in terms of components (div_score, entropy)')

    summary = list()
    for system in SYSTEMS:
        print(f'[Processing] {system} ...')

        # read logs
        logs_csv = os.path.join('dataset', system, f'{system}_preprocessed_logs.csv')
        logs_df = pd.read_csv(logs_csv, dtype={'tid': str})  # to fix the datatype of tid as string
        l_vectors = convert_df_into_l_vectors(logs_df, include_component=True)

        # initialize variables for diversity score calculation
        all_components = []

        # compute set of components appear for each log
        for log_id, l_vector in l_vectors.items():
            partitioned_log = PRINS.partition_log_by_component(l_vector)
            components = frozenset({component for component, _ in partitioned_log})
            all_components.append(components)

        # compute diversity score
        div_score = f'{(len(set(all_components)) - 1) / (len(all_components) - 1):.3f}'
        counts = pd.Series(all_components).value_counts()
        normalized_entropy = f'{entropy(counts) / math.log2(len(all_components)):.3f}'

        # compute log confidence
        log_confidence = calculate_log_confidence(l_vectors)

        # save the results
        n_components = logs_df.component.nunique()
        n_logs = logs_df.logID.nunique()
        n_templates = logs_df.tid.nunique()
        n_messages = logs_df.message.size
        summary.append([system,
                        n_components,
                        n_logs,
                        n_templates,
                        n_messages,
                        div_score,
                        normalized_entropy,
                        log_confidence])

    print('\n=== Dataset Summary ===')
    summary_df = pd.DataFrame(summary, columns=['system',
                                                'components',
                                                'logs',
                                                'templates',
                                                'messages',
                                                'div_score',
                                                'normalized_entropy',
                                                'log_confidence'
                                                ])
    print(summary_df)
    output = os.path.join('dataset', 'dataset_summary.csv')
    summary_df.to_csv(output, index=False)
    print(f'\n[Done] Summary data saved: {output}')


if __name__ == '__main__':
    main()
