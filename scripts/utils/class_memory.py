import math
import re
import os
import sys
from pathlib import Path
from utils.cacti_config import cacti_config

################################################################################
# MEMORY CLASS
#
# This class stores the infromation about a specific memory that is being
# generated. This class takes in a process object, the infromation in one of
# the items in the "sram" list section of the json configuration file, and
# finally runs cacti to generate the rest of the data.
################################################################################

class Memory:

  def __init__( self, process, sram_data , output_dir = None, cacti_dir = None):

    self.process        = process
    self.name           = str(sram_data['name'])
    self.width_in_bits  = int(sram_data['width'])
    self.depth          = int(sram_data['depth'])
    self.num_banks      = int(sram_data['banks'])
    self.cache_type     = str(sram_data['type']) if 'type' in sram_data else 'cache'
    
    # Port configuration - default to 1RW if not specified
    self.port_config    = str(sram_data.get('ports', '1rw'))
    
    # Handle different port configurations
    if self.port_config == '1rw1r':
      self.rw_ports = 1
      self.r_ports = 1
      self.w_ports = 0
    elif self.port_config == '1r1rw':
      self.rw_ports = 1
      self.r_ports = 1
      self.w_ports = 0
    elif self.port_config == '1r1w':
      self.rw_ports = 0
      self.r_ports = 1
      self.w_ports = 1
    elif self.port_config == '2r1w':
      self.rw_ports = 0
      self.r_ports = 2
      self.w_ports = 1
    elif self.port_config == '1rw1r':
      self.rw_ports = 1
      self.r_ports = 1
      self.w_ports = 0
    else: # 1rw
      self.rw_ports = 1
      self.r_ports = 0
      self.w_ports = 0
    
    # Write granularity (default to bit-level if not specified)
    self.write_granularity = int(sram_data.get('write_granularity', 1))
    
    # Write mode (default to write-first if not specified)
    # Options: 'write_first' (write-through), 'read_first' (no-change), 'write_through' (combinational)
    self.write_mode    = str(sram_data.get('write_mode', 'write_first'))

    # clk_ct array contains the amount of clks for rw, r, and w ports respectively
    self.port_clks = [ list(map(int, re.findall(r'-?\d+', clk_grp))) for clk_grp in re.findall(r'\[[^\]]*\]|(?<=,)\s*(?=,|$)|^\s*(?=,|$)', 
                        sram_data.get('port_clks', '[1], [0], [0]').strip())]
    print(self.port_clks)
    self.width_in_bytes = math.ceil(self.width_in_bits / 8.0)
    self.total_size     = self.width_in_bytes * self.depth
    if output_dir: # Output dir was set by command line option
      p = str(Path(output_dir).expanduser().resolve(strict=False))
      self.results_dir = os.sep.join([p, self.name])
    else:
      self.results_dir = os.sep.join([os.getcwd(), 'results', self.name])
    if not os.path.exists( self.results_dir ):
      os.makedirs( self.results_dir )
    if cacti_dir:
      self.cacti_dir = cacti_dir
    else:
      self.cacti_dir = os.environ['CACTI_BUILD_DIR']
    self.__run_cacti()
    with open( os.sep.join([self.results_dir, 'cacti.cfg.out']), 'r' ) as fid:
      lines = [line for line in fid]
      cacti_data = lines[-1].split(',')

    self.tech_node_nm                = int(cacti_data[0])
    self.capacity_bytes              = int(cacti_data[1])
    self.associativity               = int(cacti_data[2])
    self.output_width_bits           = int(cacti_data[3])
    self.access_time_ns              = float(cacti_data[4])
    self.cycle_time_ns               = float(cacti_data[5])
    #self.dyn_search_energy_nj        = float(cacti_data[6])
    self.dyn_read_energy_nj          = float(cacti_data[7])
    self.dyn_write_energy_nj         = float(cacti_data[8])
    self.standby_leakage_per_bank_mW = float(cacti_data[9])
    self.area_mm2                    = float(cacti_data[10])
    self.fo4_ps                      = float(cacti_data[11])
    self.width_um                    = float(cacti_data[12])
    self.height_um                   = float(cacti_data[13])

    self.cap_input_pf = 0.005

    self.tech_node_um = self.tech_node_nm / 1000.0

    print(f'Original {self.name} size = {self.width_um} x {self.height_um}')
    print(f'Port configuration: {self.port_config}')
    print(f'Write granularity: {self.write_granularity} bits')
    
    # Adjust to snap
    self.width_um = (math.ceil((self.width_um*1000.0)/self.process.snapWidth_nm)*self.process.snapWidth_nm)/1000.0
    self.height_um = (math.ceil((self.height_um*1000.0)/self.process.snapHeight_nm)*self.process.snapHeight_nm)/1000.0
    self.area_um2 = self.width_um * self.height_um

    #self.pin_dynamic_power_mW = (0.5 * self.cap_input_pf * (float(self.process.voltage)**2))*1e9 ;# P = 0.5*CV^2
    self.pin_dynamic_power_mW = self.dyn_write_energy_nj

    self.t_setup_ns = 0.050  ;# arbitrary 50ps setup
    self.t_hold_ns  = 0.050  ;# arbitrary 50ps hold

  # __run_cacti: shell out to cacti to generate a csv file with more data
  # regarding this memory based on the input parameters from the json
  # configuration file.
  def __run_cacti( self ):
    # For different port configurations, configure CACTI appropriately
    rw_ports = self.rw_ports
    r_ports = self.r_ports if hasattr(self, 'r_ports') else 0
    w_ports = self.w_ports if hasattr(self, 'w_ports') else 0
    
    fid = open(os.sep.join([self.results_dir,'cacti.cfg']), 'w')
    fid.write( cacti_config.format( self.total_size
             , self.width_in_bytes, rw_ports, r_ports, w_ports
             , self.process.tech_um, self.width_in_bytes*8, self.num_banks
             , self.cache_type ))
    fid.close()
    odir = os.getcwd()
    os.chdir(self.cacti_dir )
    cmd = os.sep.join(['.','cacti -infile ']) + os.sep.join([self.results_dir,'cacti.cfg'])
    os.system( cmd)
    os.chdir(odir)

