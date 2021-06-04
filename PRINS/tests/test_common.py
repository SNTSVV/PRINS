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

import unittest
from src.utils.common import *


class TestCommonUtils(unittest.TestCase):
    def test_generate_pattern_from_format_Hadoop(self):
        log_format = r'<date> <time> <level> \[<module>\] <component>: <message>'
        log_line = '2015-10-17 15:38:07,611 INFO [main] org.apache.hadoop.mapreduce.v2.app.client.MRClientService: Instantiated MRClientService at MININT-FNANLI5.fareast.corp.microsoft.com/10.86.169.121:49465'
        header, pattern = generate_pattern_from_log_format(log_format)
        self.assertEqual(['date', 'time', 'level', 'module', 'component', 'message'], header)

        m = re.match(pattern, log_line)
        self.assertEqual('2015-10-17', m.group('date'))
        self.assertEqual('15:38:07,611', m.group('time'))
        self.assertEqual('INFO', m.group('level'))
        self.assertEqual('main', m.group('module'))
        self.assertEqual('org.apache.hadoop.mapreduce.v2.app.client.MRClientService', m.group('component'))
        self.assertEqual('Instantiated MRClientService at MININT-FNANLI5.fareast.corp.microsoft.com/10.86.169.121:49465', m.group('message'))

    def test_generate_pattern_from_format_Linux_with_pid(self):
        log_format = r'<month> <date> <time> <level> <component>(\[<pid>\])?: <message>'
        log_line = 'Jun 12 00:07:45 combo ftpd[7720]: connection from 222.33.90.199 () at Sun Jun 12 00:07:45 2005'
        header, pattern = generate_pattern_from_log_format(log_format)
        self.assertEqual(['month', 'date', 'time', 'level', 'component', 'pid', 'message'], header)

        m = re.match(pattern, log_line)
        self.assertEqual('Jun', m.group('month'))
        self.assertEqual('12', m.group('date'))
        self.assertEqual('00:07:45', m.group('time'))
        self.assertEqual('combo', m.group('level'))
        self.assertEqual('ftpd', m.group('component'))
        self.assertEqual('7720', m.group('pid'))
        self.assertEqual('connection from 222.33.90.199 () at Sun Jun 12 00:07:45 2005', m.group('message'))

    def test_generate_pattern_from_format_Zookeeper(self):
        log_format = r'<date> <time> - <level> \[<node_ext>:<component>@<port>\] - <message>'
        log_line = '2015-07-29 17:41:41,714 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:0:2181:QuorumPeer@670] - LOOKING'
        header, pattern = generate_pattern_from_log_format(log_format)
        self.assertEqual(['date', 'time', 'level', 'node_ext', 'component', 'port', 'message'], header)

        m = re.match(pattern, log_line)
        self.assertEqual('2015-07-29', m.group('date'))
        self.assertEqual('17:41:41,714', m.group('time'))
        self.assertEqual('INFO', m.group('level'))
        self.assertEqual('QuorumPeer[myid=1]/0:0:0:0:0:0:0:0:2181', m.group('node_ext'))
        self.assertEqual('QuorumPeer', m.group('component'))
        self.assertEqual('670', m.group('port'))
        self.assertEqual('LOOKING', m.group('message'))

    def test_generate_pattern_from_format_Linux_without_pid(self):
        log_format = r'<month> <date> <time> <level> <component>(\[<pid>\])?: <message>'
        log_line = 'Jun 10 11:32:37 combo ntpd: ntpd startup succeeded'
        header, pattern = generate_pattern_from_log_format(log_format)
        self.assertEqual(['month', 'date', 'time', 'level', 'component', 'pid', 'message'], header)

        m = re.match(pattern, log_line)
        self.assertEqual('Jun', m.group('month'))
        self.assertEqual('10', m.group('date'))
        self.assertEqual('11:32:37', m.group('time'))
        self.assertEqual('combo', m.group('level'))
        self.assertEqual('ntpd', m.group('component'))
        self.assertEqual(None, m.group('pid'))
        self.assertEqual('ntpd startup succeeded', m.group('message'))

    def test_get_log_files_under_dir(self):
        log_files = get_log_files_under_dir(os.path.join('tests', 'resources', 'logs'))
        self.assertEqual([('tests/resources/logs/subdir1', '1.log'),
                          ('tests/resources/logs/subdir1', '2.log'),
                          ('tests/resources/logs/subdir1', '3.log'),
                          ('tests/resources/logs/subdir2', '1.log'),
                          ('tests/resources/logs/subdir2', '2.log')], log_files)

    def test_load_logs_into_df(self):
        log_files = get_log_files_under_dir(os.path.join('tests', 'resources', 'logs'))
        log_format = r'<date> <time> <level> \[<process>\] <component>: <message>'
        logs_df = load_logs_into_df(log_format=log_format, log_files=log_files)
        self.assertEqual([1, 2, 3, 4, 5], list(logs_df['logID']))
        self.assertEqual([1, 1, 1, 1, 1], list(logs_df['lineID']))

    def test_convert_df_into_l_vectors1(self):
        logs_df = pd.read_csv('tests/resources/test_system_structured_logs.csv')
        l_vectors = convert_df_into_l_vectors(logs_df, include_component=True)
        self.assertEqual({1: [{'component': 'rpc.statd',
                               'tid': 'E114',
                               'ts': 'Jun 9 06:06:20',
                               'values': "['1', '0.6']"},
                              {'component': 'hcid',
                               'tid': 'E48',
                               'ts': 'Jun 9 06:06:22',
                               'values': "['2.4']"},
                              {'component': 'sdpd',
                               'tid': 'E95',
                               'ts': 'Jun 9 06:06:22',
                               'values': "['1.5']"}],
                          4: [{'component': 'sshd(pam_unix)',
                               'tid': 'E16',
                               'ts': 'Jun 23 02:55:14',
                               'values': "['200.60.37.201']"},
                              {'component': 'su(pam_unix)',
                               'tid': 'E102',
                               'ts': 'Jun 23 04:05:28',
                               'values': "['cyrus', '0']"}]},
                         l_vectors)

    def test_convert_df_into_l_vectors2(self):
        logs_df = pd.DataFrame([['log1', 'ts1', 'tid1', "['x', 'y']"],
                                ['log1', 'ts2', 'tid1', "['a', 'b']"],
                                ['log2', 'ts1', 'tid3', "[]"]],
                               columns=['logID', 'time', 'tid', 'values'])
        l_vectors = convert_df_into_l_vectors(logs_df=logs_df)

        self.assertEqual({'log1':
                              [{'ts': 'ts1', 'tid': 'tid1', 'values': "['x', 'y']"},
                               {'ts': 'ts2', 'tid': 'tid1', 'values': "['a', 'b']"}],
                          'log2':
                              [{'ts': 'ts1', 'tid': 'tid3', 'values': '[]'}]},
                         l_vectors)

    def test_generate_pattern_from_template(self):
        template = 'send <*> <*>'
        pattern = generate_pattern_from_template(template)
        m = re.match(pattern, 'send X Y')
        self.assertEqual(('X', 'Y'), m.groups())

    def test_generate_pattern_from_template_multi_tokens(self):
        template = 'send <*>'
        pattern = generate_pattern_from_template(template)
        m = re.match(pattern, 'send X Y')
        self.assertEqual(('X Y',), m.groups())

    def test_generate_pattern_from_template_empty_token(self):
        template = 'send <*> done'
        pattern = generate_pattern_from_template(template)
        m = re.match(pattern, 'send done')
        self.assertEqual(None, m)
