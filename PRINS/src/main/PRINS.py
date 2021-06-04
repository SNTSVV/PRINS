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
import time
import concurrent
import pandas as pd
from copy import deepcopy
from natsort import natsorted
from src.automata.NFA import NFA
from src.utils.common import convert_df_into_l_vectors
from src.main.mint_helper import infer_model_by_mint
from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor

import logging
logger = logging.getLogger(__name__)


class PRINS:
    """
    Main class for PRINS, which takes as input structured (preprocessed) logs and returns system-level model (gFSM).
    """
    system: str
    logs_df: pd.DataFrame
    l_vectors: dict
    components: list
    output_dir: str

    def __init__(self, system: str, logs, output_dir: str):
        """

        :param system: system name
        :param logs: logs (either csv file or l_vectors)
        :param output_dir: output directory
        """
        self.system = system
        self.output_dir = output_dir

        if type(logs) == dict:  # logs is l_vectors
            self.logs_df = None
            self.l_vectors = logs
            components = set()
            for _, l_vector in self.l_vectors.items():
                for e in l_vector:
                    components.add(e['component'])
            self.components = natsorted(components)
        else:  # logs is a pointer for the csv file
            self.logs_df = pd.read_csv(logs, dtype={'tid': str})
            self.l_vectors = convert_df_into_l_vectors(self.logs_df, include_component=True)
            self.components = natsorted(self.logs_df.component.unique())

    def run(self, mint_timeout=3600, mint_param=2, ignore_values=False, save_pdf=True, num_workers=4):
        """
        Run PRINS (main algorithm).

        :param mint_timeout: mint timeout (sec) (default=3600)
        :param mint_param: the parameter `k` of MINT (default=2)
        :param ignore_values: whether to ignore values in generating a model (default=False)
        :param save_pdf: (optional) True if to save intermediate and final models as files
        :param num_workers: the number of workers for parallel component model inference (default=2)
        :return: DFA (system-level model)
        """

        print(f'PRINS.run(save_files={save_pdf}, mint_timeout={mint_timeout}, ignore_values={ignore_values}, num_workers={num_workers})')
        logger.info(f'PRINS.run(save_files={save_pdf}, mint_timeout={mint_timeout}, ignore_values={ignore_values}, num_workers={num_workers})')

        # STEP1: Projection -------------------------------------------------------------------------------------------
        print('STEP1: Projection ...')
        logger.info('STEP1: Projection ...')
        # project the system logs into individual component logs
        projection_start = time.time()
        component_logs = self.project()
        projection_time = time.time() - projection_start
        print(f'Projection done. [Time taken: {projection_time:.3f} sec]')
        logger.info(f'Projection done. [Time taken: {projection_time:.3f} sec]')

        # STEP2: Inference --------------------------------------------------------------------------------------------
        print(f'STEP2: Inference (workers={num_workers}) ...')
        logger.info(f'STEP2: Inference (workers={num_workers}) ...')
        # infer each component-level model with process pool (multiprocessing)
        inference_start = time.time()
        component_models = {}
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(self.component_model_inference,
                                       component, l_vectors, mint_timeout, mint_param, ignore_values)
                       for component, l_vectors in component_logs.items()}

            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    component, component_model = future.result()
                    component_models[component] = component_model
        inference_time = time.time() - inference_start
        print(f'Inference done. [Time taken: {inference_time:.3f} sec]')
        logger.info(f'Inference done. [Time taken: {inference_time:.3f} sec]')

        # STEP3: Stitching --------------------------------------------------------------------------------------------
        print('STEP3: Stitching ...')
        logger.info('STEP3: Stitching ...')
        stitching_start = time.time()

        # initialize variables for uniqueness score calculation
        all_components = []

        # stitch component-level models according to system-level logs
        appended_models = []

        # sequential stitch
        for log_id, l_vector in self.l_vectors.items():
            model_appended, components = self.stitch(log_id, l_vector, component_models)
            all_components.append(components)
            appended_models.append(model_appended)

        # # parallel stitch (for each execution log): Deactivated as it does not improve the speed much
        # with ThreadPoolExecutor(max_workers=num_workers) as executor:
        #     futures = {
        #         executor.submit(
        #             self.stitch,
        #             log_id,
        #             l_vector,
        #             component_models
        #         ) for log_id, l_vector in self.l_vectors.items()
        #     }
        #     for future in concurrent.futures.as_completed(futures):
        #         if future.result():
        #             model_appended, components = future.result()
        #             all_components.append(components)
        #             appended_models.append(model_appended)
        #
        # # sanity check
        # assert len(appended_models) == len(self.l_vectors.keys())

        # Merge appended_models using union and then convert it into DFA
        m_sys = NFA.union_nfa_models(appended_models, system=self.system)

        # shorten state names (non-functional post-processing in NFA)
        m_sys.rename_states(padding=0)

        stitching_time = time.time() - stitching_start
        print(f'Stitching done. [Time taken: {stitching_time:.3f} sec]')
        logger.info(f'Stitching done. [Time taken: {stitching_time:.3f} sec]')

        print(f'Resulting model (m_sys): states={len(m_sys.states)}, transitions={len(m_sys.transitions)}')
        logger.info(f'Resulting model (m_sys): states={len(m_sys.states)}, transitions={len(m_sys.transitions)}')

        # print log diversity score
        lc_div_score = len(set(all_components)) / len(all_components)
        print(f'lcDivScore: {lc_div_score:.3f}')

        # (optional) Saving the Results as a pdf file
        if save_pdf:
            if len(m_sys.states) < 1000:
                m_sys.save_pdf(output_dir=self.output_dir)
            else:
                print(f'Do not save model.pdf because of too many states: {len(m_sys.states)}')

        return m_sys, projection_time, inference_time, stitching_time

    def component_model_inference(self, component: str, l_vectors: dict, mint_timeout: int, mint_param: int, ignore_values: bool):
        component_model = infer_model_by_mint(component, l_vectors, os.path.join(self.output_dir, component),
                                              allow_non_det=False, timeout=mint_timeout, k=mint_param, ignore_values=ignore_values)
        return component, component_model

    def stitch(self, log_id, l_vector, component_models):
        logger.debug(f'Stitching (log_id={log_id}) ...')

        # initialize
        partitioned_log = self.partition_log_by_component(l_vector)
        slice_starting_states = {}
        for _, component_model in component_models.items():
            slice_starting_states[component_model] = component_model.initial_state

        # expand model_appended
        logger.debug(f'Slicing component-level models')
        model_appended = None
        for component, component_l_vector in partitioned_log:
            # NOTE: slice() does not change the internal states of individual component models
            model_sliced = component_models[component].slice(component_l_vector, slice_starting_states)

            logger.debug(f'Appending sliced models')
            if model_appended is None:
                model_appended = deepcopy(model_sliced)
            else:
                model_appended.append(model_sliced)

        # for the calculation of the component set uniqueness score
        components = frozenset({component for component, _ in partitioned_log})

        return model_appended, components

    def project(self) -> dict:
        """
        Project system-level logs into component-level logs.
        In terms of datatype, This function convert pd.DataFrame into l_vectors (dict).

        :return: component_logs (dict; key: component, value: l_vectors for the component)
        """

        # initialize component_logs (dict)
        component_logs = {}
        for component in self.components:
            component_logs[component] = {}

        # for each log entry, append it on the proper l_vector of the corresponding component
        for log_id, l_vector in self.l_vectors.items():
            for log_entry in l_vector:
                if log_id in component_logs[log_entry['component']].keys():
                    component_logs[log_entry['component']][log_id].append(log_entry)
                else:
                    component_logs[log_entry['component']][log_id] = [log_entry]

        return component_logs

    @staticmethod
    def partition_log_by_component(l_vector: list) -> list:
        """
        Partition a given single log (l_vector) by component.
        A subsequence of log entries having the same component becomes a single partition.

        :param l_vector: a list of log entries, each of which is composed of 'ts', 'component', 'tid', and 'values'
        :return: a list of tuples where each tuple is composed of (component, sequence of log entries)
        """

        partitioned_log = []
        component_l_vector = []
        for i in range(len(l_vector)):
            component_l_vector.append(l_vector[i])
            if i+1 == len(l_vector) or l_vector[i+1]['component'] != l_vector[i]['component']:
                partitioned_log.append((l_vector[i]['component'], component_l_vector))
                component_l_vector = []
        return partitioned_log

    @staticmethod
    def postprocess(m_sys: 'NFA', determinize_technique: str = 'hybrid-1'):
        """
        Postprocessing function.
        Currently, we only convert NFA to DFA.

        :param m_sys: system model in the form of NFA
        :param determinize_technique: determinization technique ('heuristic'|'standard'|'hybrid-k')
        :return: system model in the form of DFA
        """

        start_time = time.time()
        m_sys = deepcopy(m_sys)
        dfa_sys = None
        if determinize_technique == 'standard':
            dfa_sys = m_sys.standard_determinize()
        elif determinize_technique == 'heuristic':  # hybrid-INF, but not necessarily starting from the initial state
            dfa_sys = m_sys.heuristic_determinize()
        elif 'hybrid' in determinize_technique:
            dfa_sys = m_sys.hybrid_determinize(per_state_merge_limit=int(determinize_technique.split('-')[1]))
        else:
            print(f'Unknown determinize_technique: {determinize_technique}')
            exit(-1)

        print(f'Post-processed model (m_sys): states={len(dfa_sys.states)}, transitions={len(dfa_sys.transitions)}')
        logger.info(f'Post-processed model (m_sys): states={len(dfa_sys.states)}, transitions={len(dfa_sys.transitions)}')

        return dfa_sys, time.time() - start_time
