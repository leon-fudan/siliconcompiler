import os
import hashlib
import pytest

import siliconcompiler

@pytest.mark.eda
@pytest.mark.quick
def test_klayout(datadir):
    in_def = os.path.join(datadir, 'heartbeat_wrapper.def')
    library_gds = os.path.join(datadir, 'heartbeat.gds')
    library_lef = os.path.join(datadir, 'heartbeat.lef')

    chip = siliconcompiler.Chip()
    chip.load_target('freepdk45_demo')

    chip.set('design', 'heartbeat_wrapper')
    chip.set('read', 'def', 'export', '0', in_def)

    chip.add('asic', 'macrolib', 'heartbeat')
    chip.set('library', 'heartbeat', 'lef', '10M', library_lef)
    chip.set('library', 'heartbeat', 'gds', '10M', library_gds)

    chip.set('arg', 'step', 'export')
    chip.set('flow', 'klayout')

    chip.set('eda', 'klayout', 'variable', 'export', '0', 'timestamps', 'false')

    chip.run()

    result = chip.find_result('gds', 'export')

    with open(result, 'rb') as gds_file:
        data = gds_file.read()
        assert hashlib.md5(data).hexdigest() == '5045229cefe367e6cb4200b3e2f5bd54'
