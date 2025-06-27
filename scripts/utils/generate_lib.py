import os
import math
import time
import datetime

################################################################################
# GENERATE LIBERTY VIEW - ACCURATE TO SPECIALIZED LOGIC
#
# Generate a .lib file with the exact interface used in specialized logic
################################################################################

def generate_lib( mem ):

    # Make sure the data types are correct
    name              = str(mem.name)
    depth             = int(mem.depth)
    bits              = int(mem.width_in_bits)
    area              = float(mem.area_um2)
    x                 = float(mem.width_um)
    y                 = float(mem.height_um)
    leakage           = float(mem.standby_leakage_per_bank_mW)*1e3
    tsetup            = float(mem.t_setup_ns)
    thold             = float(mem.t_hold_ns)
    tcq               = float(mem.access_time_ns)
    clkpindynamic     = float(mem.pin_dynamic_power_mW)*1e3
    pindynamic        = float(mem.pin_dynamic_power_mW)*1e1
    min_driver_in_cap = float(mem.cap_input_pf)
    voltage           = float(mem.process.voltage)
    min_period        = float(mem.cycle_time_ns)
    fo4               = float(mem.fo4_ps)/1e3

    # Port configuration
    num_rwport = mem.rw_ports
    num_rport = mem.r_ports if hasattr(mem, 'r_ports') else 0
    has_byte_write = hasattr(mem, 'write_granularity') and mem.write_granularity == 8
    num_bytes = bits // 8 if has_byte_write else 0
    write_mode = mem.write_mode if hasattr(mem, 'write_mode') else 'write_first'

    # Number of bits for address
    addr_width    = math.ceil(math.log2(mem.depth))
    addr_width_m1 = addr_width-1

    # Get the date
    d = datetime.date.today()
    date = d.isoformat()
    current_time = time.strftime("%H:%M:%SZ", time.gmtime())

    # Table indices
    min_slew = 1   * fo4               
    max_slew = 25  * fo4               
    min_load = 1   * min_driver_in_cap 
    max_load = 100 * min_driver_in_cap 

    slew_indicies = '%.3f, %.3f' % (min_slew, max_slew)
    load_indicies = '%.3f, %.3f' % (min_load, max_load)

    # Start generating the LIB file
    LIB_file = open(os.sep.join([mem.results_dir, name + '.lib']), 'w')

    # Write header (same as before)
    write_lib_header(LIB_file, name, date, current_time, voltage, max_slew)
    
    # Write templates
    write_lib_templates(LIB_file, name)
    
    # Write bus types
    write_lib_bus_types(LIB_file, name, bits, addr_width, addr_width_m1, num_bytes, has_byte_write)

    # Start cell definition
    LIB_file.write( 'cell(%s) {\n' % name )
    LIB_file.write( '    area : %.3f;\n' % area)
    LIB_file.write( '    interface_timing : true;\n')
    LIB_file.write( '    memory() {\n')
    LIB_file.write( '        type : ram;\n')
    LIB_file.write( '        address_width : %d;\n' % addr_width)
    LIB_file.write( '        word_width : %d;\n' % bits)
    LIB_file.write( '    }\n')

    # Port 0: RW Port with write mode specific timing
    write_port0_rw(LIB_file, name, bits, addr_width, min_driver_in_cap, min_period, 
                   clkpindynamic, pindynamic, tsetup, thold, tcq, 
                   slew_indicies, load_indicies, min_slew, max_slew, max_load,
                   has_byte_write, num_bytes, write_mode)
    
    # Port 1: R Port (if present)
    if num_rport > 0:
        write_port1_r(LIB_file, name, bits, addr_width, min_driver_in_cap, min_period,
                      clkpindynamic, pindynamic, tsetup, thold, tcq,
                      slew_indicies, load_indicies, min_slew, max_slew, max_load)

    LIB_file.write('    cell_leakage_power : %.3f;\n' % (leakage))
    LIB_file.write('}\n')
    LIB_file.write('\n')
    LIB_file.write('}\n')
    LIB_file.close()

