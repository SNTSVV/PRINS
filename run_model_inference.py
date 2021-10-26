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
import time
import subprocess
import pandas as pd
from src.utils.common import convert_df_into_l_vectors, common_logger, common_arg_parser
from src.main.mint_helper import infer_model_by_mint
from expr_config import *
from src.main.PRINS import PRINS


def run_MINT_sys(logger, timestamp, args, summary, system, duplicate_factor, logs_csv):
    logs_df = pd.read_csv(logs_csv, dtype={'tid': str})  # to fix the datatype of tid as string
    l_vectors = convert_df_into_l_vectors(logs_df, num_logs=args.num_logs, include_component=True)
    # tid_to_components = generate_map_from_tid_to_components(l_vectors)

    # check the error code from the previous run and skip this time if needed
    error = get_error_from_the_last_run(summary, 'MINT-SYS')
    if error:
        # do not actually run MINT considering the error occurred in previous configs
        summary.append([system, 'MINT-SYS', len(l_vectors.keys()), duplicate_factor, error, pd.NA, pd.NA, pd.NA, pd.NA, pd.NA])
        return

    start_time = time.time()
    try:
        print(f'running MINT-SYS ...')
        model = infer_model_by_mint(component=system,
                                    l_vectors=l_vectors,
                                    output_dir=os.path.join('output', system, f'{timestamp}_MINT-SYS'),
                                    allow_non_det=True,  # meaning NFA is accepted as the output of MINT
                                    ignore_values=IGNORE_VALUES,
                                    timeout=MINT_TIMEOUT,
                                    k=MINT_PARAM)
        print(f'state={len(model.states)}, transitions={len(model.transitions)}')
        summary.append([system,
                        'MINT-SYS',
                        len(l_vectors.keys()),
                        duplicate_factor,
                        f'{time.time() - start_time:.3f}',
                        pd.NA,
                        pd.NA,
                        pd.NA,
                        len(model.states),
                        get_dfa_transition_size(model.transitions)])
        if SAVE_PDF:
            model.save_pdf(
                output_dir=os.path.join('output', system, f'{timestamp}_MINT-SYS'),
                # label_dict=tid_to_components
            )
    except subprocess.TimeoutExpired:
        print(f'MINT-SYS timeout ({MINT_TIMEOUT} sec)\n')
        logger.info(f'MINT-SYS timeout ({MINT_TIMEOUT} sec)')
        summary.append([system, 'MINT-SYS', len(l_vectors.keys()), duplicate_factor, 'timeout', pd.NA, pd.NA, pd.NA, pd.NA, pd.NA])
    except subprocess.CalledProcessError:
        print(f'MINT-SYS crashes\n')
        logger.info(f'MINT-SYS crashes')
        summary.append([system, 'MINT-SYS', len(l_vectors.keys()), duplicate_factor, 'crash', pd.NA, pd.NA, pd.NA, pd.NA, pd.NA])


def run_PRINS(logger, timestamp, summary, system, duplicate_factor, logs_csv):
    instance = PRINS(system, logs_csv, os.path.join('output', system, f'{timestamp}_PRINS'))

    print(f'\nrunning PRINS ...')
    # PRINS - main algorithm
    m_sys = None
    for num_workers in [4, 3, 2, 1]:
        technique = f'PRINS-w{num_workers}'

        # check the error code from the previous run and skip this time if needed
        error = get_error_from_the_last_run(summary, technique)
        if error:
            # do not actually run PRINS considering the error occurred in previous sessions
            summary.append([system, technique, len(instance.l_vectors.keys()), duplicate_factor, error, pd.NA, pd.NA, pd.NA, pd.NA, pd.NA])
            continue

        try:
            m_sys, p_time, i_time, s_time = instance.run(mint_timeout=MINT_TIMEOUT,
                                                         mint_param=MINT_PARAM,
                                                         ignore_values=IGNORE_VALUES,
                                                         save_pdf=SAVE_PDF,
                                                         num_workers=num_workers)

            summary.append([system,
                            technique,
                            len(instance.l_vectors.keys()),
                            duplicate_factor,
                            f'{p_time + i_time + s_time:.3f}',
                            f'{p_time:.3f}',
                            f'{i_time:.3f}',
                            f'{s_time:.3f}',
                            len(m_sys.states),
                            get_dfa_transition_size(m_sys.transitions)])

        except subprocess.TimeoutExpired:
            print(f'PRINS (MINT-component) timeout ({MINT_TIMEOUT} sec)\n')
            logger.info(f'PRINS (MINT-component) timeout ({MINT_TIMEOUT} sec)')
            summary.append([system, technique, len(instance.l_vectors.keys()), duplicate_factor, 'timeout', pd.NA, pd.NA, pd.NA, pd.NA, pd.NA])
        except subprocess.CalledProcessError:
            print(f'PRINS crashes due to MINT\n')
            logger.info(f'PRINS crashes due to MINT')
            summary.append([system, technique, len(instance.l_vectors.keys()), duplicate_factor, 'crash', pd.NA, pd.NA, pd.NA, pd.NA, pd.NA])
        except ValueError as e:
            print(f'PRINS crashes due to {e}\n')
            logger.info(f'PRINS crashes due to {e}')
            summary.append([system, technique, len(instance.l_vectors.keys()), duplicate_factor, 'crash', pd.NA, pd.NA, pd.NA, pd.NA, pd.NA])

    if m_sys:
        # PRINS - determinization
        det_techniques = []
        for i in range(0, 11):  # hybrid-0 == standard determinization
            det_techniques.append(f'hybrid-{i}')
        for det_tech in det_techniques:
            dfa_sys, hybrid_det_time = PRINS.postprocess(m_sys, determinize_technique=det_tech)
            summary.append([system,
                            det_tech,
                            len(instance.l_vectors.keys()),
                            duplicate_factor,
                            f'{hybrid_det_time:.3f}',
                            pd.NA,
                            pd.NA,
                            pd.NA,
                            len(dfa_sys.states),
                            get_dfa_transition_size(dfa_sys.transitions)])
            if SAVE_PDF:
                dfa_sys.save_pdf(
                    output_dir=os.path.join('output', system, f'{timestamp}_PRINS'),
                    # label_dict=tid_to_components
                )

