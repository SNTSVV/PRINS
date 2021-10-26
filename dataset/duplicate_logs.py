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
import pandas as pd
from natsort import natsorted
from tqdm import trange

# all system available in the dataset
SYSTEMS = ['Hadoop', 'HDFS', 'Linux', 'Spark', 'Zookeeper', 'CoreSync', 'NGLClient', 'Oobelib', 'PDApp']

def duplicate_logs_for_system(dataset_dir: str, system: str, duplication_factor: int = 8):
    """Duplicate logs for a given system.

    *NOTE*: column *logID* in the input log file (csv) should contain consecutive log ids starting from 1.

    :param dataset_dir: dataset directory
    :param system: target system
    :param duplication_factor: duplication factor (default=10)
    :return: None (internally generates duplicated logs in the form of csv)
    """
    print(f'processing {system} logs ...')
    assert duplication_factor > 0

    # read logs
    org_log_file = os.path.join(dataset_dir, system, f'{system}_preprocessed_logs.csv')
    df = pd.read_csv(org_log_file)
    new_df = df.copy()

    sorted_logIDs = natsorted(df['logID'].unique())
    assert sorted_logIDs[0] == 1 and sorted_logIDs[-1] == len(sorted_logIDs)
    for d in trange(1, duplication_factor):
        # duplicate log ids
        start_id = len(sorted_logIDs) * d
        new_ids_dict = {}
        for i in range(len(sorted_logIDs)):
            new_ids_dict[sorted_logIDs[i]] = i+1+start_id

        # duplicate logs
        df_duplicated = df.copy()
        df_duplicated['logID'] = df['logID'].map(new_ids_dict)

        # append duplicated logs
        assert len(set(new_df['logID'].unique()).intersection(set(df_duplicated['logID'].unique()))) == 0
        new_df = new_df.append(df_duplicated)
        new_df.to_csv(os.path.join(dataset_dir, system, f'{system}_preprocessed_logs_dup{d+1}.csv'), index=False)


if __name__ == '__main__':
    for s in SYSTEMS:
        duplicate_logs_for_system(dataset_dir='./', system=s)
