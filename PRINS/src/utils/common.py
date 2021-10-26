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
import natsort
import random
import argparse
import pandas as pd
from datetime import datetime

import logging
logger = logging.getLogger(__name__)


def read_templates_into_df(system: str, template_dir: str):
    """
    Read templates from `self.template_dir/{self.system}_templates.csv`.
    Exit here if there is no such file.
    """

    templates_df = None

    # read templates (if exist)
    template_file = os.path.join(template_dir, f'{system}_templates.csv')
    if os.path.isfile(template_file):
        templates_df = pd.read_csv(os.path.join(template_file), index_col='tid')
        print(f'Total number of templates loaded: {len(templates_df)}')
        logger.info(f'Total number of templates loaded: {len(templates_df)}')
    else:
        print(f'ERROR: No such file: {template_file}')
        exit(0)

    if 'template' not in templates_df.columns:
        print(f'ERROR: {template_file} has no columns `tid` and `template`')
        exit(0)

    return templates_df


def get_log_files_under_dir(log_dir: str, file_ext='.log'):
    """
    Return a list of log files (with path, as tuple) under the given log_dir
    :param log_dir: the root directory for searching log files
    :param file_ext: (optional) log file extension; `.log` by default
    :return: a (sorted) list of tuples composed of (log_path, log_file)
    """
    raw_logs = []
    for root, dirs, files in os.walk(log_dir):
        for file in files:
            if file.endswith(file_ext):
                raw_logs.append((root, file))
                logger.debug('collected log file: %s/%s' % (root, file))
    print('Total number of logs: %d' % len(raw_logs))

    if len(raw_logs) == 0:
        print(f'ERROR: No log files detected under: {log_dir}')
        exit(0)

    return natsort.humansorted(raw_logs)


def load_logs_into_df(log_format: str, log_files: list):
    """
    Load logs with parsing according to the given log format.
    :param log_format:
    :param log_files:
    :return:
    """
    header, pattern = generate_pattern_from_log_format(log_format)
    if 'message' not in header:
        print(f'ERROR: <message> is not in log_format={log_format}')
        exit(-1)

    log_id = 1
    log_dfs = []
    for path, file in log_files:
        log_lines = []
        with open(os.path.join(path, file), 'r', errors='replace') as log:
            for line in log:
                m = re.match(pattern, line.strip())
                if m:
                    log_line = [m.group(h) for h in header]
                    log_lines.append(log_line)
                else:
                    logger.debug(f'Skip non-matched log_line={line.strip()}')
        log_df = pd.DataFrame(log_lines, columns=header)
        log_df['message'] = log_df['message'].str.strip()
        if 'logID' not in header:
            log_df.insert(0, 'lineID', None)
            log_df['lineID'] = [i + 1 for i in range(len(log_lines))]
            log_df.insert(0, 'logID', log_id)
            log_id += 1
        log_dfs.append(log_df)
        logger.info(f'loaded log file (lines=%d): %s' % (len(log_lines), os.path.join(path, file)))

    logs_df = pd.concat(log_dfs, ignore_index=True)
    print(f'Total number of log messages in raw logs: %d' % len(logs_df))

    return logs_df


def generate_pattern_from_log_format(log_format: str):
    header = re.findall(r'<(\S+?)>', log_format)
    pattern = re.sub(r'(<\S+?>)', r'(?P\1.+?)', log_format)
    pattern = re.sub(r'<(\S+)_ext>\.\+\?', r'<\1_ext>.+', pattern)  # bypassing the issue of `test_generate_pattern_from_format_Zookeeper`
    pattern = re.sub(r'\s+', r'\\s+', pattern)
    pattern = '^' + pattern + '$'
    return header, pattern


def generate_pattern_from_template(template: str):
    escaped = re.escape(template)
    spaced_escape = re.sub(r'\\\s+', "\\\s+", escaped)
    return "^" + spaced_escape.replace(r"<\*>", r"(.*?)") + "$"  # a single <*> can consume multiple tokens


def get_parameter_list(row):
    template = row['template']
    if "<*>" not in template:
        return []

    pattern = generate_pattern_from_template(template)
    parameter_list = re.findall(pattern, row['message'])
    parameter_list = parameter_list[0] if parameter_list else ()
    parameter_list = list(parameter_list) if isinstance(parameter_list, tuple) else [parameter_list]
    return parameter_list


