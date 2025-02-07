source ./sc_manifest.tcl

set sc_step    [dict get $sc_cfg arg step]
set sc_index   [dict get $sc_cfg arg index]

set sc_design  [dict get $sc_cfg design]
set sc_macrolibs [dict get $sc_cfg asic macrolib]
set sc_stackup [dict get $sc_cfg asic stackup]
set sc_runset [dict get $sc_cfg pdk lvs runset netgen $sc_stackup basic]

if {[dict exists $sc_cfg asic exclude $sc_step $sc_index]} {
    set sc_exclude  [dict get $sc_cfg asic exclude $sc_step $sc_index]
} else {
    set sc_exclude [list]
}

set layout_file "inputs/$sc_design.spice"
if {[dict exists $sc_cfg "read" netlist $sc_step $sc_index]} {
    set schematic_file [dict get $sc_cfg "read" netlist $sc_step $sc_index]
} else {
    set schematic_file "inputs/$sc_design.vg"
}


# readnet returns a number that can be used to associate additional files with
# each netlist read in here
set layout_fileset [readnet spice $layout_file]
set schematic_fileset [readnet verilog $schematic_file]

# Read netlists associated with all non-excluded macro libraries
foreach lib $sc_macrolibs {
    if {[lsearch -exact $sc_exclude $lib] < 0} {
        set netlist [dict get $sc_cfg library $lib netlist verilog]
        # Read $netlist into group of files associated with schematic
        readnet verilog $netlist $schematic_fileset
    }
}

lvs "$layout_file $sc_design" "$schematic_file $sc_design" $sc_runset reports/$sc_design.lvs.out -json

exit
