import os
import re
import shutil
import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs():
    '''
    Magic is a chip layout viewer, editor, and circuit verifier with
    built in DRC and LVS engines.

    Documentation: http://opencircuitdesign.com/magic/userguide.html

    Installation: https://github.com/RTimothyEdwards/magic

    Sources: https://github.com/RTimothyEdwards/magic

    '''

    chip = siliconcompiler.Chip()
    chip.load_pdk('skywater130')
    chip.set('arg','index','<index>')

    # check drc
    chip.set('arg','step','drc')
    setup(chip)

    # check lvs
    chip.set('arg','step', 'extspice')
    setup(chip)

    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Setup function for 'magic' tool
    '''

    tool = 'magic'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # magic used for drc and lvs
    #if step not in ('drc', 'extspice'):
    #    raise ValueError(f"Magic tool doesn't support step {step}.")
    script = 'sc_magic.tcl'

    chip.set('eda', tool, 'exe', tool)
    chip.set('eda', tool, 'vswitch', '--version')
    chip.set('eda', tool, 'version', '>=8.3.196')
    chip.set('eda', tool, 'format', 'tcl')
    chip.set('eda', tool, 'copy', 'true') # copy in .magicrc file
    chip.set('eda', tool, 'threads', step, index,  4)
    chip.set('eda', tool, 'refdir', step, index,  refdir)
    chip.set('eda', tool, 'script', step, index,  refdir + '/' + script)

    # set options
    options = []
    options.append('-noc')
    options.append('-dnull')
    options.append('-rcfile')
    options.append('sc.magicrc')
    chip.set('eda', tool, 'option', step, index,  options, clobber=False)

    design = chip.get('design')
    if chip.valid('read', 'gds', step, index):
        chip.add('eda', tool, 'require', step, index, ','.join(['read', 'gds', step, index]))
    else:
        chip.add('eda', tool, 'input', step, index, f'{design}.gds')
    if step == 'extspice':
        chip.add('eda', tool, 'output', step, index, f'{design}.spice')

    # TODO: actually parse errors/warnings in post_process()
    logfile = f"{step}.log"
    chip.set('eda', tool, 'report', step, index, 'errors', logfile)
    chip.set('eda', tool, 'report', step, index, 'warnings', logfile)

    if step == 'drc':
        report_path = f'reports/{design}.drc'
        chip.set('eda', tool, 'report', step, index, 'drvs', report_path)

################################
# Version Check
################################

def parse_version(stdout):
    return stdout.strip('\n')

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution

    Reads error count from output and fills in appropriate entry in metrics
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    design = chip.get('design')

    if step == 'drc':
        report_path = f'reports/{design}.drc'
        with open(report_path, 'r') as f:
            for line in f:
                errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

                if errors:
                    chip.set('metric', step, index, 'drvs', 'real', errors.group(1))

    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("magic.json")
