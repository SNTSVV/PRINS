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
    # all_component_transitions = []
    # all_component_sequences = []

    for log_id, l_vector in l_vectors.items():
        partitioned_log = PRINS.partition_log_by_component(l_vector)
        components = frozenset({component for component, _ in partitioned_log})
        all_components.append(components)
        # component_transitions = [component for component, _ in partitioned_log]
        # component_sequence = [e['component'] for e in l_vector]
        # all_component_transitions.append(','.join(component_transitions))
        # all_component_sequences.append(','.join(component_sequence))

    # compute diversity score
    div_score = f'{(len(set(all_components))-1) / (len(all_components)-1):.3f}'
    counts = pd.Series(all_components).value_counts()
    normalized_entropy = f'{entropy(counts) / math.log2(len(all_components)):.3f}'

    # save the results
    n_components = logs_df.component.nunique()
    n_logs = logs_df.logID.nunique()
    n_templates = logs_df.tid.nunique()
    n_messages = logs_df.message.size
    summary.append([system, n_components, n_logs, n_templates, n_messages, div_score, normalized_entropy])

print('\n=== Dataset Summary ===')
summary_df = pd.DataFrame(summary, columns=['system', 'components', 'logs', 'templates', 'messages', 'div_score', 'normalized_entropy'])
print(summary_df)
output = os.path.join('dataset', 'dataset_summary.csv')
summary_df.to_csv(output, index=False)
print(f'\n[Done] Summary data saved: {output}')
