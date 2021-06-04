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
from src.automata.automata_utils import *


class TestAutomataUtils(unittest.TestCase):
    def test_evaluate(self):
        guard = 'var0=="ok"'
        values = "['ok']"
        self.assertEqual(True, evaluate(guard, values))

        values = "['ok', 'not-ok']"
        self.assertEqual(True, evaluate(guard, values))

        values = "[]"
        self.assertEqual(False, evaluate(guard, values))

    def test_evaluate2(self):
        # bug fix: mint's value must not include whitespace, so we should delete whitespace in values in evaluate()
        guard = 'var0=="211.90.241.7user=root" or var0=="squid.netcomputers.rouser=test"'
        values = "['211.90.241.7  user=root']"
        self.assertEqual(True, evaluate(guard, values))
