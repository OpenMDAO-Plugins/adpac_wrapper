import logging
import os.path
import pkg_resources
import shutil
import sys
import unittest

import nose

from openmdao.main.api import set_as_top

from adpac_wrapper import ADPAC

ORIG_DIR = os.getcwd()


class TestCase(unittest.TestCase):
    """
    Test basic functionality of ADPAC input file parser/generator.
    This is written for the EEE 'lpc' case, which is currently not
    publicly available. Until that data is approved for public use
    all tests here will be skipped.
    """

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

    def test_property(self):
        raise nose.SkipTest('Waiting for public data')
        logging.debug('')
        logging.debug('test_property')

        # Read configuration.
        self.adpac.read_input('lpc')

        # Create properties.
        self.adpac.create_property('exit_ps', 'boundata.BC_91.pexit')

        self.adpac.create_property('shaft_speed', (
                                   ('input.rpm', 2),
                                   ('input.rpm', 3),
                                   ('input.rpm', 4),
                                   ('input.rpm', 6),
                                   'boundata.BC_72.rpmwall',
                                   'boundata.BC_73.rpmwall',
                                   'boundata.BC_74.rpmwall',
                                   'boundata.BC_75.rpmwall',
                                   'boundata.BC_76.rpmwall',
                                   'boundata.BC_77.rpmwall',
                                   'boundata.BC_78.rpmwall',
                                   'boundata.BC_79.rpmwall',
                                   'boundata.BC_81.rpmwall',
                                   'boundata.BC_82.rpmwall',
                                   'boundata.BC_87.rpmwall',
                                   'boundata.BC_89.rpmwall',
                                   'boundata.BC_90.rpmwall',
                                   ))

        # Set property and verify new values.
        self.adpac.exit_ps = 123.456
        self.assertEqual(self.adpac.exit_ps, 123.456)
        self.assertEqual(self.adpac.boundata.BC_91.pexit, 123.456)

        self.adpac.shaft_speed = -654.321
        self.assertEqual(self.adpac.shaft_speed, -654.321)
        self.assertEqual(self.adpac.input.rpm[1], 0.)
        self.assertEqual(self.adpac.input.rpm[2], -654.321)
        self.assertEqual(self.adpac.boundata.BC_90.rpmwall, -654.321)

    def test_copy(self):
        raise nose.SkipTest('Waiting for public data')
        logging.debug('')
        logging.debug('test_copy')

        casename = 'junk'

        # Check that we can copy inputs.
        inp_dir = 'Inputs'
        inp_suffixes = ('.input', '.boundata', '.mesh', '.restart.old')
        if os.path.exists(inp_dir):
            shutil.rmtree(inp_dir)
        os.mkdir(inp_dir)
        try:
            for suffix in inp_suffixes:
                shutil.copy('lpc'+suffix, os.path.join(inp_dir,
                                                       casename+suffix))
            self.adpac.copy_inputs(inp_dir, casename)
            for suffix in inp_suffixes:
                self.assertEqual(os.path.exists(casename+suffix), True)

            self.adpac.read_input(casename)
            self.adpac.input.casename = casename

            # Now check that we can use precomputed results.
            self.adpac.results_dir = 'Outputs'
            out_suffixes = ('.converge', '.forces', '.output',
                            '.p3dabs', '.p3drel', '.restart.new')
            if os.path.exists(self.adpac.results_dir):
                shutil.rmtree(self.adpac.results_dir)
            os.mkdir(self.adpac.results_dir)
            try:
                for suffix in out_suffixes:
                    shutil.copy('lpc'+suffix,
                                os.path.join(self.adpac.results_dir,
                                             casename+suffix))
                self.adpac.run_adpac = False
                self.adpac.run()
                for suffix in out_suffixes:
                    self.assertEqual(os.path.exists(casename+suffix), True)
            finally:
                shutil.rmtree(self.adpac.results_dir)
                for suffix in out_suffixes:
                    if os.path.exists(casename+suffix):
                        os.remove(casename+suffix)
        finally:
            shutil.rmtree(inp_dir)
            for suffix in inp_suffixes:
                if os.path.exists(casename+suffix):
                    os.remove(casename+suffix)

    def test_vis3d(self):
        raise nose.SkipTest('Waiting for public data')
        logging.debug('')
        logging.debug('test_vis3d')
        self.adpac.read_input('lpc')
        vis3d = self.adpac.create_bladerow_vis3d()
        cmdfile = 'ensight.cmd'
        try:
            vis3d.write_ensight(cmdfile)
        finally:
            if os.path.exists(cmdfile):
                os.remove(cmdfile)

    def test_converge(self):
        raise nose.SkipTest('Waiting for public data')
        logging.debug('')
        logging.debug('test_converge')
        self.adpac.converge.read('lpc')
        self.assertEqual(len(self.adpac.converge.max_error), 50)
        self.assertEqual(len(self.adpac.converge.rms_error), 50)
        self.assertEqual(len(self.adpac.converge.mass_inflow), 50)
        self.assertEqual(len(self.adpac.converge.mass_outflow), 50)
        self.assertEqual(len(self.adpac.converge.pressure_ratio), 50)
        self.assertEqual(len(self.adpac.converge.efficiency), 50)
        self.assertEqual(len(self.adpac.converge.ss_pts), 50)
        self.assertEqual(len(self.adpac.converge.sep_pts), 50)


if __name__ == '__main__':
    sys.argv.append('--cover-package=adpac_wrapper.')
    sys.argv.append('--cover-erase')
    nose.runmodule()

