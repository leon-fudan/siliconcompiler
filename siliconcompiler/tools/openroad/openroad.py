import os
import re
import shutil
import math
import siliconcompiler
from siliconcompiler.floorplan import _infer_diearea

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    OpenROAD is an automated physical design platform for
    integrated circuit design with a complete set of features
    needed to translate a synthesized netlist to a tapeout ready
    GDSII.

    Documentation:https://github.com/The-OpenROAD-Project/OpenROAD

    Sources: https://github.com/The-OpenROAD-Project/OpenROAD

    Installation: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg', 'step', '<step>')
    chip.set('arg', 'index', '<index>')
    chip.set('design', '<design>')
    # TODO: how to make it clear in docs that certain settings are
    # target-dependent?
    chip.load_target('freepdk45_demo')
    setup(chip)

    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip, mode='batch'):

    # default tool settings, note, not additive!

    tool = 'openroad'
    refdir = 'tools/'+tool
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('flow')

    if mode == 'show':
        clobber = True
        option = "-no_init -gui"
    else:
        clobber = False
        option = "-no_init"

    script = '/sc_apr.tcl'

    # exit automatically in batch mode and not bkpt
    if (mode=='batch') and (step not in chip.get('bkpt')):
        option += " -exit"

    chip.set('eda', tool, 'exe', tool, clobber=clobber)
    chip.set('eda', tool, 'vswitch', '-version', clobber=clobber)
    chip.set('eda', tool, 'version', '>=v2.0-3394', clobber=clobber)
    chip.set('eda', tool, 'format', 'tcl', clobber=clobber)
    chip.set('eda', tool, 'copy', 'true', clobber=clobber)
    chip.set('eda', tool, 'option',  step, index, option, clobber=clobber)
    chip.set('eda', tool, 'refdir',  step, index, refdir, clobber=clobber)
    chip.set('eda', tool, 'script',  step, index, refdir + script, clobber=clobber)

    # normalizing thread count based on parallelism and local
    threads = os.cpu_count()
    if not chip.get('remote') and step in chip.getkeys('flowgraph', flow):
        np = len(chip.getkeys('flowgraph', flow, step))
        threads = int(math.ceil(os.cpu_count()/np))

    chip.set('eda', tool, 'threads', step, index, threads, clobber=clobber)

    # Input/Output requirements
    if step == 'floorplan':
        if (not chip.valid('read', 'netlist', step, index) or
            not chip.get('read', 'netlist', step, index)):
            chip.add('eda', tool, 'input', step, index, chip.get('design') +'.vg')
    else:
        if (not chip.valid('read', 'def', step, index) or
            not chip.get('read', 'def', step, index)):
            chip.add('eda', tool, 'input', step, index, chip.get('design') +'.def')

    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.sdc')
    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.vg')
    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.def')

    # openroad makes use of these parameters
    targetlibs = chip.get('asic', 'logiclib')
    stackup = chip.get('asic', 'stackup')
    if stackup and targetlibs:
        mainlib = targetlibs[0]
        macrolibs = chip.get('asic', 'macrolib')
        libtype = str(chip.get('library', mainlib, 'arch'))

        chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'logiclib']))
        chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'stackup']))
        chip.add('eda', tool, 'require', step, index, ",".join(['library', mainlib, 'arch']))
        chip.add('eda', tool, 'require', step, index, ",".join(['pdk', 'aprtech', 'openroad', stackup, libtype, 'lef']))

        for lib in (targetlibs + macrolibs):
            for corner in chip.getkeys('library', lib, 'nldm'):
                chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'nldm', corner, 'lib']))
            chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'lef', stackup]))
    else:
        chip.error = 1
        chip.logger.error(f'Stackup and logiclib parameters required for OpenROAD.')

    variables = (
        'place_density',
        'pad_global_place',
        'pad_detail_place',
        'macro_place_halo',
        'macro_place_channel'
    )
    for variable in variables:
        # For each OpenROAD tool variable, read default from PDK and write it
        # into schema. If PDK doesn't contain a default, the value must be set
        # by the user, so we add the variable keypath as a requirement.
        if chip.valid('pdk', 'variable', tool, stackup, variable):
            value = chip.get('pdk', 'variable', tool, stackup, variable)
            # Clobber needs to be False here, since a user might want to
            # overwrite these.
            chip.set('eda', tool, 'variable', step, index, variable, value,
                     clobber=False)

        keypath = ','.join(['eda', tool, 'variable', step, index, variable])
        chip.add('eda', tool, 'require', step, index, keypath)

    for clock in chip.getkeys('clock'):
        chip.add('eda', tool, 'require', step, index, ','.join(['clock', clock, 'period']))
        chip.add('eda', tool, 'require', step, index, ','.join(['clock', clock, 'pin']))

    for supply in chip.getkeys('supply'):
        chip.add('eda', tool, 'require', step, index, ','.join(['supply', supply, 'level']))
        chip.add('eda', tool, 'require', step, index, ','.join(['supply', supply, 'pin']))

    # basic warning and error grep check on logfile
    chip.set('eda', tool, 'regex', step, index, 'warnings', "WARNING", clobber=False)
    chip.set('eda', tool, 'regex', step, index, 'errors', "ERROR", clobber=False)

    # reports
    logfile = f"{step}.log"
    for metric in chip.getkeys('metric', 'default', 'default'):
        if metric not in ('runtime', 'memory',
                          'luts', 'dsps', 'brams'):
            chip.set('eda', tool, 'report', step, index, metric, logfile)

