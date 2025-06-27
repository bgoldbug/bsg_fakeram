import os
import sys
import math

################################################################################
# GENERATE LEF VIEW - ACCURATE TO SPECIALIZED LOGIC
#
# Generate a .lef file with the exact pin naming used in specialized logic
################################################################################

def generate_lef( mem ):

    # File pointer
    fid = open(os.sep.join([mem.results_dir, mem.name + '.lef']), 'w')

    # Memory parameters
    name        = mem.name
    depth       = mem.depth
    bits        = mem.width_in_bits
    w           = mem.width_um
    h           = mem.height_um
    num_rwport  = mem.rw_ports
    num_rport   = mem.r_ports if hasattr(mem, 'r_ports') else 0
    addr_width  = math.ceil(math.log2(mem.depth))
    has_byte_write = hasattr(mem, 'write_granularity') and mem.write_granularity == 8
    num_bytes = bits // 8 if has_byte_write else 0

    # Process parameters
    min_pin_width   = mem.process.pinWidth_um
    pin_height      = mem.process.pinHeight_um
    min_pin_pitch   = mem.process.pinPitch_um
    metalPrefix     = mem.process.metalPrefix
    flip            = mem.process.flipPins.lower() == 'true'

    # Offset from bottom edge to first pin
    x_offset = 10 * min_pin_pitch   ;# arbitrary offset
    y_offset = 10 * min_pin_pitch   ;# arbitrary offset

    #########################################
    # Calculate the pin spacing (pitch)
    #########################################

    # Count total pins for specialized interface
    # Port 0 (RW): clk0, csb0, web0, addr0[n:0], din0[m:0], dout0[m:0], [wmask0[b:0]]
    # Port 1 (R): clk1, csb1, addr1[n:0], dout1[m:0]
    
    number_of_pins = 0
    # Port 0 pins
    number_of_pins += 3  # clk0, csb0, web0
    number_of_pins += addr_width  # addr0
    number_of_pins += bits * 2  # din0, dout0
    if has_byte_write:
        number_of_pins += num_bytes  # wmask0
    
    # Port 1 pins (if present)
    if num_rport > 0:
        number_of_pins += 2  # clk1, csb1
        number_of_pins += addr_width  # addr1
        number_of_pins += bits  # dout1
    
    number_of_tracks_available = math.floor((h - 2*y_offset) / min_pin_pitch)
    number_of_spare_tracks = number_of_tracks_available - number_of_pins

    print(f'Final {name} size = {w} x {h}')
    print(f'num pins: {number_of_pins}, available tracks: {number_of_tracks_available}')
    if number_of_spare_tracks < 0:
        print("ERROR: not enough tracks!")
        sys.exit(1)        

    track_count = 1
    while number_of_spare_tracks > 0:
        track_count += 1
        number_of_spare_tracks = number_of_tracks_available - number_of_pins*track_count
    track_count -= 1

    pin_pitch = min_pin_pitch * track_count
    
    # Calculate group pitch
    num_groups = 6 if num_rport > 0 else 4  # More groups for specialized interface
    group_pitch = math.floor((number_of_tracks_available - number_of_pins*track_count) / num_groups)*mem.process.pinPitch_um

    #########################################
    # LEF HEADER
    #########################################

    fid.write('VERSION 5.7 ;\n')
    fid.write('BUSBITCHARS "[]" ;\n')
    fid.write('MACRO %s\n' % (name))
    fid.write('  FOREIGN %s 0 0 ;\n' % (name))
    fid.write('  SYMMETRY X Y R90 ;\n')
    fid.write('  SIZE %.3f BY %.3f ;\n' % (w,h))
    fid.write('  CLASS BLOCK ;\n')

    ########################################
    # LEF SIGNAL PINS - Specialized Interface
    ########################################

    y_step = y_offset
    
    # Port 0 Control Pins
    y_step = lef_add_pin( fid, mem, 'clk0', True, y_step, pin_pitch )
    y_step = lef_add_pin( fid, mem, 'csb0', True, y_step, pin_pitch )
    y_step = lef_add_pin( fid, mem, 'web0', True, y_step, pin_pitch )
    
    # Port 0 Address
    y_step += group_pitch-pin_pitch
    for i in range(int(addr_width)) :
        y_step = lef_add_pin( fid, mem, 'addr0[%d]'%i, True, y_step, pin_pitch )
    
    # Port 0 Data In
    y_step += group_pitch-pin_pitch
    for i in range(int(bits)) :
        y_step = lef_add_pin( fid, mem, 'din0[%d]'%i, True, y_step, pin_pitch )
    
    # Port 0 Write Mask (if byte-write)
    if has_byte_write:
        y_step += group_pitch-pin_pitch
        for i in range(int(num_bytes)) :
            y_step = lef_add_pin( fid, mem, 'wmask0[%d]'%i, True, y_step, pin_pitch )
    
    # Port 0 Data Out
    y_step += group_pitch-pin_pitch
    for i in range(int(bits)) :
        y_step = lef_add_pin( fid, mem, 'dout0[%d]'%i, False, y_step, pin_pitch )

    # Port 1 pins (if present)
    if num_rport > 0:
        # Port 1 Control
        y_step += group_pitch-pin_pitch
        y_step = lef_add_pin( fid, mem, 'clk1', True, y_step, pin_pitch )
        y_step = lef_add_pin( fid, mem, 'csb1', True, y_step, pin_pitch )
        
        # Port 1 Address
        for i in range(int(addr_width)) :
            y_step = lef_add_pin( fid, mem, 'addr1[%d]'%i, True, y_step, pin_pitch )
        
        # Port 1 Data Out
        y_step += group_pitch-pin_pitch
        for i in range(int(bits)) :
            y_step = lef_add_pin( fid, mem, 'dout1[%d]'%i, False, y_step, pin_pitch )

    ########################################
    # Create VDD/VSS Straps (same as before)
    ########################################

    supply_pin_width = min_pin_width*4
    supply_pin_half_width = supply_pin_width/2
    supply_pin_pitch = min_pin_pitch*8
    supply_pin_layer = '%s4' % metalPrefix

    # Vertical straps
    if flip:
        x_step = x_offset
        fid.write('  PIN VSS\n')
        fid.write('    DIRECTION INOUT ;\n')
        fid.write('    USE GROUND ;\n')
        fid.write('    PORT\n')
        fid.write('      LAYER %s ;\n' % supply_pin_layer)
        while x_step <= w - x_offset:
            fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (x_step-supply_pin_half_width, y_offset, x_step+supply_pin_half_width, h-y_offset))
            x_step += supply_pin_pitch*2
        fid.write('    END\n')
        fid.write('  END VSS\n')

        x_step = x_offset + supply_pin_pitch
        fid.write('  PIN VDD\n')
        fid.write('    DIRECTION INOUT ;\n')
        fid.write('    USE POWER ;\n')
        fid.write('    PORT\n')
        fid.write('      LAYER %s ;\n' % supply_pin_layer)
        while x_step <= w - x_offset:
            fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (x_step-supply_pin_half_width, y_offset, x_step+supply_pin_half_width, h-y_offset))
            x_step += supply_pin_pitch*2
        fid.write('    END\n')
        fid.write('  END VDD\n')

    # Horizontal straps
    else:
        y_step = y_offset
        fid.write('  PIN VSS\n')
        fid.write('    DIRECTION INOUT ;\n')
        fid.write('    USE GROUND ;\n')
        fid.write('    PORT\n')
        fid.write('      LAYER %s ;\n' % supply_pin_layer)
        while y_step <= h - y_offset:
            fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (x_offset, y_step-supply_pin_half_width, w-x_offset, y_step+supply_pin_half_width))
            y_step += supply_pin_pitch*2
        fid.write('    END\n')
        fid.write('  END VSS\n')

        y_step = y_offset + supply_pin_pitch
        fid.write('  PIN VDD\n')
        fid.write('    DIRECTION INOUT ;\n')
        fid.write('    USE POWER ;\n')
        fid.write('    PORT\n')
        fid.write('      LAYER %s ;\n' % supply_pin_layer)
        while y_step <= h - y_offset:
            fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (x_offset, y_step-supply_pin_half_width, w-x_offset, y_step+supply_pin_half_width))
            y_step += supply_pin_pitch*2
        fid.write('    END\n')
        fid.write('  END VDD\n')

    ########################################
    # Create obstructions
    ########################################

    # Generate obstruction layers (simplified for brevity - same pattern as original)
    fid.write('  OBS\n')
    
    # Layer 1-4 obstructions
    for layer in range(1, 5):
        fid.write('    LAYER %s%d ;\n' % (metalPrefix, layer))
        if layer < 3 or (layer == 3 and not flip) or (layer == 4 and flip):
            # Full obstruction
            fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))
        else:
            # Partial obstructions around pins - simplified
            fid.write('    RECT %.3f 0 %.3f %.3f ;\n' % (pin_height if flip else min_pin_width, w, h))

    # Overlap layer
    fid.write('    LAYER OVERLAP ;\n')
    fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))

    # Finish up LEF file
    fid.write('  END\n')
    fid.write('END %s\n' % name)
    fid.write('\n')
    fid.write('END LIBRARY\n')
    fid.close()

#
# Helper function that adds a signal pin
#
def lef_add_pin( fid, mem, pin_name, is_input, y, pitch ):

  layer = mem.process.metalPrefix + ('3' if mem.process.flipPins.lower() == 'true' else '4')
  pw  = mem.process.pinWidth_um
  hpw = (mem.process.pinWidth_um/2.0) # half pin width
  ph = mem.process.pinHeight_um 

  fid.write('  PIN %s\n' % pin_name)
  fid.write('    DIRECTION %s ;\n' % ('INPUT' if is_input else 'OUTPUT'))
  fid.write('    USE SIGNAL ;\n')
  fid.write('    SHAPE ABUTMENT ;\n')
  fid.write('    PORT\n')
  fid.write('      LAYER %s ;\n' % layer)
  fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (0, y-hpw, ph, y+hpw))
  fid.write('    END\n')
  fid.write('  END %s\n' % pin_name)
  
  return y + pitch