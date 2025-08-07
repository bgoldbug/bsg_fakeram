################################################################################
# PROCESS CLASS
#
# This class stores the infromation about the process that the memory is being
# generated in. Every memory has a pointer to a process object. The information
# for the process comes from the json configuration file (typically before the
# "sram" list section).
# Additions:
#    - Added required information for asap7 (from ABKGroup's FakeRAM2.0)
################################################################################

class Process:

  def __init__(self, json_data):

    # From JSON configuration file
    self.tech_nm        = int(json_data['tech_nm'])
    self.metalPrefix    = str(json_data['metalPrefix'])
    self.pinWidth_nm    = int(json_data['pinWidth_nm'])
    self.pinPitch_nm    = int(json_data['pinPitch_nm'])
    self.voltage        = str(json_data['voltage'])
    if (self.tech_nm == 7):
      # Required from JSON if tech nm is 7
      self.fin_pitch_nm = int(json_data['fin_pitch_nm'])
      self.metal_track_pitch_nm =  int(json_data['metal_track_pitch_nm'])
      self.contacted_poly_pitch_nm = int(json_data['contacted_poly_pitch_nm'])
      self.column_mux_factor = int(json_data['column_mux_factor'])
      
    # Optional keys
    self.snapWidth_nm   = int(json_data['snapWidth_nm']) if 'snapWidth_nm' in json_data else 1
    self.snapHeight_nm  = int(json_data['snapHeight_nm']) if 'snapHeight_nm' in json_data else 1
    self.flipPins       = str(json_data['flipPins']) if 'flipPins' in json_data else 'false'
    self.pinHeight_nm   = int(json_data['pinHeight_nm']) if 'pinHeight_nm' in json_data else (self.pinWidth_nm) # Default to square pins
    self.vlogTimingCheckSignalExpansion = bool(json_data['vlogTimingCheckSignalExpansion']) if 'vlogTimingCheckSignalExpansion' in json_data else False

    # Converted values
    self.tech_um     = self.tech_nm / 1000.0
    self.pinWidth_um = self.pinWidth_nm / 1000.0
    self.pinHeight_um = self.pinHeight_nm / 1000.0
    self.pinPitch_um = self.pinPitch_nm / 1000.0