def write_lib_header(f, name, date, current_time, voltage, max_slew):
    '''Write Liberty file header'''
    f.write( 'library(%s) {\n' % name)
    f.write( '    technology (cmos);\n')
    f.write( '    delay_model : table_lookup;\n')
    f.write( '    revision : 1.0;\n')
    f.write( '    date : "%s %s";\n' % (date, current_time))
    f.write( '    comment : "SRAM";\n')
    f.write( '    time_unit : "1ns";\n')
    f.write( '    voltage_unit : "1V";\n')
    f.write( '    current_unit : "1uA";\n')
    f.write( '    leakage_power_unit : "1uW";\n')
    f.write( '    nom_process : 1;\n')
    f.write( '    nom_temperature : 25.000;\n')
    f.write( '    nom_voltage : %s;\n' % voltage)
    f.write( '    capacitive_load_unit (1,pf);\n\n')
    f.write( '    pulling_resistance_unit : "1kohm";\n\n')
    f.write( '    operating_conditions(tt_1.0_25.0) {\n')
    f.write( '        process : 1;\n')
    f.write( '        temperature : 25.000;\n')
    f.write( '        voltage : %s;\n' % voltage)
    f.write( '        tree_type : balanced_tree;\n')
    f.write( '    }\n')
    f.write( '\n')
    f.write( '    /* default attributes */\n')
    f.write( '    default_cell_leakage_power : 0;\n')
    f.write( '    default_fanout_load : 1;\n')
    f.write( '    default_inout_pin_cap : 0.0;\n')
    f.write( '    default_input_pin_cap : 0.0;\n')
    f.write( '    default_output_pin_cap : 0.0;\n')
    f.write( '    default_max_transition : %.3f;\n\n' % max_slew)
    f.write( '    default_operating_conditions : tt_1.0_25.0;\n')
    f.write( '    default_leakage_power_density : 0.0;\n')
    f.write( '\n')
    f.write( '    /* additional header data */\n')
    f.write( '    slew_derate_from_library : 1.000;\n')
    f.write( '    slew_lower_threshold_pct_fall : 20.000;\n')
    f.write( '    slew_upper_threshold_pct_fall : 80.000;\n')
    f.write( '    slew_lower_threshold_pct_rise : 20.000;\n')
    f.write( '    slew_upper_threshold_pct_rise : 80.000;\n')
    f.write( '    input_threshold_pct_fall : 50.000;\n')
    f.write( '    input_threshold_pct_rise : 50.000;\n')
    f.write( '    output_threshold_pct_fall : 50.000;\n')
    f.write( '    output_threshold_pct_rise : 50.000;\n\n')
    f.write( '\n')

def write_lib_templates(f, name):
    '''Write Liberty templates'''
    f.write( '    lu_table_template(%s_mem_out_delay_template) {\n' % name )
    f.write( '        variable_1 : input_net_transition;\n')
    f.write( '        variable_2 : total_output_net_capacitance;\n')
    f.write( '            index_1 ("1000, 1001");\n')
    f.write( '            index_2 ("1000, 1001");\n')
    f.write( '    }\n')
    f.write( '    lu_table_template(%s_mem_out_slew_template) {\n' % name )
    f.write( '        variable_1 : total_output_net_capacitance;\n')
    f.write( '            index_1 ("1000, 1001");\n')
    f.write( '    }\n')
    f.write( '    lu_table_template(%s_constraint_template) {\n' % name )
    f.write( '        variable_1 : related_pin_transition;\n')
    f.write( '        variable_2 : constrained_pin_transition;\n')
    f.write( '            index_1 ("1000, 1001");\n')
    f.write( '            index_2 ("1000, 1001");\n')
    f.write( '    }\n')
    f.write( '    power_lut_template(%s_energy_template_clkslew) {\n' % name )
    f.write( '        variable_1 : input_transition_time;\n')
    f.write( '            index_1 ("1000, 1001");\n')
    f.write( '    }\n')
    f.write( '    power_lut_template(%s_energy_template_sigslew) {\n' % name )
    f.write( '        variable_1 : input_transition_time;\n')
    f.write( '            index_1 ("1000, 1001");\n')
    f.write( '    }\n')
    f.write( '    library_features(report_delay_calculation);\n')

