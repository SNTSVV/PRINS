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
import copy
import math
import time
import random
import tempfile
import argparse
import concurrent
import subprocess
import pandas as pd
from expr_config import *
from natsort import natsorted
from src.main.PRINS import PRINS
from src.automata.NFA import NFA
from src.automata.DFA import DFA
from func_timeout import FunctionTimedOut
from src.main.mint_helper import infer_model_by_mint
from concurrent.futures.process import ProcessPoolExecutor
from src.utils.common import convert_df_into_l_vectors, common_logger


def split_execution_ids_into_k_folds(execution_ids: list, k: int, seed: int = None):
    if len(execution_ids) < k:
        logger.error('k-folding is not possible; k=%d > len(ids)=%d' % (k, len(execution_ids)))
        raise Exception

    no_tests = math.floor(len(execution_ids) / k)

    # sort
    execution_ids = natsorted(execution_ids)
    if seed is None:
        seed = os.getpid()
    random.seed(seed)  # randomize splitting k-folds, but using a certain seed
    random.shuffle(execution_ids)
    logger.info(f'split_execution_ids_into_k_folds(): random.seed={seed}')
    print(f'split_execution_ids_into_k_folds(): random.seed={seed}')

    # split
    k_folds = []
    remaining = copy.deepcopy(execution_ids)
    i = 0
    while len(k_folds) < k:
        testing_ids = execution_ids[i:i + no_tests]
        k_folds.append(testing_ids)
        for testing_id in testing_ids:
            remaining.remove(testing_id)
        i += no_tests

    i = 0
    for remained_id in remaining:
        k_folds[i].append(remained_id)
        i += 1

    return k_folds


def generate_pnn_l_vectors(testing_l_vectors: dict, testing_id: int, templates_df: pd.DataFrame):
    """
    Generate positive and negative logs.
    To generate negative logs, either (1) randomly add one entry or (2) randomly swap two entries.

    :param testing_l_vectors: all testing logs
    :param testing_id: testing log id
    :param templates_df: all templates
    :return: positive log, negative log
    """

    positive_l_vector = testing_l_vectors[testing_id]

    trial = 0
    negative_l_vector = None
    negative_confirmed = False
    while not negative_confirmed:
        negative_l_vector = copy.deepcopy(positive_l_vector)
        random_action_indicator = random.random()

        try:
            if random_action_indicator < 1/3:
                # randomly add one entry
                selected_template = random.choice(list(templates_df['template']))
                selected_tid = templates_df[templates_df['template'] == selected_template].index.item()
                selected_timestamp = random.choice([e['ts'] for e in negative_l_vector])
                negative_l_vector.append({'ts': selected_timestamp,
                                          'tid': selected_tid,
                                          'values': []})
            elif 1/3 <= random_action_indicator < 2/3:
                # randomly delete one entry
                if len(negative_l_vector) == 1:
                    continue
                selected_entry = random.choice(negative_l_vector)
                negative_l_vector.remove(selected_entry)
            else:
                # randomly swap two entries
                if len(negative_l_vector) < 2:
                    continue
                x = random.choice(negative_l_vector)
                y = random.choice([e for e in negative_l_vector if e != x])
                x['ts'], y['ts'] = y['ts'], x['ts']  # swap timestamps

            # sort negative_l_vector using timestamps
            negative_l_vector = natsorted(negative_l_vector, key=lambda entry: entry['ts'])

            # check if negative_l_vector is not in testing_l_vectors
            negative_confirmed = all(not is_subsequence(negative_l_vector, l_vector)
                                     for _, l_vector in testing_l_vectors.items())

            trial += 1
            if trial == 100:
                logger.info('negative log generation reaches 100 trials!')
                logger.debug('positive_l_vector=%s' % positive_l_vector)
                logger.debug('negative_l_vector=%s' % negative_l_vector)
                break

        except IndexError as e:
            logger.exception(e)
            logger.error(f'testing_id={testing_id}')
            logger.error(f'positive_l_vector={positive_l_vector}')
            logger.error(f'negative_l_vector={negative_l_vector}')
            logger.error(f'mutation_key={random_action_indicator}')
            exit(-1)

    return positive_l_vector, negative_l_vector


