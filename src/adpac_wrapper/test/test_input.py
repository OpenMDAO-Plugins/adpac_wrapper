import filecmp
import logging
import os.path
import pkg_resources
import sys
import unittest

import nose

from openmdao.main.api import set_as_top

from adpac_wrapper import ADPAC

ORIG_DIR = os.getcwd()


class TestCase(unittest.TestCase):
    """ Test basic functionality of ADPAC input file parser/generator. """

    directory = os.path.realpath(
        pkg_resources.resource_filename('adpac_wrapper', 'test'))

    def setUp(self):
        """ Called before each test in this class. """
        os.chdir(TestCase.directory)
        self.adpac = ADPAC()
        set_as_top(self.adpac)

    def tearDown(self):
        """ Called after each test in this class. """
        os.chdir(ORIG_DIR)

    def compare_files(self, case1, case2):
        """ Compare output files, save input & output on mismatch. """
        for ext in ('.input', '.boundata'):
            file1 = case1+ext
            file2 = case2+ext
            logging.debug('    comparing %s to %s', file1, file2)
            files_ok = filecmp.cmp(file2, file1, shallow=False)
            if not files_ok:
                os.rename(file1, file1+'.bad')
                os.rename(file2, file2+'.bad')
                self.fail('%s is not the same as %s' % (file1, file2))
            else:
                os.remove(file1)
                os.remove(file2)

    def parse_and_generate(self, base):
        """
        Parse `base`, generate from that, parse that, generate, compare.
        Not really a good test, but at least it proves we can read what
        we wrote.
        """
        self.adpac.read_input(base)
        self.adpac.check_config()
        self.adpac.boundata.schedule()
        self.adpac.write_input(base+'_new')
        self.adpac.read_input(base+'_new')
        for ext in ('.input', '.boundata'):
            os.rename(base+'_new'+ext, base+'_new1'+ext)
        self.adpac.boundata.schedule()
        self.adpac.write_input(base+'_new')
        for ext in ('.input', '.boundata'):
            os.rename(base+'_new'+ext, base+'_new2'+ext)
        self.compare_files(base+'_new1', base+'_new2')

    def test_all_bcs(self):
        logging.debug('')
        logging.debug('test_all_bcs')
        self.parse_and_generate('all-bcs')

    def test_eee_frontend(self):
        raise nose.SkipTest('Waiting for public data')
        logging.debug('')
        logging.debug('test_eee_frontend')
        self.parse_and_generate('lpc')

    def test_eee_hpc(self):
        raise nose.SkipTest('Waiting for public data')
        logging.debug('')
        logging.debug('test_eee_hpc')
        self.parse_and_generate('core')

    def test_eee_hpt(self):
        raise nose.SkipTest('Waiting for public data')
        logging.debug('')
        logging.debug('test_eee_hpt')
        self.parse_and_generate('hptnew')

    def test_eee_backend(self):
        raise nose.SkipTest('Waiting for public data')
        logging.debug('')
        logging.debug('test_eee_backend')
        self.parse_and_generate('lpt')


if __name__ == '__main__':
    sys.argv.append('--cover-package=adpac_wrapper.')
    sys.argv.append('--cover-erase')
    nose.runmodule()