################################
# Version Check
################################

def parse_version(stdout):
    # stdout will be in one of the following forms:
    # - 1 08de3b46c71e329a10aa4e753dcfeba2ddf54ddd
    # - 1 v2.0-880-gd1c7001ad
    # - v2.0-1862-g0d785bd84

    # strip off the "1" prefix if it's there
    version = stdout.split()[-1]

    pieces = version.split('-')
    if len(pieces) > 1:
        # strip off the hash in the new version style
        return '-'.join(pieces[:-1])
    else:
        return pieces[0]

def normalize_version(version):
    if '.' in version:
        return version.lstrip('v')
    else:
        return '0'

def pre_process(chip):
    step = chip.get('arg', 'step')

    # Only do diearea inference if we're on floorplanning step and these
    # parameters are all unset.
    if (step != 'floorplan' or
        chip.get('asic', 'diearea') or
        chip.get('asic', 'corearea') or
        ('floorplan' in chip.getkeys('read', 'def'))):
        return

    r = _infer_diearea(chip)
    if r is None:
        return
    diearea, corearea = r

    chip.set('asic', 'diearea', diearea)
    chip.set('asic', 'corearea', corearea)

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    #Check log file for errors and statistics
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    design = chip.get('design')
    logfile = f"{step}.log"

    # parsing log file
    errors = 0
    warnings = 0
    metric = None

    with open(logfile) as f:
        for line in f:
            metricmatch = re.search(r'^SC_METRIC:\s+(\w+)', line)
            errmatch = re.match(r'^Error:', line)
            warnmatch = re.match(r'^\[WARNING', line)
            area = re.search(r'^Design area (\d+)\s+u\^2\s+(.*)\%\s+utilization', line)
            tns = re.search(r'^tns (.*)', line)
            wns = re.search(r'^wns (.*)', line)
            slack = re.search(r'^worst slack (.*)', line)
            vias = re.search(r'^Total number of vias = (.*).', line)
            wirelength = re.search(r'^Total wire length = (.*) um', line)
            power = re.search(r'^Total(.*)', line)
            if metricmatch:
                metric = metricmatch.group(1)
            elif errmatch:
                errors = errors + 1
            elif warnmatch:
                warnings = warnings +1
            elif area:
                #TODO: not sure the openroad utilization makes sense?
                cellarea = round(float(area.group(1)), 2)
                utilization = round(float(area.group(2)), 2)
                totalarea = round(cellarea/(utilization/100), 2)
                chip.set('metric', step, index, 'cellarea', 'real', cellarea, clobber=True)
                chip.set('metric', step, index, 'totalarea', 'real', totalarea, clobber=True)
                chip.set('metric', step, index, 'utilization', 'real', utilization, clobber=True)
            elif tns:
                chip.set('metric', step, index, 'setuptns', 'real', round(float(tns.group(1)), 2), clobber=True)
            elif wns:
                chip.set('metric', step, index, 'setupwns', 'real', round(float(wns.group(1)), 2), clobber=True)
            elif slack:
                chip.set('metric', step, index, metric, 'real', round(float(slack.group(1)), 2), clobber=True)
            elif wirelength:
                chip.set('metric', step, index, 'wirelength', 'real', round(float(wirelength.group(1)), 2), clobber=True)
            elif vias:
                chip.set('metric', step, index, 'vias', 'real', int(vias.group(1)), clobber=True)
            elif metric == "power":
                if power:
                    powerlist = power.group(1).split()
                    leakage = powerlist[2]
                    total = powerlist[3]
                    chip.set('metric', step, index, 'peakpower', 'real', float(total), clobber=True)
                    chip.set('metric', step, index, 'leakagepower', 'real', float(leakage), clobber=True)

    #Setting Warnings and Errors
    chip.set('metric', step, index, 'errors', 'real', errors, clobber=True)
    chip.set('metric', step, index, 'warnings', 'real', warnings, clobber=True)

    #Temporary superhack!rm
    #Getting cell count and net number from DEF
    if errors == 0:
        with open("outputs/" + design + ".def") as f:
            for line in f:
                cells = re.search(r'^COMPONENTS (\d+)', line)
                nets = re.search(r'^NETS (\d+)', line)
                pins = re.search(r'^PINS (\d+)', line)
                if cells:
                    chip.set('metric', step, index, 'cells', 'real', int(cells.group(1)), clobber=True)
                elif nets:
                    chip.set('metric', step, index, 'nets', 'real', int(nets.group(1)), clobber=True)
                elif pins:
                    chip.set('metric', step, index, 'pins', 'real', int(pins.group(1)), clobber=True)

    if step == 'sta':
        # Copy along GDS for verification steps that rely on it
        design = chip.get('design')
        shutil.copy(f'inputs/{design}.gds', f'outputs/{design}.gds')

    #Return 0 if successful
    return 0



##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("openroad.json")