def convert_df_into_l_vectors(logs_df: pd.DataFrame, num_logs=None, include_component=False):
    """
    Convert the format of logs from pandas dataframe into l_vectors (dict, key: log_id, value: a log).

    :param logs_df: logs (pandas dataframe)
    :param num_logs: (optional) the number of logs want to convert / for experiments
    :param include_component: (optional, default=False) True to include component information in l_vectors
    :return: l_vectors (dict, key: log_id, value: a log = a list of log entries)
    """
    logs_df = logs_df.copy()
    print(f'Total number of log entries in logs_df: {len(logs_df.index)}')
    header = set(logs_df.columns)

    if 'component' not in header:
        logs_df['component'] = 'system'

    if {'month', 'date', 'time'}.issubset(header):
        # (ex) month = Jun, date = 9, time = 06:06:20
        logs_df['ts'] = logs_df.apply(lambda x: ' '.join([str(x['month']), str(x['date']), str(x['time'])]), axis=1)
    elif {'date', 'time'}.issubset(header):
        # (ex) date = 2015-10-17, time = 15:37:56,547
        # (ex) date = 16/04/07, time=10:46:05
        logs_df['ts'] = logs_df.apply(lambda x: ' '.join([str(x['date']), str(x['time'])]), axis=1)
    elif {'time'}.issubset(header):
        # (ex) time = 2020-03-08T23:01:10.016Z
        logs_df = logs_df.rename(columns={'time': 'ts'})
    else:
        print(f'WARNING: No timestamp in the logs:\n{logs_df.head()}')
        logs_df['ts'] = logs_df['lineID']

    l_vectors = dict()
    reduced_header = ['ts', 'tid', 'values']
    if include_component:
        reduced_header.append('component')
    # logs_df = logs_df[['logID'] + reduced_header]
    for log_id in logs_df['logID'].unique():
        log_df = logs_df[logs_df['logID'] == log_id][reduced_header]
        l_vector = log_df.to_dict('records')
        l_vectors[log_id] = l_vector

    # use subset of all logs if specified
    if num_logs:
        print(f'Use only {num_logs} logs among {len(l_vectors.keys())} logs')
        logger.info(f'Use only {num_logs} logs among {len(l_vectors.keys())} logs')
        log_ids = random.sample(list(l_vectors.keys()), k=len(l_vectors.keys()) - num_logs)
        for log_id in log_ids:
            del l_vectors[log_id]
    else:
        logger.info(f'Total number of logs: {len(l_vectors.keys())}')

    return l_vectors


def generate_map_from_tid_to_components(l_vectors: dict) -> dict:
    """
    Generate a dict from tid to component.

    :param l_vectors: original l_vectors (logs)
    :return: a dict from tid to component
    """
    tid_to_components = {}
    for log_id, l_vector in l_vectors.items():
        for e in l_vector:
            e['component'] = e['component'].replace('org.apache.hadoop.', '')
            if e['tid'] in tid_to_components.keys():
                tid_to_components[e['tid']].add(e['component'])
            else:
                tid_to_components[e['tid']] = {e['component']}
    return tid_to_components


def common_arg_parser(systems, name: str = ''):
    # argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--system', help="System name (default=None)", type=str, default=None)
    parser.add_argument('-n', '--num_logs', help="Number of logs (default=all)", type=int, default=None)
    parser.add_argument('--prins_only', help="Specify this to run PRINS only",
                        dest='prins_only', action='store_true', default=False)
    parser.add_argument('--mint_sys_only', help="Specify this to run MINT-SYS only",
                        dest='mint_sys_only', action='store_true', default=False)
    parser.add_argument('-d', '--duplicate_range', help="Input log duplication factor range 'from,to' (default='1,1')",
                        type=str, default='1,1')
    parser.add_argument('-r', '--repetitions', help="Number of repetitions (default=1)",
                        type=int, default=1)
    args = parser.parse_args()

    # specify target systems
    if args.system:
        assert args.system in systems
        return args, [args.system]

    return args, systems


def common_logger(name: str, level='DEBUG'):
    if not os.path.exists('_logs'):
        os.makedirs(os.path.join('_logs'))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_id = timestamp + f'_{os.getpid()}'
    log_file = os.path.join('_logs', f'{name}_{log_id}.log')
    logging.basicConfig(filename=log_file,
                        format="%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s")
    lg = logging.getLogger()
    if level == 'DEBUG':
        lg.setLevel(logging.DEBUG)
    elif level == 'INFO':
        lg.setLevel(logging.INFO)
    return lg, log_id
