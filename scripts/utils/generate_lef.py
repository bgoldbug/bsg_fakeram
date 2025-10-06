import os
import sys
import math

################################################################################
# GENERATE LEF VIEW
#
# Generate a .lef file based on the given SRAM.
################################################################################
def count_tracks(spare_track_ct, number_of_tracks_available, number_of_pins):
    number_of_spare_tracks=spare_track_ct
    if number_of_spare_tracks < 0:
        print("ERROR: not enough tracks!")
        print(f'tracks needed: {number_of_spare_tracks}')
        sys.exit(1)     
    
    track_count = 1
    while number_of_spare_tracks > 0:
        track_count += 1
        number_of_spare_tracks = number_of_tracks_available - number_of_pins*track_count
    track_count -= 1
    print(f'Track Count: {track_count}')
    return track_count
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
    num_wport   = mem.w_ports
    num_rport   = mem.r_ports
    addr_width  = math.ceil(math.log2(mem.depth))

    # Process parameters
    supply_pin_width = mem.process.PSwidth_um*4
    supply_pin_half_width = supply_pin_width/2
    supply_pin_pitch = mem.process.PSpitch_um*8

    min_lr_width   = mem.process.LRpitch_um
    pin_lr_height  = mem.process.LRheight_um
    min_lr_pitch   = mem.process.LRpitch_um 

    min_tb_width   = mem.process.TBpitch_um
    pin_tb_height  = mem.process.TBheight_um
    min_tb_pitch   = mem.process.TBpitch_um 

    y_offset = 2 * min_lr_pitch   ;# arbitrary offset (looks decent)
    x_offset = 2 * min_tb_pitch; 

    metalPrefix    = mem.process.metalPrefix
    flip           = mem.process.flipPins.lower() == 'true'
    pin_height = mem.process.LRheight_um
    supply_pin_layer = '%s4' % metalPrefix
    # Offset from bottom edge to first pin
    # Offset from bottom edge to first pin
    
    #########################################
    # Calculate the pin spacing (pitch)
    #########################################
    number_of_vertical_tracks_available = math.floor((h - 2*y_offset) / min_lr_pitch)
    print(f'Number of vertical tracks available: {number_of_vertical_tracks_available}')
    number_of_horizontal_tracks_available = math.floor((w - 2*x_offset) / min_tb_pitch)
    print(f'Number of horizontal tracks available: {number_of_horizontal_tracks_available}')
    print(f'Height is {h}, width is {w}')
    number_of_left_pins = math.ceil(((num_wport + num_rwport) * 2 if mem.has_wmask else 1  * bits)/2)
    number_of_spare_left_tracks = number_of_vertical_tracks_available - number_of_left_pins
    print(f'Number of spare left tracks: {number_of_spare_left_tracks}')
    left_track_count = count_tracks(number_of_spare_left_tracks, number_of_vertical_tracks_available, number_of_left_pins)
    left_pin_pitch = min_lr_pitch * left_track_count
    left_group_pitch = math.floor((number_of_vertical_tracks_available - number_of_left_pins*left_track_count) / 2)*mem.process.LRpitch_um 
    print(f"Left track_count complete. pitch is {left_group_pitch}")

    number_of_right_pins = (num_wport + num_rwport) * addr_width + (num_wport + num_rwport) * 3 + math.ceil((num_wport + num_rwport) * (2 if mem.has_wmask else 1) * bits / 2)  
    number_of_spare_right_tracks = number_of_vertical_tracks_available - number_of_right_pins
    print(f'Number of spare right tracks: {number_of_spare_right_tracks}')
    right_track_count = count_tracks(number_of_spare_right_tracks, number_of_vertical_tracks_available, number_of_right_pins)
    right_pin_pitch = min_lr_pitch * right_track_count
    right_group_pitch = math.floor((number_of_vertical_tracks_available - number_of_right_pins*right_track_count) / 2)*mem.process.LRpitch_um 
    print(f"Right track_count complete. pitch is {right_group_pitch}")

    number_of_top_pins = math.ceil((num_rport + num_rwport) * bits / 2) + math.ceil(num_rport * addr_width / 2) + num_rport * 2
    number_of_spare_top_tracks = number_of_horizontal_tracks_available - number_of_top_pins
    print(f'Number of spare top tracks: {number_of_spare_top_tracks}')
    top_track_count = count_tracks(number_of_spare_top_tracks, number_of_horizontal_tracks_available, number_of_top_pins)
    top_pin_pitch = min_tb_pitch * top_track_count
    top_group_pitch = math.floor((number_of_horizontal_tracks_available - number_of_top_pins*top_track_count) / 2)*mem.process.TBpitch_um 
    print(f"Top track_count complete. pitch is {top_group_pitch}")

    number_of_bottom_pins = math.ceil((num_rport + num_rwport) * bits / 2) + math.ceil(num_rport * addr_width / 2)
    number_of_spare_bottom_tracks = number_of_horizontal_tracks_available - number_of_bottom_pins
    print(f'Number of spare bottom tracks: {number_of_spare_bottom_tracks}')
    print(f'Number of bottom pins: {number_of_bottom_pins}')
    bottom_track_count = count_tracks(number_of_spare_bottom_tracks, number_of_horizontal_tracks_available, number_of_bottom_pins)
    bottom_pin_pitch = min_tb_pitch * bottom_track_count
    bottom_group_pitch = math.floor((number_of_horizontal_tracks_available - number_of_bottom_pins*bottom_track_count) / 2)*mem.process.TBpitch_um 

    print(f"Bottom track_count complete. pitch is {bottom_group_pitch}")

    print(f'Final {name} size = {w} x {h}')

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
    # LEF SIGNAL PINS
    ########################################

    y_left_step   = y_offset
    y_right_step  = y_offset
    x_top_step    = x_offset
    x_bottom_step = x_offset
    if (mem.has_wmask):
        for ct in range(num_rwport) :
            for i in range(math.ceil(int(bits)/2)):
                y_left_step = lef_add_pin( fid, mem, f'rw{ct}_mask_in[{i}]', True, 'L', y_left_step, left_pin_pitch )
            y_left_step += left_group_pitch-left_pin_pitch
            for i in range(math.ceil(int(bits)/2), int(bits)):
                y_right_step = lef_add_pin( fid, mem, f'rw{ct}_mask_in[{i}]', True, 'R', y_right_step, right_pin_pitch )
            if math.ceil(int(bits)/2) != int(bits):
                y_right_step += right_group_pitch-right_pin_pitch
        
        for ct in range(num_wport) :
            for i in range(math.ceil(int(bits)/2)):
                y_left_step = lef_add_pin( fid, mem, f'w{ct}_mask_in[{i}]', True, 'L', y_left_step, left_pin_pitch )
            y_left_step += left_group_pitch-left_pin_pitch
            for i in range(math.ceil(int(bits)/2), int(bits)):
                y_right_step = lef_add_pin( fid, mem, f'w{ct}_mask_in[{i}]', True, 'R', y_right_step, right_pin_pitch )
            if math.ceil(int(bits)/2) != int(bits):
                y_right_step += right_group_pitch-right_pin_pitch
    
    for ct in range(num_rwport) :
        for i in range(math.ceil(int(bits)/2)):
            y_left_step = lef_add_pin( fid, mem, f'rw{ct}_wd_in[{i}]', True, 'L', y_left_step, left_pin_pitch )
        y_left_step += left_group_pitch-left_pin_pitch
        for i in range(math.ceil(int(bits)/2), int(bits)):
            y_right_step = lef_add_pin( fid, mem, f'rw{ct}_wd_in[{i}]', True, 'R', y_right_step, right_pin_pitch )
        if math.ceil(int(bits)/2) != int(bits):
            y_right_step += right_group_pitch-right_pin_pitch

    for ct in range(num_wport) :
        for i in range(math.ceil(int(bits)/2)):
            y_left_step = lef_add_pin( fid, mem, f'w{ct}_wd_in[{i}]', True, 'L', y_left_step, left_pin_pitch )
        y_left_step += left_group_pitch-left_pin_pitch
        for i in range(math.ceil(int(bits)/2), int(bits)):
            y_right_step = lef_add_pin( fid, mem, f'w{ct}_wd_in[{i}]', True, 'R', y_right_step, right_pin_pitch )
        if math.ceil(int(bits)/2) != int(bits):
            y_right_step += right_group_pitch-right_pin_pitch
        
    for ct in range(num_rwport) :
        for i in range(math.ceil(int(bits)/2)) :
            x_bottom_step = lef_add_pin( fid, mem, f'rw{ct}_rd_out[{i}]', False, 'B', x_bottom_step, bottom_pin_pitch )
        x_bottom_step += bottom_group_pitch-bottom_pin_pitch
        for i in range(math.ceil(int(bits)/2), int(bits)):
            x_top_step = lef_add_pin( fid, mem, f'rw{ct}_rd_out[{i}]', False, 'T', x_top_step, top_pin_pitch )
        if math.ceil(int(bits)/2) != int(bits):
            x_top_step += top_group_pitch-top_pin_pitch

    for ct in range(num_rport):
        for i in range(math.ceil(int(bits)/2)) :
            x_bottom_step = lef_add_pin( fid, mem, f'r{ct}_rd_out[{i}]', False, 'B', x_bottom_step, bottom_pin_pitch )
        x_bottom_step += bottom_group_pitch-bottom_pin_pitch
        for i in range(math.ceil(int(bits)/2), int(bits)):
            x_top_step = lef_add_pin( fid, mem, f'r{ct}_rd_out[{i}]', False, 'T', x_top_step, top_pin_pitch )
        if math.ceil(int(bits)/2) != int(bits):
            x_top_step += top_group_pitch-top_pin_pitch
    
    

    for ct in range(num_rwport) :
        for i in range(int(addr_width)) :
            y_right_step = lef_add_pin( fid, mem, f'rw{ct}_addr_in[{i}]', True, 'R', y_right_step, right_pin_pitch )
        y_right_step += right_group_pitch-right_pin_pitch

    for ct in range(num_wport) :
        for i in range(int(addr_width)) :
            y_right_step = lef_add_pin( fid, mem, f'w{ct}_addr_in[{i}]', True, 'R', y_right_step, right_pin_pitch )
        y_right_step += right_group_pitch-right_pin_pitch

    for ct in range(num_rport) :
        for i in range(math.ceil(int(addr_width)/2)) :
            x_top_step = lef_add_pin( fid, mem, f'r{ct}_addr_in[{i}]', True, 'T', x_top_step, top_pin_pitch )
        x_top_step += top_group_pitch-top_pin_pitch
        for i in range(math.ceil(int(addr_width)/2), int(addr_width)):
            x_bottom_step = lef_add_pin( fid, mem, f'r{ct}_addr_in[{i}]', True, 'B', x_bottom_step, bottom_pin_pitch )
        if math.ceil(int(addr_width)/2) != int(addr_width):
            x_bottom_step += bottom_group_pitch-bottom_pin_pitch
    # Clock and control pins
    for ct in range(num_rwport) :
        y_right_step = lef_add_pin( fid, mem, f'rw{ct}_we_in', True, 'R', y_right_step, right_pin_pitch )
        y_right_step = lef_add_pin( fid, mem, f'rw{ct}_ce_in', True, 'R', y_right_step, right_pin_pitch)
        y_right_step = lef_add_pin( fid, mem, f'rw{ct}_clk', True, 'R', y_right_step, right_pin_pitch)
    for ct in range(num_wport) :
        y_right_step = lef_add_pin( fid, mem, f'w{ct}_we_in', True, 'R', y_right_step, right_pin_pitch )
        y_right_step = lef_add_pin( fid, mem, f'w{ct}_ce_in', True, 'R', y_right_step, right_pin_pitch )
        y_right_step = lef_add_pin( fid, mem, f'w{ct}_clk', True, 'R', y_right_step, right_pin_pitch)
    for ct in range(num_rport):
        x_top_step = lef_add_pin( fid, mem, f'r{ct}_ce_in', True, 'T', x_top_step, top_pin_pitch )  
        x_top_step = lef_add_pin( fid, mem, f'r{ct}_clk', True, 'T', x_top_step, top_pin_pitch)


    ########################################
    # Create VDD/VSS Straps
    ########################################

   

    # --- configure per-layer geometry ---
    # widths are HALF widths (µm)
    fid.write('  PIN VSS\n')
    fid.write('    DIRECTION INOUT ;\n')
    fid.write('    USE GROUND ;\n')
    fid.write('    PORT\n')
    fid.write('      LAYER %s ;\n' % supply_pin_layer)
    ps_x_offset = 2 * min_tb_pitch
    ps_y_offset = 5 * min_lr_pitch
    if flip: # Vertical straps
        ps_x_step = ps_x_offset
        while ps_x_step <= w - ps_x_offset:
            fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (ps_x_step-supply_pin_half_width, ps_y_offset, ps_x_step+supply_pin_half_width, h-ps_y_offset))
            ps_x_step += supply_pin_pitch*2
    else:  # Horizontal straps
        ps_y_step = ps_y_offset
        while ps_y_step <= h - ps_y_offset:
            fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (ps_x_offset, ps_y_step-supply_pin_half_width, w-ps_x_offset, ps_y_step+supply_pin_half_width))
            ps_y_step += supply_pin_pitch*2
    fid.write('    END\n')
    fid.write('  END VSS\n')

    fid.write('  PIN VDD\n')
    fid.write('    DIRECTION INOUT ;\n')
    fid.write('    USE POWER ;\n')
    fid.write('    PORT\n')
    fid.write('      LAYER %s ;\n' % supply_pin_layer)
    if flip:  # Vertical straps
        ps_x_step = ps_x_offset
        while ps_x_step <= w - ps_x_offset:
            fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (ps_x_step-supply_pin_half_width, ps_y_offset, ps_x_step+supply_pin_half_width, h-ps_y_offset))
            ps_x_step += supply_pin_pitch*2
    else:  # Horizontal straps
        ps_y_step = ps_y_offset
        while ps_y_step <= h - ps_y_offset:
            fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (ps_x_offset, ps_y_step-supply_pin_half_width, w-ps_x_offset, ps_y_step+supply_pin_half_width))
            ps_y_step += supply_pin_pitch*2
    fid.write('    END\n')
    fid.write('  END VDD\n')
    # Horizontal straps

    ########################################
    # Create obstructions
    ########################################

    fid.write('  OBS\n')

    ################
    # Layer 1
    ################

    # No pins (full rect)
    fid.write('    LAYER %s1 ;\n' % metalPrefix)
    fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))

    ################
    # Layer 2
    ################

    # No pins (full rect)
    fid.write('    LAYER %s2 ;\n' % metalPrefix)
    fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))

    ################
    # Layer 3
    ################

    fid.write('    LAYER %s3 ;\n' % metalPrefix)
    fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))
    # # Flipped therefore pins on M3
    # if flip:

    #     # Rect from top to bottom, just right of pins to right edge
    #     fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))


    # # Not flipped therefore no pins on M3 (Full rect)
    # else:
    #     fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))

    ################
    # Layer 4
    ################

    fid.write('    LAYER %s4 ;\n' % metalPrefix)
    fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))
    # # Flipped therefore only vertical pg straps
    # if flip:

    #     # Block under and above the vertical power straps (full width)
    #     fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w, y_offset))
    #     fid.write('    RECT 0 %.3f %.3f %.3f ;\n' % (h-y_offset,w,h))

    # # Not flipped therefore pins on M4 and horizontal pg straps
    # else:

    #     # Block from right of pins to left of straps and a block to the right
    #     # of the straps (full height)
    #     fid.write('    RECT %.3f 0 %.3f %.3f ;\n' % (min_lr_width, x_offset, h))
    #     fid.write('    RECT %.3f 0 %.3f %.3f ;\n' % (w-x_offset, w, h))


       

    # Overlap layer (full rect)
    if (mem.process.tech_nm == 45):
        fid.write('    LAYER OVERLAP ;\n')
        fid.write('    RECT 0 0 %.3f %.3f ;\n' % (w,h))

    # Finish up LEF file
    fid.write('  END\n')
    fid.write('END %s\n' % name)
    fid.write('\n')
    fid.write('END LIBRARY\n')
    fid.close()