def write_lib_bus_types(f, name, bits, addr_width, addr_width_m1, num_bytes, has_byte_write):
    '''Write Liberty bus type definitions'''
    f.write( '    type (%s_DATA) {\n' % name )
    f.write( '        base_type : array ;\n')
    f.write( '        data_type : bit ;\n')
    f.write( '        bit_width : %d;\n' % bits)
    f.write( '        bit_from : %d;\n' % (int(bits)-1))
    f.write( '        bit_to : 0 ;\n')
    f.write( '        downto : true ;\n')
    f.write( '    }\n')
    f.write( '    type (%s_ADDRESS) {\n' % name)
    f.write( '        base_type : array ;\n')
    f.write( '        data_type : bit ;\n')
    f.write( '        bit_width : %d;\n' % addr_width)
    f.write( '        bit_from : %d;\n' % addr_width_m1)
    f.write( '        bit_to : 0 ;\n')
    f.write( '        downto : true ;\n')
    f.write( '    }\n')
    if has_byte_write:
        f.write( '    type (%s_WMASK) {\n' % name)
        f.write( '        base_type : array ;\n')
        f.write( '        data_type : bit ;\n')
        f.write( '        bit_width : %d;\n' % num_bytes)
        f.write( '        bit_from : %d;\n' % (num_bytes-1))
        f.write( '        bit_to : 0 ;\n')
        f.write( '        downto : true ;\n')
        f.write( '    }\n')

def write_port0_rw(f, name, bits, addr_width, min_driver_in_cap, min_period,
                   clkpindynamic, pindynamic, tsetup, thold, tcq,
                   slew_indicies, load_indicies, min_slew, max_slew, max_load,
                   has_byte_write, num_bytes, write_mode):
    '''Write Port 0 (RW) Liberty definitions'''
    
    # Clock pin
    f.write('    pin(clk0)   {\n')
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % (min_driver_in_cap*5))
    f.write('        clock : true;\n')
    f.write('        min_period           : %.3f ;\n' % (min_period))
    f.write('        internal_power(){\n')
    f.write('            rise_power(%s_energy_template_clkslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (clkpindynamic, clkpindynamic))
    f.write('            }\n')
    f.write('            fall_power(%s_energy_template_clkslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (clkpindynamic, clkpindynamic))
    f.write('            }\n')
    f.write('        }\n')
    f.write('    }\n')
    f.write('\n')

    # Chip select (active low)
    write_control_pin(f, 'csb0', name, min_driver_in_cap, pindynamic, tsetup, thold, slew_indicies, True)
    
    # Write enable (active low)
    write_control_pin(f, 'web0', name, min_driver_in_cap, pindynamic, tsetup, thold, slew_indicies, True)

    # Address bus
    f.write('    bus(addr0)   {\n')
    f.write('        bus_type : %s_ADDRESS;\n' % name)
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % (min_driver_in_cap))
    write_timing_constraint(f, name, 'clk0', tsetup, thold, slew_indicies)
    write_internal_power(f, name, pindynamic, slew_indicies)
    f.write('    }\n')

    # Data input bus
    f.write('    bus(din0)   {\n')
    f.write('        bus_type : %s_DATA;\n' % name)
    f.write('        memory_write() {\n')
    f.write('            address : addr0;\n')
    f.write('            clocked_on : "clk0";\n')
    f.write('        }\n')
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % (min_driver_in_cap))
    write_timing_constraint(f, name, 'clk0', tsetup, thold, slew_indicies)
    write_internal_power_conditional(f, name, pindynamic, slew_indicies, '(web0)', '(! (web0) )')
    f.write('    }\n')

    # Write mask (if byte-write enabled)
    if has_byte_write:
        f.write('    bus(wmask0)   {\n')
        f.write('        bus_type : %s_WMASK;\n' % name)
        f.write('        direction : input;\n')
        f.write('        capacitance : %.3f;\n' % (min_driver_in_cap))
        write_timing_constraint(f, name, 'clk0', tsetup, thold, slew_indicies)
        write_internal_power_conditional(f, name, pindynamic, slew_indicies, '(web0)', '(! (web0) )')
        f.write('    }\n')

    # Data output bus - timing depends on write mode
    f.write('    bus(dout0)   {\n')
    f.write('        bus_type : %s_DATA;\n' % name)
    f.write('        direction : output;\n')
    f.write('        max_capacitance : %.3f;\n' % max_load)
    f.write('        memory_read() {\n')
    f.write('            address : addr0;\n')
    f.write('        }\n')
    
    # Clock-to-Q timing (for all modes)
    write_timing_arc(f, name, 'clk0', tcq, slew_indicies, load_indicies, min_slew, max_slew)
    
    # Additional timing for write_through mode (combinational path)
    if write_mode == 'write_through':
        f.write('        timing() {\n')
        f.write('            related_pin : "addr0" ;\n')
        f.write('            timing_type : combinational;\n')
        f.write('            timing_sense : non_unate;\n')
        f.write('            cell_rise(%s_mem_out_delay_template) {\n' % name)
        f.write('                index_1 ("%s");\n' % slew_indicies)
        f.write('                index_2 ("%s");\n' % load_indicies)
        f.write('                values ( \\\n')
        f.write('                  "%.3f, %.3f", \\\n' % (tcq*0.7, tcq*0.7))  # Slightly faster for combinational
        f.write('                  "%.3f, %.3f" \\\n' % (tcq*0.7, tcq*0.7))
        f.write('                )\n')
        f.write('            }\n')
        f.write('            cell_fall(%s_mem_out_delay_template) {\n' % name)
        f.write('                index_1 ("%s");\n' % slew_indicies)
        f.write('                index_2 ("%s");\n' % load_indicies)
        f.write('                values ( \\\n')
        f.write('                  "%.3f, %.3f", \\\n' % (tcq*0.7, tcq*0.7))
        f.write('                  "%.3f, %.3f" \\\n' % (tcq*0.7, tcq*0.7))
        f.write('                )\n')
        f.write('            }\n')
        f.write('            rise_transition(%s_mem_out_slew_template) {\n' % name)
        f.write('                index_1 ("%s");\n' % load_indicies)
        f.write('                values ("%.3f, %.3f")\n' % (min_slew, max_slew))
        f.write('            }\n')
        f.write('            fall_transition(%s_mem_out_slew_template) {\n' % name)
        f.write('                index_1 ("%s");\n' % load_indicies)
        f.write('                values ("%.3f, %.3f")\n' % (min_slew, max_slew))
        f.write('            }\n')
        f.write('        }\n')
    
    f.write('    }\n')