def save_summary(summary: list, timestamp: str) -> pd.DataFrame:
    summary_df = pd.DataFrame(summary,
                              columns=[
                                  'system',
                                  'technique',
                                  'num_logs',
                                  'duplicated',
                                  'time_s',
                                  'PR_time',
                                  'IN_time',
                                  'S_time',
                                  'states',
                                  'transitions'
                              ])
    summary_df.to_csv(os.path.join('output', f'summary_model_inference_{timestamp}.csv'), index=False)
    return summary_df


def get_error_from_the_last_run(summary: list, technique: str):
    """
    Return the error code from the last run of the given technique.

    :param summary: the collection of the running history
    :param technique: the target technique ('MINT-SYS' | 'PRINS')
    :return: error code ('timeout' | 'crash' | None)
    """
    for i in reversed(range(len(summary))):
        if technique == summary[i][1]:
            if 'timeout' == summary[i][4]:
                return 'timeout'
            elif 'crash' == summary[i][4]:
                return 'crash'
            else:
                return None
    return None


def main():
    logger, timestamp = common_logger('run_model_inference', level='INFO')

    # argument parsing & specify target systems
    args, systems = common_arg_parser(SYSTEMS, 'run_model_inference')

    summary = []
    for system in systems:
        print('-' * 80)
        print(f'{system}')
        logger.info(f'system={system}')
        print(f'MINT_TIMEOUT={MINT_TIMEOUT}, MINT_PARAM={MINT_PARAM}, SAVE_PDF={SAVE_PDF}, IGNORE_VALUES={IGNORE_VALUES}')
        logger.info(f'MINT_TIMEOUT={MINT_TIMEOUT}, MINT_PARAM={MINT_PARAM}, SAVE_PDF={SAVE_PDF}, IGNORE_VALUES={IGNORE_VALUES}')

        duplicate_range = [int(x) for x in args.duplicate_range.split(',')]
        for duplicate_factor in range(duplicate_range[0], duplicate_range[1]+1):
            for r in range(args.repetitions):
                print(f'duplicate_factor={duplicate_factor}, repetition={r}')

                # read logs
                if duplicate_factor == 1:
                    logs_csv = os.path.join(DATASET, system, f'{system}_preprocessed_logs.csv')
                else:
                    logs_csv = os.path.join(DATASET, system, f'{system}_preprocessed_logs_dup{duplicate_factor}.csv')
                    if not os.path.isfile(logs_csv):
                        # if duplicated logs are not yet generated, then generate duplicate logs
                        from dataset.duplicate_logs import duplicate_logs_for_system
                        duplicate_logs_for_system(DATASET, system)

                # run model inference approaches
                if not args.prins_only:
                    # MINT-SYS
                    run_MINT_sys(logger, timestamp, args, summary, system, duplicate_factor, logs_csv)
                    save_summary(summary, timestamp)

                if not args.mint_sys_only:
                    # PRINS
                    run_PRINS(logger, timestamp, summary, system, duplicate_factor, logs_csv)
                    save_summary(summary, timestamp)

    print('\n=== Model Inference Summary ===')
    summary_df = save_summary(summary, timestamp)
    print(summary_df)
    logger.info('run_model_inference: ends without errors')


def get_dfa_transition_size(transitions: dict) -> int:
    unique_transitions = set()
    for (src, word), dst in transitions.items():
        unique_transitions.add((src, frozenset(dst)))
    return len(unique_transitions)


if __name__ == '__main__':
    main()
