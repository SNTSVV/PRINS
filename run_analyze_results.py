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

import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from natsort import natsorted
from scipy.stats import median_abs_deviation, entropy

latex_figures = './'
latex_data = './'
SYSTEMS = ['Hadoop', 'HDFS', 'Linux', 'Zookeeper', 'CoreSync', 'NGLClient', 'Oobelib', 'PDApp']

plt.style.use('bmh')
plt.rcParams["font.family"] = "Times New Roman"


def message_distribution():
    results = []
    for system in SYSTEMS:
        logs_df = pd.read_csv(f'dataset/{system}/{system}_preprocessed_logs.csv')
        counts = natsorted(logs_df.groupby(by='component')['message'].count(), reverse=True)
        dist = np.array(counts[:4])/sum(counts[:4])
        results.append((system, f'{np.std(dist):.3f}', f'{np.mean(np.absolute(dist - np.mean(dist))):.3f}', f'{entropy(dist, base=2)/2:.3f}', dist))
    df = pd.DataFrame(results, columns=['system', 'std', 'MAD', 'norm_entropy', 'dist'])
    df.to_csv('message_distribution.csv', index=False)


def rq1_boxplot(ncols=4):
    file = 'expr_output/summary_model_inference.csv'
    df = pd.read_csv(file)
    grouped = df.groupby(by=['system', 'technique'])

    nrows = math.ceil(len(SYSTEMS) / ncols)
    fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=(10, 5))

    for system in SYSTEMS:
        i, j = divmod(SYSTEMS.index(system), ncols)

        labels = [1, 2, 3, 4]
        data = []
        for w in labels:
            technique = f'PRINS-w{w}'
            data.append(grouped.get_group((system, technique))['time_s'])

        axs[i][j].boxplot(data, labels=labels, sym='.')
        axs[i][j].set_title(system, size=14)
        if j == 0:
            axs[i][j].set_ylabel('Execution Time (s)', fontsize=13)
        if i == nrows-1:
            axs[i][j].set_xlabel('Workers', fontsize=13)
        axs[i][j].tick_params(axis='both', which='major', labelsize=13)

    plt.tight_layout()
    plt.show()
    fig.savefig(latex_figures + 'rq1-boxplot.pdf', dpi=300)


def rq2_boxplot(ncols=4):
    file = 'expr_output/summary_model_inference.csv'
    df = pd.read_csv(file)
    grouped = df.groupby(by=['system', 'technique'])

    nrows = math.ceil(len(SYSTEMS) / ncols)
    fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=(10, 5))

    for system in SYSTEMS:
        i, j = divmod(SYSTEMS.index(system), ncols)

        labels = [x for x in range(0, 11)]
        data = []
        for w in labels:
            technique = f'hybrid-{w}'
            data.append(grouped.get_group((system, technique))['time_s'])

        axs[i][j].boxplot(data, labels=labels, sym='.')
        axs[i][j].set_title(system, size=14)
        if j == 0:
            axs[i][j].set_ylabel('Execution time (s)', fontsize=13)
        if i == nrows-1:
            axs[i][j].set_xlabel('Parameter', fontsize=13)
        axs[i][j].tick_params(axis='both', which='major', labelsize=13)

    plt.tight_layout()
    plt.show()
    fig.savefig(latex_figures + 'rq2-boxplot.pdf', dpi=300)