def write_port1_r(f, name, bits, addr_width, min_driver_in_cap, min_period,
                  clkpindynamic, pindynamic, tsetup, thold, tcq,
                  slew_indicies, load_indicies, min_slew, max_slew, max_load):
    '''Write Port 1 (R) Liberty definitions'''
    
    # Clock pin
    f.write('    pin(clk1)   {\n')
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % (min_driver_in_cap*5))
    f.write('        clock : true;\n')
    f.write('        min_period           : %.3f ;\n' % (min_period))
    f.write('        internal_power(){\n')
    f.write('            rise_power(%s_energy_template_clkslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (clkpindynamic, clkpindynamic))
    f.write('            }\n')
    f.write('            fall_power(%s_energy_template_clkslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (clkpindynamic, clkpindynamic))
    f.write('            }\n')
    f.write('        }\n')
    f.write('    }\n')
    f.write('\n')

    # Chip select (active low)
    write_control_pin(f, 'csb1', name, min_driver_in_cap, pindynamic, tsetup, thold, slew_indicies, True)

    # Address bus
    f.write('    bus(addr1)   {\n')
    f.write('        bus_type : %s_ADDRESS;\n' % name)
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % (min_driver_in_cap))
    write_timing_constraint(f, name, 'clk1', tsetup, thold, slew_indicies)
    write_internal_power(f, name, pindynamic, slew_indicies)
    f.write('    }\n')

    # Data output bus
    f.write('    bus(dout1)   {\n')
    f.write('        bus_type : %s_DATA;\n' % name)
    f.write('        direction : output;\n')
    f.write('        max_capacitance : %.3f;\n' % max_load)
    f.write('        memory_read() {\n')
    f.write('            address : addr1;\n')
    f.write('        }\n')
    write_timing_arc(f, name, 'clk1', tcq, slew_indicies, load_indicies, min_slew, max_slew)
    f.write('    }\n')

def write_control_pin(f, pin_name, sram_name, cap, power, tsetup, thold, slew_indicies, active_low=False):
    '''Write a control pin definition'''
    f.write('    pin(%s){\n' % pin_name)
    f.write('        direction : input;\n')
    f.write('        capacitance : %.3f;\n' % cap)
    if active_low:
        f.write('        /* Active Low Signal */\n')
    write_timing_constraint(f, sram_name, pin_name.replace('0','0').replace('1','1').replace('csb','clk').replace('web','clk'), 
                           tsetup, thold, slew_indicies)
    write_internal_power(f, sram_name, power, slew_indicies)
    f.write('    }\n')

def write_timing_constraint(f, name, related_pin, tsetup, thold, slew_indicies):
    '''Write setup/hold timing constraints'''
    f.write('        timing() {\n')
    f.write('            related_pin : %s;\n' % related_pin)
    f.write('            timing_type : setup_rising ;\n')
    f.write('            rise_constraint(%s_constraint_template) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                index_2 ("%s");\n' % slew_indicies)
    f.write('                values ( \\\n')
    f.write('                  "%.3f, %.3f", \\\n' % (tsetup, tsetup))
    f.write('                  "%.3f, %.3f" \\\n'  % (tsetup, tsetup))
    f.write('                )\n')
    f.write('            }\n')
    f.write('            fall_constraint(%s_constraint_template) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                index_2 ("%s");\n' % slew_indicies)
    f.write('                values ( \\\n')
    f.write('                  "%.3f, %.3f", \\\n' % (tsetup, tsetup))
    f.write('                  "%.3f, %.3f" \\\n'  % (tsetup, tsetup))
    f.write('                )\n')
    f.write('            }\n')
    f.write('        } \n')
    f.write('        timing() {\n')
    f.write('            related_pin : %s;\n' % related_pin)
    f.write('            timing_type : hold_rising ;\n')
    f.write('            rise_constraint(%s_constraint_template) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                index_2 ("%s");\n' % slew_indicies)
    f.write('                values ( \\\n')
    f.write('                  "%.3f, %.3f", \\\n' % (thold, thold))
    f.write('                  "%.3f, %.3f" \\\n'  % (thold, thold))
    f.write('                )\n')
    f.write('            }\n')
    f.write('            fall_constraint(%s_constraint_template) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                index_2 ("%s");\n' % slew_indicies)
    f.write('                values ( \\\n')
    f.write('                  "%.3f, %.3f", \\\n' % (thold, thold))
    f.write('                  "%.3f, %.3f" \\\n'  % (thold, thold))
    f.write('                )\n')
    f.write('            }\n')
    f.write('        }\n')

def write_timing_arc(f, name, related_pin, tcq, slew_indicies, load_indicies, min_slew, max_slew):
    '''Write output timing arc'''
    f.write('        timing() {\n')
    f.write('            related_pin : "%s" ;\n' % related_pin)
    f.write('            timing_type : rising_edge;\n')
    f.write('            timing_sense : non_unate;\n')
    f.write('            cell_rise(%s_mem_out_delay_template) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                index_2 ("%s");\n' % load_indicies)
    f.write('                values ( \\\n')
    f.write('                  "%.3f, %.3f", \\\n' % (tcq, tcq))
    f.write('                  "%.3f, %.3f" \\\n' % (tcq, tcq))
    f.write('                )\n')
    f.write('            }\n')
    f.write('            cell_fall(%s_mem_out_delay_template) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                index_2 ("%s");\n' % load_indicies)
    f.write('                values ( \\\n')
    f.write('                  "%.3f, %.3f", \\\n' % (tcq, tcq))
    f.write('                  "%.3f, %.3f" \\\n' % (tcq, tcq))
    f.write('                )\n')
    f.write('            }\n')
    f.write('            rise_transition(%s_mem_out_slew_template) {\n' % name)
    f.write('                index_1 ("%s");\n' % load_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (min_slew, max_slew))
    f.write('            }\n')
    f.write('            fall_transition(%s_mem_out_slew_template) {\n' % name)
    f.write('                index_1 ("%s");\n' % load_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (min_slew, max_slew))
    f.write('            }\n')
    f.write('        }\n')

def write_internal_power(f, name, power, slew_indicies):
    '''Write internal power for a pin'''
    f.write('        internal_power(){\n')
    f.write('            rise_power(%s_energy_template_sigslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (power, power))
    f.write('            }\n')
    f.write('            fall_power(%s_energy_template_sigslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (power, power))
    f.write('            }\n')
    f.write('        }\n')

def write_internal_power_conditional(f, name, power, slew_indicies, when1, when2):
    '''Write conditional internal power'''
    f.write('        internal_power(){\n')
    f.write('            when : "%s";\n' % when1)
    f.write('            rise_power(%s_energy_template_sigslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (power, power))
    f.write('            }\n')
    f.write('            fall_power(%s_energy_template_sigslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (power, power))
    f.write('            }\n')
    f.write('        }\n')
    f.write('        internal_power(){\n')
    f.write('            when : "%s";\n' % when2)
    f.write('            rise_power(%s_energy_template_sigslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (power, power))
    f.write('            }\n')
    f.write('            fall_power(%s_energy_template_sigslew) {\n' % name)
    f.write('                index_1 ("%s");\n' % slew_indicies)
    f.write('                values ("%.3f, %.3f")\n' % (power, power))
    f.write('            }\n')
    f.write('        }\n')
    