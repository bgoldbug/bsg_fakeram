import os
import math

################################################################################
# Generate a .v file based on the given SRAM matching the exact interface
################################################################################

def generate_verilog(mem, tmChkExpand=False):
  '''Generate a verilog view for the RAM'''
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  addr_width = math.ceil(math.log2(depth))
  crpt_on_x  = 1

  # New Additional vars:
  write_mode               = str(mem.write_mode)
  rw_clks, r_clks, w_clks  = mem.port_clks
  
  unique_clks = list(set(x for sub in mem.port_clks for x in sub))

  byte_write               = 1 if mem.write_granularity == 8 else 0
  # Change masking based on wether byte write attribute exists or not
  
  #############################################
  ###   Generate 'setuphold' timing checks  ###
  #############################################

  # Shortened per-bit and per-signal checks
  setuphold_checks=''
  # rw ports setuphold check
  clk_ctr = 0
  for ct in range(mem.rw_ports):
   # Initial check to see if future r or w ports exist (such that we'll label clk differently)
   if len(unique_clks) == 1: clk_suff = ''  
   elif clk_ctr < len(rw_clks): 
      clk_suff=rw_clks[clk_ctr]
      clk_ctr+=1
   setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, we_in_rw{ct+1}, 0, 0, notifier);\n'
   setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, ce_rw{ct+1}, 0, 0, notifier);\n'
   if tmChkExpand: # per-bit
      for i in range(addr_width): setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, addr_rw{ct+1}{i}, 0, 0, notifier);\n'
      for i in range(      bits): setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, wd_in{ct+1}{i}, 0, 0, notifier);\n'
      for i in range(      bits): setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, w_mask_rw{ct+1}{i}, 0, 0, notifier);\n'
   else:           # per-sig
      setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, addr_rw{ct+1}, 0, 0, notifier);\n'
      setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, wd_in{ct+1}, 0, 0, notifier);\n'
      setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, w_mask_rw{ct+1}, 0, 0, notifier);\n'
  # r ports setuphold check
  clk_ctr = 0
  for ct in range(mem.r_ports):
   if len(unique_clks) == 1: clk_suff = ''  
   elif clk_ctr < len(r_clks): 
      clk_suff=r_clks[clk_ctr]
      clk_ctr+=1
   setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, ce_r{ct+1}, 0, 0, notifier);\n'
   if tmChkExpand: # per-bit
      for i in range(addr_width): setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, addr_r{ct+1}{i}, 0, 0, notifier);\n'
   else:           # per-sig
      setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, addr_r{ct+1}, 0, 0, notifier);\n'
  
  # w ports setuphold check
  clk_ctr = 0
  for ct in range(mem.w_ports):
   if len(unique_clks) == 1: clk_suff = ''  
   elif clk_ctr < len(w_clks): 
      clk_suff=w_clks[clk_ctr]
      clk_ctr+=1
   setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, ce_w{ct+1}, 0, 0, notifier);\n'
   if tmChkExpand: # per-bit
      for i in range(addr_width): setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, addr_w{ct+1}{i}, 0, 0, notifier);\n'
      for i in range(      bits): setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, wd_in_w{ct+1}{i}, 0, 0, notifier);\n'
      for i in range(      bits): setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, w_mask_w{ct+1}{i}, 0, 0, notifier);\n'
   else:           # per-sig
      setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, addr_w{ct+1}, 0, 0, notifier);\n'
      setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, wd_in_w{ct+1}, 0, 0, notifier);\n'
      setuphold_checks += f'      $setuphold (posedge clk{clk_suff}, w_mask_w{ct+1}, 0, 0, notifier);\n'
  #################################################
  ###   END Generate 'setuphold' timing checks  ###
  #################################################
  fout = os.sep.join([mem.results_dir, name + '.v'])

  with open(fout, 'w') as f:
   TEMPLATE_MAPPING = {
      "1r1w"  : VLOG_TEMPLATE_1r1w,
      "2r1w"  : VLOG_TEMPLATE_2r1w,
      "1rw1r" : VLOG_TEMPLATE_1rw1r,
      "1rw"   : VLOG_TEMPLATE_1rw
   } 
   MEM_CONFIG       = {
      "name": name,
      "data_width" : bits,
      "depth" : depth,
      "addr_width" : addr_width,
      "crpt_on_x" : crpt_on_x,
      "setuphold_checks": setuphold_checks
   }
   # Memory Specific configs:
   if mem.port_config == "1r1w":
      MEM_CONFIG["start_of_rw_p1"] = generate_start_mode_priority(write_mode, "rd_out_r1", "addr_r1", "ce_r1")
      MEM_CONFIG["end_of_rw_p1"] = generate_end_mode_priority(write_mode, "rd_out_r1", "addr_r1", "ce_r1")
      MEM_CONFIG["byte_write_logic"] = generate_byte_write_logic(byte_write, bits // 8, 'w1')
   elif mem.port_config == "2r1w":
      MEM_CONFIG["start_of_rw_p1"] = generate_start_mode_priority(write_mode, "rd_out_r1", "addr_r1", "ce_r1")
      MEM_CONFIG["end_of_rw_p1"] = generate_end_mode_priority(write_mode, "rd_out_r1", "addr_r1", "ce_r1")
      MEM_CONFIG["start_of_rw_p2"] = generate_start_mode_priority(write_mode, "rd_out_r2", "addr_r2", "ce_r2")
      MEM_CONFIG["end_of_rw_p2"] = generate_end_mode_priority(write_mode, "rd_out_r2", "addr_r2", "ce_r2")
      MEM_CONFIG["byte_write_logic"] = generate_byte_write_logic(byte_write, bits // 8, 'w1')
   elif mem.port_config == "1rw1r" or mem.port_config == "1rw":
      MEM_CONFIG["start_of_rw_p1"] = generate_start_mode_priority(write_mode, "rd_out_rw1", "addr_rw1")
      MEM_CONFIG["end_of_rw_p1"] = generate_end_mode_priority(write_mode, "rd_out_rw1", "addr_rw1")
      MEM_CONFIG["byte_write_logic"] = generate_byte_write_logic(byte_write, bits // 8, 'rw1')
   elif mem.port_config not in TEMPLATE_MAPPING:
      print(f"Listed config '{mem.port_config}' doesn't exist!\nExiting...\n")
      exit(1)
   # Generate RW port logic based on write mode
   f.write(TEMPLATE_MAPPING[mem.port_config].format(**MEM_CONFIG))

   


def generate_verilog_bb(mem):
  '''Generate a verilog black-box view for the RAM'''
  name  = str(mem.name)
  depth = int(mem.depth)
  bits  = int(mem.width_in_bits)
  addr_width = math.ceil(math.log2(depth))
  has_rport = hasattr(mem, 'r_ports') and mem.r_ports > 0
  byte_write = hasattr(mem, 'write_granularity') and mem.write_granularity == 8
  crpt_on_x = 1
  fout = os.sep.join([mem.results_dir, name + '.bb.v'])
  with open(fout, 'w') as f:
      # Prepare byte-write parameters for black box
      BB_TEMPLATE_MAPPING = {
         "1r1w"  : VLOG_BB_TEMPLATE_1r1w,
         "2r1w"  : VLOG_BB_TEMPLATE_2r1w,
         "1rw1r" : VLOG_BB_TEMPLATE_1rw1r,
         "1rw"   : VLOG_BB_TEMPLATE_1rw
      } 
      # Configs that all fakeram memory will require 
      BB_MEM_CONFIG       = {
         "name": name,
         "data_width" : bits,
         "depth" : depth,
         "addr_width" : addr_width,
         "crpt_on_x" : crpt_on_x
      }

      if mem.port_config not in BB_TEMPLATE_MAPPING:
         print(f"Listed config '{mem.port_config}' doesn't exist!\n")
         exit(1)

      f.write(BB_TEMPLATE_MAPPING[mem.port_config].format(**BB_MEM_CONFIG))

# Dynamic write mode setup. Specialized check for ce read mode
def generate_start_mode_priority(write_mode, regname, addrname, ce_r=None,):
   if write_mode == 'read_first':
      if (ce_r):
         return f'''      
         if ({ce_r})
            {regname} <= mem[{addrname}];
         else
            {regname} <= 'x;'''
      else:
         return f"{regname} <= mem[{addrname}];"
   else:
      return ''

def generate_end_mode_priority(write_mode, regname, addrname, ce_r=None,):
   if write_mode == 'read_first':
      return ''
   else:
      if (ce_r):
         return f'''      
         if ({ce_r})
            {regname} <= mem[{addrname}];
         else
            {regname} <= 'x;'''
      else:
         return f"{regname} <= mem[{addrname}];"

def generate_byte_write_logic(byte_write, num_bytes, portnum):
  '''Generate the byte-write logic for memories that support it'''
  if not byte_write:
    return f'mem[addr_{portnum}] <= (wd_in_{portnum} & w_mask_{portnum}) | (mem[addr_{portnum}] & ~w_mask_{portnum});'
  else:
    return f'mem[addr_{portnum}][{num_bytes*8+7}:{num_bytes*8}] <= (wd_in_{portnum}[{num_bytes*8+7}:{num_bytes*8}] & w_mask_{portnum}[{num_bytes*8+7}:{num_bytes*8}]) | (mem[addr_{portnum}][{num_bytes*8+7}:{num_bytes*8}] & ~w_mask_{portnum}[{num_bytes*8+7}:{num_bytes*8}]);'


VLOG_TEMPLATE_1r1w = '''\
module {name}
(
   clk,
   rd_out_r1,
   addr_r1,
   addr_w1,
   we_in_w1,
   wd_in_w1,
   w_mask_w1,
   ce_r1,
   ce_w1
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out_r1;
   input  [ADDR_WIDTH-1:0]  addr_r1;
   input  [ADDR_WIDTH-1:0]  addr_w1;
   input                    we_in_w1;
   input  [BITS-1:0]        wd_in_w1;
   input  [BITS-1:0]   w_mask_w1;
   input                    clk;
   input                    ce_r1;
   input                    ce_w1;

   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];
   integer j;

   always @(posedge clk)
   begin
      // Write port
      {start_of_rw_p1}
      if (ce_w1)
      begin
         if (corrupt_mem_on_X_p && ((^we_in_w === 1'bx) || (^addr_w === 1'bx)))
         begin
            for (j = 0; j < WORD_DEPTH; j = j + 1)
               mem[j] <= 'x;
         end
         else if (we_in_w1)
         begin
            {byte_write_logic}
         end
      end
      {end_of_rw_p1}
   end
   `ifdef SRAM_TIMING
   reg notifier;
   specify
      (posedge clk *> rd_out_r1) = (0, 0);
      $width     (posedge clk, 0, 0, notifier);
      $width     (negedge clk, 0, 0, notifier);
      $period    (posedge clk, 0, notifier);
{setuphold_checks}
   endspecify
   `endif

endmodule
'''

VLOG_TEMPLATE_2r1w = '''\
module {name}
(
   clk,
   rd_out_r1,
   rd_out_r2,
   addr_r1,
   addr_r2,
   addr_w1,
   we_in_w1,
   wd_in_w1,
   w_mask_w1,
   ce_r1,
   ce_r2,
   ce_w1
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out_r1;
   output reg [BITS-1:0]    rd_out_r2;
   input  [ADDR_WIDTH-1:0]  addr_r1;
   input  [ADDR_WIDTH-1:0]  addr_r2;
   input  [ADDR_WIDTH-1:0]  addr_w1;
   input                    we_in_w1;
   input  [BITS-1:0]        wd_in_w1;
   input  [BITS-1:0]   w_mask_w1;
   input                    clk;
   input                    ce_r1;
   input                    ce_r2;
   input                    ce_w1;

   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];
   integer j;

   always @(posedge clk)
   begin
      {start_of_rw_p1}
      {start_of_rw_p2}
      // Write port
      if (ce_w1)
      begin
         if (corrupt_mem_on_X_p && ((^we_in_w === 1'bx) || (^addr_w === 1'bx)))
         begin
            for (j = 0; j < WORD_DEPTH; j = j + 1)
               mem[j] <= 'x;
         end
         else if (we_in_w1)
         begin
            {byte_write_logic}
         end
      end
      {end_of_rw_p1}
      {end_of_rw_p1}
   end

   `ifdef SRAM_TIMING
   reg notifier;
   specify
      (posedge clk *> rd_out_r1) = (0, 0);
      (posedge clk *> rd_out_r2) = (0, 0);
      $width     (posedge clk, 0, 0, notifier);
      $width     (negedge clk, 0, 0, notifier);
      $period    (posedge clk, 0, notifier);
{setuphold_checks}
   endspecify
   `endif
endmodule '''

VLOG_TEMPLATE_1rw1r = '''\
module {name} (
    // Port 0: RW (Write/Read Port)
    clk0,
    ce_rw1,
    we_in_rw1,
    w_mask_rw1,
    addr_rw1,
    wd_in_rw1,
    rd_out_rw1,
    // Port 1: R (Read-Only Port)
    clk1,
    ce_r1,
    addr_r1,
    rd_out_r1
);

   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};


   // Port 0: RW
   input                    clk0;
   input                    ce_rw1;
   input                    we_in_rw1;
   input  [BITS-1:0]        w_mask_rw1;
   input  [ADDR_WIDTH-1:0]  addr_rw1;
   input  [BITS-1:0]        wd_in_rw1;
   output [BITS-1:0]        rd_out_rw1;
   
   // Port 1: R
   input                    clk1;
   input                    ce_r1;
   input  [ADDR_WIDTH-1:0]  addr_r1;
   output [BITS-1:0]        rd_out_r1;

   // Memory array
   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];

   integer i;

   always @(posedge clk0) begin
      if(ce_rw1) 
      begin
         {start_of_rw_p1}
         if (we_in_rw1)   
         begin
            {byte_write_logic}
         end
         {end_of_rw_p1}
      end
   end
   
   
   always @(posedge clk1) begin
      if (ce_r1) begin  // Active low chip select
         rd_out_r1 <= mem[addr_r1];
      end
   end
   

   `ifdef SRAM_TIMING
   reg notifier;
   specify
      // Delays from clk to outputs (registered outputs)
      (posedge clk0 *> rd_out_rw1) = (0, 0);
      (posedge clk1 *> rd_out_r1) = (0, 0);

      // Timing checks
      $width     (posedge clk0,              0, 0, notifier);
      $width     (negedge clk0,              0, 0, notifier);
      $period    (posedge clk0,              0,    notifier);
      $width     (posedge clk1,              0, 0, notifier);
      $width     (negedge clk1,              0, 0, notifier);
      $period    (posedge clk1,              0,    notifier);
{setuphold_checks}
   endspecify
   `endif

endmodule
'''

VLOG_TEMPLATE_1rw = '''\
module {name}
(
   rd_out_rw1,
   addr_rw1,
   we_in_rw1,
   wd_in_rw1,
   w_mask_rw1,
   clk,
   ce_rw1
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out_rw1;
   input  [ADDR_WIDTH-1:0]  addr_rw1;
   input                    we_in_rw1;
   input  [BITS-1:0]        wd_in_rw1;
   input  [BITS-1:0]        w_mask_rw1;
   input                    clk;
   input                    ce_rw1;

   reg    [BITS-1:0]        mem [0:WORD_DEPTH-1];

   integer j;

   always @(posedge clk)
   begin
      if (ce_rw1)
      begin
         {start_of_rw_p1}
         if (corrupt_mem_on_X_p &&
             ((^we_in_rw1 === 1'bx) || (^addr_rw1 === 1'bx))
            )
         begin
            // WEN or ADDR is unknown, so corrupt entire array (using unsynthesizeable for loop)
            for (j = 0; j < WORD_DEPTH; j = j + 1)
               mem[j] <= 'x;
         end
         else if (we_in_rw1)
         begin
            {byte_write_logic}
         end
         // read
         {end_of_rw_p1}
      end
      else
      begin
         // Make sure read fails if ce_in is low
         rd_out <= 'x;
      end
   end

   // Timing check placeholders (will be replaced during SDF back-annotation)
   reg notifier;
   specify
      // Delay from clk to rd_out
      (posedge clk *> rd_out_r1) = (0, 0);

      // Timing checks
      $width     (posedge clk,               0, 0, notifier);
      $width     (negedge clk,               0, 0, notifier);
      $period    (posedge clk,               0,    notifier);
{setuphold_checks}
   endspecify

endmodule
'''
VLOG_BB_TEMPLATE_1r1w = '''\
module {name}
(
   clk,
   rd_out_r1,
   addr_r1,
   addr_w1,
   we_in_w1,
   wd_in_w1,
   w_mask_w1,
   ce_r1,
   ce_w1
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out_r1;
   input  [ADDR_WIDTH-1:0]  addr_r1;
   input  [ADDR_WIDTH-1:0]  addr_w1;
   input                    we_in_w1;
   input  [BITS-1:0]        wd_in_w1;
   input  [BITS-1:0]        w_mask_w1;
   input                    clk;
   input                    ce_r1;
   input                    ce_w1;
endmodule'''

VLOG_BB_TEMPLATE_2r1w = '''\
module {name}
(
   clk,
   rd_out_r1,
   rd_out_r2,
   addr_r1,
   addr_r2,
   addr_w1,
   we_in_w1,
   wd_in_w1,
   w_mask_w1,
   ce_r1,
   ce_r2,
   ce_w1
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out_r1;
   output reg [BITS-1:0]    rd_out_r2;
   input  [ADDR_WIDTH-1:0]  addr_r1;
   input  [ADDR_WIDTH-1:0]  addr_r2;
   input  [ADDR_WIDTH-1:0]  addr_w;
   input                    we_in_w1;
   input  [BITS-1:0]        wd_in_w1;
   input  [BITS-1:0]   w_mask_w1;
   input                    clk;
   input                    ce_r1;
   input                    ce_r2;
   input                    ce_w1;
endmodule'''

VLOG_BB_TEMPLATE_1rw1r = '''\
module {name} (
    // Port 0: RW (Write/Read Port)
    clk0,
    ce_rw1,
    we_in_rw1,
    w_mask_rw1,
    addr_rw1,
    wd_in_rw1,
    rd_out_rw1,
    // Port 1: R (Read-Only Port)
    clk1,
    ce_r1,
    addr_r1,
    rd_out_r1
);

   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};


   // Port 0: RW
   input                    clk0;
   input                    ce_rw1;
   input                    we_in_rw1;
   input  [BITS-1:0]        w_mask_rw1;
   input  [ADDR_WIDTH-1:0]  addr_rw1;
   input  [BITS-1:0]        wd_in_rw1;
   output [BITS-1:0]        rd_out_rw1;
   
   // Port 1: R
   input                    clk1;
   input                    ce_r1;
   input  [ADDR_WIDTH-1:0]  addr_r1;
   output [BITS-1:0]        rd_out_r1;
endmodule
'''

# Template for a verilog 1rw RAM interface
VLOG_BB_TEMPLATE_1rw = '''\
module {name}
(
   rd_out_rw1,
   addr_rw1,
   we_in_rw1,
   wd_in_rw1,
   w_mask_rw1,
   clk,
   ce_rw1
);
   parameter BITS = {data_width};
   parameter WORD_DEPTH = {depth};
   parameter ADDR_WIDTH = {addr_width};
   parameter corrupt_mem_on_X_p = {crpt_on_x};

   output reg [BITS-1:0]    rd_out_rw1;
   input  [ADDR_WIDTH-1:0]  addr_rw1;
   input                    we_in_rw1;
   input  [BITS-1:0]        wd_in_rw1;
   input  [BITS-1:0]        w_mask_rw1;
   input                    clk;
   input                    ce_rw1;

endmodule
'''