def lef_add_pin(fid, mem, pin_name, is_input, side, cursor, pitch):
    layer = mem.process.metalPrefix + ('3' if mem.process.flipPins.lower() == 'true' else '4')
    if (side == 'T' or side == 'B'):
        # Switch layers for preferred direction based on top/bottom pins
        layer = mem.process.metalPrefix + '2' if layer == mem.process.metalPrefix + '3' else mem.process.metalPrefix + '3' 
        pw  = mem.process.TBwidth_um
        ph  = mem.process.TBheight_um
    else:
        pw  = mem.process.LRwidth_um
        ph  = mem.process.LRheight_um
    
    hpw = pw / 2.0
    
    W   = mem.width_um 
    H   = mem.height_um 

    fid.write('  PIN %s\n' % pin_name)
    fid.write('    DIRECTION %s ;\n' % ('INPUT' if is_input else 'OUTPUT'))
    fid.write('    USE SIGNAL ;\n')
    fid.write('    SHAPE ABUTMENT ;\n')
    fid.write('    PORT\n')
    fid.write('      LAYER %s ;\n' % layer)

    if side == 'L':      # vertical strip at left edge
        x0, y0, x1, y1 = 0.0, (cursor - hpw), ph, (cursor + hpw)
    elif side == 'R':    # vertical strip at right edge
        x0, y0, x1, y1 = (W - ph), (cursor - hpw), W, (cursor + hpw)
    elif side == 'T':    # horizontal strip at top edge
        x0, y0, x1, y1 = (cursor - hpw), (H - ph),(cursor + hpw), H
    elif side == 'B':    # horizontal strip at bottom edge
        x0, y0, x1, y1 = (cursor - hpw), 0.0, (cursor + hpw), ph

    fid.write('      RECT %.3f %.3f %.3f %.3f ;\n' % (x0, y0, x1, y1))
    fid.write('    END\n')
    fid.write('  END %s\n' % pin_name)

    return cursor + pitch