def rq3_line():
    file = 'expr_output/summary_k_folds_cv.csv'
    df = pd.read_csv(file)
    grouped = df.groupby(by=['system', 'technique'])

    fig, axs = plt.subplots(nrows=6, ncols=4, figsize=(10, 12))

    metrics = ['recall', 'specificity', 'BA']
    for metric in metrics:
        for system in SYSTEMS:
            i, j = divmod(SYSTEMS.index(system), 4)
            i += metrics.index(metric) * 2

            labels = ['PRINS']
            for u in range(1, 11):
                labels.append(f'PRINS:hybrid-{u}')

            y_values = []
            for technique in labels:
                if metric == 'BA':
                    value = (grouped.get_group((system, technique))['recall'].values[0] +
                             grouped.get_group((system, technique))['specificity'].values[0]) / 2
                else:
                    value = grouped.get_group((system, technique))[metric].values[0]
                y_values.append(value)

            # axs[i][j].plot([x for x in range(11)], y_values, '.k', markersize=3)
            axs[i][j].plot([x for x in range(11)], y_values, linestyle='-', color='gray', linewidth=1, zorder=1)
            axs[i][j].scatter([x for x in range(11)], y_values, color='black', s=10, zorder=2)
            axs[i][j].set_title(system, size=14)
            if i == 5:
                axs[i][j].set_xlabel('Parameter', fontsize=13)
            if j == 0:
                axs[i][j].set_ylabel(metric, fontsize=13)
            axs[i][j].set_xticks([x for x in range(0, 11, 2)])
            axs[i][j].set_yticks([y / 10 for y in range(0, 11, 2)])
            axs[i][j].tick_params(axis='both', which='major', labelsize=13)

    plt.tight_layout()
    plt.show()
    fig.savefig(latex_figures + 'rq3-boxplot.pdf', dpi=300)


def rq4_table(det: str = 'hybrid-1'):
    file = 'expr_output/summary_model_inference.csv'
    df = pd.read_csv(file)
    grouped = df.groupby(by=['system', 'technique']).mean()

    summary = []
    for system in SYSTEMS:
        if system == 'Spark':
            continue

        states_m = grouped.loc[system, 'MINT-SYS']['states']
        states_p = grouped.loc[system, det]['states']

        trans_m = grouped.loc[system, 'MINT-SYS']['transitions']
        trans_p = grouped.loc[system, det]['transitions']

        time_m = grouped.loc[system, 'MINT-SYS']['time_s']
        time_p = grouped.loc[system, 'PRINS-w4']['time_s'] + grouped.loc[system, det]['time_s']

        summary.append((system,
                        states_m, states_p, states_p/states_m,
                        trans_m, trans_p, trans_p/trans_m,
                        time_m, time_p, time_m/time_p))

    df = pd.DataFrame(summary, columns=['system',
                                        'states_m', 'states_p', 'states_r',
                                        'trans_m', 'trans_p', 'trans_r',
                                        'time_m', 'time_p', 'su'])
    df = df.set_index('system')
    df.loc['Average'] = df.mean()
    df.to_csv(latex_data + 'rq4-table.csv')


def rq5_table(det: str = 'hybrid-1'):
    file = 'expr_output/summary_k_folds_cv.csv'
    df = pd.read_csv(file)
    df = df.set_index(['system', 'technique'])

    summary = []
    for system in SYSTEMS:
        if system == 'Spark':
            continue
        recall_m = df.loc[system, 'MINT-SYS']['recall']
        recall_p = df.loc[system, f'PRINS:{det}']['recall']
        recall_diff = (recall_p - recall_m) * 100

        spec_m = df.loc[system, 'MINT-SYS']['specificity']
        spec_p = df.loc[system, f'PRINS:{det}']['specificity']
        spec_diff = (spec_p - spec_m) * 100

        ba_m = (recall_m + spec_m) / 2
        ba_p = (recall_p + spec_p) / 2
        ba_diff = (ba_p - ba_m) * 100

        summary.append((system, recall_m, recall_p, recall_diff, spec_m, spec_p, spec_diff, ba_m, ba_p, ba_diff))
    df = pd.DataFrame(summary, columns=['system',
                                        'r_mint', 'r_prins', 'r_diff',
                                        's_mint', 's_prins', 's_diff',
                                        'ba_mint', 'ba_prins', 'ba_diff'])
    df = df.set_index('system')
    df.loc['Average'] = df.mean()
    df.to_csv(latex_data + 'rq5-table.csv')


if __name__ == '__main__':
    message_distribution()

    # execution time
    rq1_boxplot(ncols=4)
    rq2_boxplot(ncols=4)
    rq4_table('hybrid-1')

    # accuracy
    rq3_line()
    rq5_table('hybrid-1')
