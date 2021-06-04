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


def main():
    logger, timestamp = common_logger('run_model_inference', level='INFO')

    # argument parsing & specify target systems
    args, systems = common_arg_parser(SYSTEMS, 'run_model_inference')

    summary = list()
    for system in systems:
        print('-' * 80)
        print(f'{system}')
        logger.info(f'system={system}')
        print(f'MINT_TIMEOUT={MINT_TIMEOUT}, MINT_PARAM={MINT_PARAM}, SAVE_PDF={SAVE_PDF}, IGNORE_VALUES={IGNORE_VALUES}')
        logger.info(f'MINT_TIMEOUT={MINT_TIMEOUT}, MINT_PARAM={MINT_PARAM}, SAVE_PDF={SAVE_PDF}, IGNORE_VALUES={IGNORE_VALUES}')

        # read logs
        logs_csv = os.path.join(DATASET, system, f'{system}_preprocessed_logs.csv')

        if not args.prins_only:
            # MINT-SYS
            logs_df = pd.read_csv(logs_csv, dtype={'tid': str})  # to fix the datatype of tid as string
            l_vectors = convert_df_into_l_vectors(logs_df, args.num_logs, include_component=True)
            # tid_to_components = generate_map_from_tid_to_components(l_vectors)
            start_time = time.time()
            try:
                print(f'running MINT-SYS ...')
                logger.info(f'run_model_inference: system={system}')
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
                summary.append([system, 'MINT-SYS', len(l_vectors.keys()), 'timeout', pd.NA, pd.NA])
            except subprocess.CalledProcessError:
                print(f'MINT-SYS crashes\n')
                summary.append([system, 'MINT-SYS', len(l_vectors.keys()), 'crash', pd.NA, pd.NA])

        if not args.mint_sys_only:
            # PRINS
            print(f'\nrunning PRINS ...')
            instance = PRINS(system, logs_csv, os.path.join('output', system, f'{timestamp}_PRINS'))
            try:
                # PRINS - main algorithm
                for num_workers in [4, 3, 2, 1]:
                    m_sys, p_time, i_time, s_time = instance.run(mint_timeout=MINT_TIMEOUT,
                                                                 mint_param=MINT_PARAM,
                                                                 ignore_values=IGNORE_VALUES,
                                                                 save_pdf=SAVE_PDF,
                                                                 num_workers=num_workers)
                    summary.append([system,
                                    f'PRINS-w{num_workers}',
                                    len(instance.l_vectors.keys()),
                                    f'{p_time + i_time + s_time:.3f}',
                                    f'{p_time:.3f}',
                                    f'{i_time:.3f}',
                                    f'{s_time:.3f}',
                                    len(m_sys.states),
                                    get_dfa_transition_size(m_sys.transitions)])

                # PRINS - determinization
                det_techniques = []
                for i in range(0, 11):  # hybrid-0 == standard determinization
                    det_techniques.append(f'hybrid-{i}')
                for det_tech in det_techniques:
                    dfa_sys, hybrid_det_time = PRINS.postprocess(m_sys, determinize_technique=det_tech)
                    summary.append([system,
                                    det_tech,
                                    len(instance.l_vectors.keys()),
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

            except subprocess.TimeoutExpired:
                print(f'PRINS (MINT-component) timeout ({MINT_TIMEOUT} sec)\n')
                summary.append([system, 'PRINS', len(instance.l_vectors.keys()), 'timeout', pd.NA, pd.NA])
            except subprocess.CalledProcessError:
                print(f'PRINS crashes due to MINT\n')
                summary.append([system, 'PRINS', len(instance.l_vectors.keys()), 'crash', pd.NA, pd.NA])
            except ValueError as e:
                print(f'PRINS crashes due to {e}\n')
                summary.append([system, 'PRINS', len(instance.l_vectors.keys()), 'crash', pd.NA, pd.NA])

    print('\n=== Model Inference Summary ===')
    summary_df = pd.DataFrame(summary, columns=['system', 'technique', 'num_logs', 'time_s', 'PR_time', 'IN_time', 'S_time', 'states', 'transitions'])
    print(summary_df)
    summary_df.to_csv(os.path.join('output', f'summary_model_inference_{timestamp}.csv'), index=False)
    logger.info('run_model_inference: ends without errors')


def get_dfa_transition_size(transitions: dict) -> int:
    unique_transitions = set()
    for (src, word), dst in transitions.items():
        unique_transitions.add((src, frozenset(dst)))
    return len(unique_transitions)


if __name__ == '__main__':
    main()
