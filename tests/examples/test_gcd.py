import siliconcompiler

import os
import subprocess

import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_py(setup_example_test):
    setup_example_test('gcd')

    import gcd
    gcd.main()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
    # Verify that report file was generated.
    assert os.path.isfile('build/gcd/job0/report.html')

    manifest = 'build/gcd/job0/export/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    chip = siliconcompiler.Chip()
    chip.read_manifest(manifest)

    assert chip.get('eda', 'yosys', 'report', 'syn', '0', 'cellarea') == ['syn.log']

@pytest.mark.eda
@pytest.mark.quick
def test_cli(setup_example_test):
    ex_dir = setup_example_test('gcd')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run.sh')])
    assert proc.returncode == 0

@pytest.mark.eda
@pytest.mark.quick
def test_py_sky130(setup_example_test):
    setup_example_test('gcd')

    import gcd_skywater
    gcd_skywater.main()

    assert os.path.isfile('build/gcd/rtl2gds/export/0/outputs/gcd.gds')

    manifest = 'build/gcd/signoff/signoff/0/outputs/gcd.pkg.json'
    assert os.path.isfile(manifest)

    chip = siliconcompiler.Chip()
    chip.read_manifest(manifest)

    # Verify that the build was LVS and DRC clean.
    assert chip.get('metric', 'lvs', '0', 'drvs', 'real') == 0
    assert chip.get('metric', 'drc', '0', 'drvs', 'real') == 0

@pytest.mark.eda
def test_cli_asap7(setup_example_test):
    ex_dir = setup_example_test('gcd')

    proc = subprocess.run(['bash', os.path.join(ex_dir, 'run_asap7.sh')])
    assert proc.returncode == 0