def is_subsequence(x: list, y: list) -> bool:
    """
    Decide whether x is a subsequence of y or not.

    :param x: a list
    :param y: a list
    :return: True is x is a subsequence of y; False otherwise
    """

    if len(x) > len(y):
        return False

    for i in range(len(y)):
        if x[0] == y[i] and (len(y) - i) >= len(x):
            matched = 1
            while (matched < len(x)) and (x[matched] == y[i+matched]):
                matched += 1
            if matched == len(x):
                return True

    return False


def save_cv_result(technique, system, num_logs, recall, specificity):
    if not os.path.isdir('output'):
        os.mkdir('output')
    result_file = os.path.join('output', f'summary_k_folds_cv.csv')
    header = 'technique,system,num_logs,recall,specificity,log-timestamp\n'
    if os.path.isfile(result_file):
        header = ''
    with open(result_file, 'a') as f:
        f.write(header + f'{technique},{system},{num_logs},{recall},{specificity},{timestamp}\n')


def main(seed: int = None, single_fold_no: int = None):
    """
    Run k-folds CV for the benchmark dataset.
    Detailed configuration (such as dataset/output paths) should be done in `expr_config.py`.

    """

    # argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('system', help="System name (e.g., Hadoop)", type=str, default=None)
    parser.add_argument('-k', '--num_folds', help="Number of folds", type=int, default=10)
    parser.add_argument('-n', '--num_logs', help="Number of logs (default: all)", type=int, default=None)
    args = parser.parse_args()
    timeout = MINT_TIMEOUT * 3

    # Base logging (info)
    logger.info(f'system={args.system}, '
                f'num_folds={args.num_folds}, '
                f'num_logs={args.num_logs} '
                f'timeout={timeout} '
                f'timestamp={timestamp}')
    print(f'system={args.system}, '
          f'num_folds={args.num_folds}, '
          f'num_logs={args.num_logs} '
          f'timeout={timeout} '
          f'timestamp={timestamp}')

    # read logs and templates from {LOG_TYPE}_logs.csv
    logs_csv = os.path.join(DATASET, args.system, f'{args.system}_preprocessed_logs.csv')
    logs_df = pd.read_csv(logs_csv, dtype={'tid': str})  # dtype to fix the datatype of tid as string
    l_vectors = convert_df_into_l_vectors(logs_df=logs_df, num_logs=args.num_logs, include_component=True)
    templates_df = logs_df[['tid', 'template']].drop_duplicates().set_index('tid')
    templates_df.reindex(index=natsorted(templates_df.index))  # this sorts the templates using their tid
    args.num_logs = len(l_vectors.keys())

    # initialize TECHNIQUES
    TECHNIQUES = ['MINT-SYS', 'PRINS']
    for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1000]:
        technique = f'PRINS:hybrid-{i}'
        TECHNIQUES.append(technique)

    # split execution_ids into k folds
    k_folds = split_execution_ids_into_k_folds(l_vectors.keys(), args.num_folds, seed=seed)

    # initialize cv_results
    cv_results = {}
    for metric in ['recall', 'specificity']:
        cv_results[metric] = {}
        for technique in TECHNIQUES:
            cv_results[metric][technique] = 0

    # for each fold, call run_one_fold
    for testing_ids in k_folds:
        no_fold = k_folds.index(testing_ids) + 1
        if single_fold_no and no_fold != single_fold_no:
            continue  # for debugging

        start_time = time.time()
        print(f'Processing fold_no={no_fold} ...')
        logger.info(f'Processing fold_no={no_fold} ...')
        logger.debug(f'testing_ids={testing_ids}')
        training_ids = natsorted(list(set(l_vectors.keys()).difference(set(testing_ids))))

        # initialize one fold results
        one_fold_results = {}
        for metric in ['recall', 'specificity']:
            one_fold_results[metric] = {}
            for technique in TECHNIQUES:
                one_fold_results[metric][technique] = 0

        # prepare testing/training l_vectors and templates
        training_l_vectors = dict()
        testing_l_vectors = dict()
        for ex_id in l_vectors.keys():
            if ex_id in training_ids:
                training_l_vectors[ex_id] = l_vectors[ex_id]
            elif ex_id in testing_ids:
                testing_l_vectors[ex_id] = l_vectors[ex_id]

        # prepare negative_l_vectors
        negative_l_vectors = dict()
        for testing_id in testing_l_vectors.keys():
            _, negative_l_vector = generate_pnn_l_vectors(testing_l_vectors, testing_id, templates_df)
            negative_l_vectors[testing_id] = negative_l_vector
        logger.info(f'prepare negative_l_vectors: total {len(negative_l_vectors.keys())} logs')

        # Infer and check the acceptance for each technique
        model = {}
        for technique in TECHNIQUES:
            model[technique] = None

        if 'MINT-SYS' in TECHNIQUES:
            technique = 'MINT-SYS'
            if type(cv_results['recall'][technique]) != str:
                try:
                    with tempfile.TemporaryDirectory() as working_dir:
                        model[technique] = infer_model_by_mint(component=args.system,
                                                               l_vectors=training_l_vectors,
                                                               output_dir=working_dir,
                                                               allow_non_det=True,
                                                               ignore_values=IGNORE_VALUES,
                                                               timeout=timeout,
                                                               k=MINT_PARAM)
                except subprocess.TimeoutExpired:
                    print(f'{technique} timeout ({timeout} sec)\n')
                    logger.info(f'{technique} timeout ({timeout} sec)\n')
                    cv_results['recall'][technique] = 'timeout'
                    cv_results['specificity'][technique] = 'timeout'
                except subprocess.CalledProcessError:
                    print(f'MINT crashes during {technique}\n')
                    logger.info(f'MINT crashes during {technique}\n')
                    cv_results['recall'][technique] = 'crash'
                    cv_results['specificity'][technique] = 'crash'

        if 'PRINS' in TECHNIQUES:
            technique = 'PRINS'
            if type(cv_results['recall'][technique]) != str:
                try:
                    with tempfile.TemporaryDirectory() as working_dir:
                        instance = PRINS(args.system, training_l_vectors, working_dir)
                        model[technique], _, _, _ = instance.run(mint_timeout=timeout,
                                                                 mint_param=MINT_PARAM,
                                                                 ignore_values=IGNORE_VALUES,
                                                                 save_pdf=SAVE_PDF,
                                                                 num_workers=PRINS_NUM_WORKERS)
                except subprocess.TimeoutExpired:
                    print(f'{technique} timeout ({timeout} sec)\n')
                    logger.info(f'{technique} timeout ({timeout} sec)\n')
                    for technique in TECHNIQUES:
                        if 'PRINS' in technique:
                            cv_results['recall'][technique] = 'timeout'
                            cv_results['specificity'][technique] = 'timeout'
                except subprocess.CalledProcessError:
                    print(f'MINT crashes during {technique}\n')
                    logger.info(f'MINT crashes during {technique}\n')
                    for technique in TECHNIQUES:
                        if 'PRINS' in technique:
                            cv_results['recall'][technique] = 'mint-oom'
                            cv_results['specificity'][technique] = 'mint-oom'

            # PRINS with hybrid determinization
            for technique in TECHNIQUES:
                if 'hybrid' in technique:
                    if model['PRINS'] and type(cv_results['recall'][technique]) != str:
                        try:
                            model[technique], _ = PRINS.postprocess(model['PRINS'],
                                                                    determinize_technique=technique.split(':')[1])
                        except MemoryError:
                            print(f'{technique} ran out of memory\n')
                            logger.info(f'{technique} ran out of memory\n')
                            cv_results['recall'][technique] = 'post-oom'
                            cv_results['specificity'][technique] = 'post-oom'

        # acceptance check for all techniques
        print('Checking acceptance of positive/negative logs ...', end=' ', flush=True)
        logger.info('Checking acceptance of positive/negative logs ...')
        acceptance_start_time = time.time()
        with ProcessPoolExecutor() as executor:
            futures = {executor.submit(
                acceptance_checker,
                m_sys, technique, testing_l_vectors[testing_id], negative_l_vectors[testing_id]
            )
                for technique, m_sys in model.items() if m_sys
                for testing_id in testing_l_vectors.keys()
            }

            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    technique, true_positive, true_negative = future.result()
                    one_fold_results['recall'][technique] += true_positive
                    one_fold_results['specificity'][technique] += true_negative
        acceptance_check_time = time.time() - acceptance_start_time
        print(f'done. [Time taken: {acceptance_check_time:.3f} sec]')
        logger.info(f'Acceptance check done. [Time taken: {acceptance_check_time:.3f} sec]')

        # Save the acceptance results in cv_results
        total_testings = len(testing_l_vectors.keys())
        for technique, training_model in model.items():
            if model[technique]:
                recall = one_fold_results['recall'][technique] / total_testings
                specificity = one_fold_results['specificity'][technique] / total_testings
                print(f"{technique:8s}: recall={recall:.3f}, specificity={specificity:.3f}")
                logger.info(f"{technique:8s}: recall={recall:.3f}, specificity={specificity:.3f}")
                cv_results['recall'][technique] += recall
                cv_results['specificity'][technique] += specificity

        # end one fold
        one_fold_time = time.time() - start_time
        print(f'End one fold. [Time taken: {one_fold_time:.3f} sec]\n')
        logger.info(f'End one fold. [Time taken: {one_fold_time:.3f} sec]')

    print(f'{args.num_folds}-fold CV Summary: {args.system} ' + '-'*(29-len(args.system)))
    for technique in TECHNIQUES:
        if type(cv_results['recall'][technique]) != str:
            recall = cv_results['recall'][technique] / args.num_folds
            specificity = cv_results['specificity'][technique] / args.num_folds
            print(f"{technique:8s}: recall={recall:.3f}, specificity={specificity:.3f}")
            logger.info(f"{technique:8s}: recall={recall:.3f}, specificity={specificity:.3f}")
        else:
            recall = cv_results['recall'][technique]
            specificity = cv_results['specificity'][technique]
            print(f"{technique:8s}: recall={recall}, specificity={specificity}")
            logger.info(f"{technique:8s}: recall={recall}, specificity={specificity}")
        save_cv_result(technique, args.system, args.num_logs, recall, specificity)
    print('-'*50+'\n')
    logger.info('run_k_folds_cv: ends without errors')


def acceptance_checker(m_sys, technique: str, positive: list, negative: list) -> (str, int, int):
    """
    Check acceptance of positive and negative logs for the given model (multiprocessing worker).

    :param m_sys: a model
    :param technique: a technique
    :param positive: a positive log
    :param negative: a negative log
    :return:
    """
    true_positive = 0
    true_negative = 0

    if isinstance(m_sys, NFA):
        if m_sys.nfa_check_acceptance(positive):
            true_positive = 1
        if not m_sys.nfa_check_acceptance(negative):
            true_negative = 1
    elif isinstance(m_sys, DFA):
        if m_sys.dfa_check_acceptance(positive):
            true_positive = 1
        if not m_sys.dfa_check_acceptance(negative):
            true_negative = 1

    return technique, true_positive, true_negative


if __name__ == '__main__':
    """
    This script is to run k-folds CV (using MINT).
    """

    logger, timestamp = common_logger('run_k_folds_cv', level='INFO')

    retry = 0
    while retry < 10:
        try:
            main(seed=os.getpid()+retry)
            break
        except FunctionTimedOut:
            retry += 1
            print(f'\nERROR: standard_determinize() timed out. retry={retry}\n')
            logger.error(f'standard_determinize() timed out. retry={retry}')
