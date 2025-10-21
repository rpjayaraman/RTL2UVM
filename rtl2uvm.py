'''
MIT License

Copyright (c) 2025 Jayaraman R P

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''
import pyslang
import argparse
import re
import logging
from tabulate import tabulate
import os
import shutil
import time
import google.generativeai as genai

port_list          = list()  #Store list of all Ports
input_list         = list()  #Store list of in Ports
input_declarators  = list()  #Stroe list of input declarators
output_list        = list()  #Store list of out Ports
output_declarators = list()  #Stroe list of output declarators
all_declarators    = list()  #Contains both input and output declarators
clk_rst_list       = list()  #Stroe list of output declarators
cr_list            = list()  #List with Clock and reset
only_clk           = list()  #List only with Clock signal
only_rst           = list()  #List Only with reset signal
ex_cr              = list()  #List without Clock and Reset
param_list         = list()  #List of parameters available
cp_in_list         = list()  #Coverpoint List

'''
Creating a "tb" folder to save the generated UVM testbench
'''
folder_name ="tb"
if not os.path.exists(folder_name):
  os.makedirs(folder_name)
elif os.path.exists(folder_name):
  shutil.rmtree(folder_name) #Remove if there is an existing folder/files
  os.makedirs(folder_name)

"""
Collects port data from the Verilog design.

This function logs debug information about each port found in the design,
including direction, declarators, and data width. It then appends the port
data to the port_list and categorizes it as input or output.

Args:
  None

Returns:
  None
"""
def collect_port_data():
    logging.debug("Port found in the design: " + str(m_i))  #List of ports used in the verilog file Eg: input [DATA_WIDTH-1:0]din;
    logging.debug("Port Direction          : " + str(m_i.header.direction)) #Eg: input
    logging.debug(m_i.header.direction)
    logging.debug("Port Declarators        : " + str(m_i.declarators)) #Eg: din
    logging.debug("Port Data width         : " + str(m_i.header.dataType))  #[DATA_WIDTH-1:0]
    logging.debug(dir(m_i.kind))
    logging.debug(dir(m_i.kind.name.format))
    logging.debug(m_i)
    port_list.append(m_i)
    if(m_i.header.direction.kind.name == 'InputKeyword'):
        input_list.append(str(m_i))
        input_declarators.append(str(m_i.declarators))
        all_declarators.append(str(m_i.declarators))
    elif(m_i.header.direction.kind.name == 'OutputKeyword'):
        output_list.append(m_i)
        output_declarators.append(str(m_i.declarators))
        all_declarators.append(str(m_i.declarators))

"""
Collects parameter data from the Verilog design.

This function logs debug information about each parameter found in the design.
It then appends the parameter data to the param_list.

Args:
  None

Returns:
  None
"""
def collect_param_data():
    logging.debug(m_i)
    param_list.append(str(m_i))

"""
Parses command-line arguments using argparse.

This function creates an ArgumentParser, adds a required test argument,
an optional mode argument, and an optional coverage argument,
and returns the parsed arguments.

Args:
  None

Returns:
  args (argparse.Namespace): Parsed command-line arguments
"""
def eda_argparse():
    # Create the parser
    parser = argparse.ArgumentParser()
    # Add a required test argument
    parser.add_argument('-t', '--test', type=str, required=True)
    # Add an optional mode argument with a default value 'edaplayground'
    parser.add_argument('-m', '--mode', type=str, choices=['verilator', 'edaplayground'], default='edaplayground', help='Simulation mode: verilator or edaplayground(default: edaplayground)')
    # Add an optional coverage argument
    parser.add_argument('-c', '--coverage', action='store_true', help='Enable coverage in verilator mode')
    parser.add_argument('-llm', '--llm', action='store_true', help='Use gemini for logic generation')
    # Parse the argument
    args = parser.parse_args()
    return args

"""
Sanitizes the DUT name to be a valid folder name.

This function removes any characters that are not alphanumeric or underscores.
It also ensures the name starts with a letter or underscore by adding an underscore at the beginning if needed.

Args:
    dut_name (str): The DUT name extracted from pyslang

Returns:
    str: Sanitized DUT name valid for a folder
"""
def sanitize_dut_name(dut_name):
    sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '', dut_name)
    if not re.match(r'^[a-zA-Z_]', sanitized_name):
        sanitized_name = '_' + sanitized_name
    return sanitized_name

"""
Generates a driver/monitor/scoreboard logic using the Gemini model.

This function sends a prompt to the Gemini model via its API and returns the
generated response, or a default message if the communication fails.

Args:
    prompt (str): The text prompt to send to the Gemini model.

Returns:
   str: The text from the LLM, if it fails returns a default message
"""
def call_gemini(prompt):
    try:
        genai.configure(api_key="YOUR_API_KEY")
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt);
        return response.text
    except Exception as e:
        logging.error(f"Error communicating with Gemini: {e}")
        return



"""
Creates a SystemVerilog interface file based on the provided port data.

This function iterates through the port list, replaces 'input' and 'output'
with 'logic', and writes the modified port data to a file.

Args:
    port_list (list): List of port data objects
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
    verilator_mode(bool): Check if this is verilator mode

Returns:
    None
"""
def create_interface(port_list,dut_name,tb_path,verilator_mode):
  l_intf_file_name=f"{dut_name.strip()}_interface.sv"
  global interface_name
  interface_name =f"{dut_name.strip()}_interface"
  l_intf_path =os.path.join(tb_path,l_intf_file_name)
  for j in input_declarators:
    if re.search(r".*.(pclk|clk|reset|rst|clock).*",str(j), re.IGNORECASE):
      cr_list.append(j)
    if re.search(r".*.(pclk|clk|clock).*",str(j) , re.IGNORECASE):
      only_clk.append(j)
  ports = ", ".join(only_clk)
  with open(l_intf_path,"a+") as file:
    file.write("\ninterface "+interface_name+" (input logic "+ports+");\n")
    if(param_flag):
      for parameter_i in param_list:
        file.write(parameter_i)
    for l_ports in port_list:
      if l_ports not in cr_list:
        tb_interface_input = str(l_ports).replace("input","logic").replace("output reg","logic").replace("output","logic");
        if not re.search(r".*.(pclk|clk|clock).*",str(tb_interface_input), re.IGNORECASE):
          file.write(tb_interface_input)
    file.write("\n//--------------------------------------")
    file.write("\n//Driver Clocking Block")
    file.write("\n//--------------------------------------")
    single_clk = None
    for clk_i in only_clk:    
      single_clk = clk_i.strip()
      file.write("\nclocking driver_cb @(posedge "+single_clk+");")
      
    
    file.write("\n\tdefault input #1 output #1;\n")
    out_drv_ports = ""
    in_drv_ports = ""
    for drv_ports in input_declarators:
      if drv_ports not in cr_list:
        in_drv_ports += f"\toutput {drv_ports};\n"
    for drv_out_ports in output_declarators:
      out_drv_ports += f"\tinput {drv_out_ports};\n"
    file.write(in_drv_ports)
    file.write(out_drv_ports)
    file.write("\nendclocking //driver_cb")

    file.write("\n//--------------------------------------")
    file.write("\n//Monitor Clocking Block")
    file.write("\n//--------------------------------------")
    file.write("\nclocking monitor_cb @(posedge "+single_clk+");")
    file.write("\ndefault input #1 output #1;\n")
    all_mon_ports = ""
    for mon_ports in all_declarators:
      if mon_ports not in cr_list:
        all_mon_ports+= f"\tinput {mon_ports};\n"
    file.write(all_mon_ports)
    file.write("\nendclocking //monitor_cb")

    if not verilator_mode:
      file.write("\n//--------------------------------------")
      file.write("\n//Driver Modport")
      file.write("\n//--------------------------------------")
      file.write("\nmodport DRIVER  (clocking driver_cb,input "+ports+");\n")
      file.write("\n//--------------------------------------")
      file.write("\n//Monitor Modport")
      file.write("\n//--------------------------------------")
      file.write("\nmodport MONITOR (clocking monitor_cb,input "+ports+");\n")

    file.write("\nendinterface //" +interface_name)
  logging.info(f"Successfully Created -> {l_intf_path}")
#End of create_interface

"""
Creates a SystemVerilog sequence item file based on the provided port data.

This function iterates through the port list, replaces 'input' with 'rand bit' and 'output' with 'bit',
and writes the modified port data to a file. It also creates functions for converting to and from strings.

Args:
    port_list (list): List of port data objects
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
Returns:
    None
"""
def create_seqitem(port_list,dut_name,tb_path):
  #http://www.sunburst-design.com/papers/CummingsSNUG2014SV_UVM_Transactions.pdf
  #Defining the excluded signal list
  excluded_signals = ["clk", "clock"]
  l_seq_file_name=f"{dut_name.strip()}_seq_item.sv"
  global seq_item_name #TODO Move this outside of the function
  seq_item_name =f"{dut_name.strip()}_seq_item"
  global l_seq_path
  l_seq_path =os.path.join(tb_path,l_seq_file_name)
  with open(l_seq_path,"a+") as file:
    file.write("//(0) Create a class extending from uvm_sequence_item\n")
    file.write("//(1) Register class with Factory\n")
    file.write("//(2) Declare transaction varaiable\n")
    file.write("//(3) Construct the created class with new()\n") 
    file.write("//(4) Add constraints [if any]\n")
    file.write("class "+ seq_item_name + " extends uvm_sequence_item;\n")
    file.write("\n`uvm_object_utils("+seq_item_name+")\n")
    if(param_flag):
      for parameter_j in param_list:
        file.write(parameter_j)
    for l_ports in port_list:
      if any(excluded_signal.lower() in str(l_ports).lower() for excluded_signal in excluded_signals):
        logging.debug(f"Excluding signal: {l_ports}")
        continue
      tb_seq_input = str(l_ports).replace("input","rand bit").replace("output reg","bit").replace("output","bit");
      file.write(tb_seq_input)

    file.write("\n")
    file.write("\nextern function new( string name = \""+seq_item_name +"\");\n")
    file.write("//extern constraint WRITE_YOUR_OWN_CONSTRAINT;")    
    file.write("\nextern function string input2string();")
    file.write("\nextern function string output2string();")
    file.write("\nextern function string convert2string();\n")
    file.write("\nendclass //" +seq_item_name)

    file.write("\n")
    file.write("\nfunction "+seq_item_name+"::new( string name = \""+seq_item_name +"\");")
    file.write("\n super.new( name );")
    file.write("\nendfunction : new")
    file.write("\n")
    file.write("\n//constraint "+ seq_item_name+"::WRITE_YOUR_OWN_CONSTRAINT{ a!= b; };\n")
    #Input to String
    file.write("\nfunction string "+seq_item_name+"::input2string();\n")
    in_first_half = ""
    for seq_i_ports in input_declarators:
      if seq_i_ports not in cr_list:
        ex_cr.append(seq_i_ports.strip())
    in_first_half='=%0h,'.join(ex_cr)
    in_first_half += "=%0h"
    second_half =','.join(ex_cr)
    file.write(" return $sformatf(\""+in_first_half+"\","+second_half+");")
    file.write("\nendfunction : input2string\n")
    #Output to String
    file.write("\nfunction string "+seq_item_name+"::output2string();\n")
    out_first_half='=%0h,'.join(output_declarators)
    out_first_half += "=%0h"
    out_second_half =','.join(output_declarators)
    file.write(" return $sformatf(\""+out_first_half+"\","+out_second_half+");")
    file.write("\nendfunction : output2string\n")
    #Convert to string
    file.write("\nfunction string "+seq_item_name+"::convert2string();\n")
    file.write(" return ({input2string(), \" \", output2string()});")
    file.write("\nendfunction : convert2string")
  logging.info(f"Successfully Created -> {l_seq_path}")

#End of create_seqitem

"""
Creates a SystemVerilog base sequence file based on the sequence item.

This function creates a class extending from uvm_sequence and defines the
sequence logic for creating sequence items and sending them through the sequencer port.

Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder

Returns:
    None
"""
def create_sequence(dut_name,tb_path):
  l_sequence_file_name=f"{dut_name.strip()}_base_sequence.sv"
  global seq_name
  seq_name=f"{dut_name.strip()}_base_sequence"
  l_sequence_path =os.path.join(tb_path,l_sequence_file_name)
  with open(l_sequence_path,"a+") as file:
    file.write("class "+ seq_name+ " extends uvm_sequence#("+seq_item_name+");\n")
    file.write("\n`uvm_object_utils("+seq_name+")\n")
    file.write(seq_item_name+" req;\n")
    file.write("\nextern function new( string name = \""+seq_name+"\");")
    file.write("\nextern task body();\n")
    file.write("\nendclass //" +seq_name)
    file.write("\n")
    file.write("\nfunction "+seq_name+"::new(string name = \""+seq_name+"\");")
    file.write("\n super.new( name );")
    file.write("\nendfunction : new\n")
    file.write("\ntask "+seq_name+"::body();\n")
    file.write("`uvm_info(get_type_name(), $sformatf(\"Start of " +seq_name + " Sequence\"), UVM_LOW)")
    file.write("\nreq = "+seq_item_name+":: type_id :: create(\"req\");\n")
    file.write("repeat(5) begin //{\n")
    file.write("\t`uvm_do(req)\n")
    file.write("end //}\n")
    file.write("`uvm_info(get_type_name(), $sformatf(\"End of " +seq_name + " Sequence\"), UVM_LOW)\n")
    file.write("\nendtask //"+seq_name)

  logging.info(f"Successfully Created -> {l_sequence_path}")

#End of create_sequence

"""
Creates a SystemVerilog sequencer file based on the sequence item.

This function creates a class extending from uvm_sequencer and defines the
build phase which outputs the standard UVM message.

Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
    verilator_mode(bool): check for verilator mode

Returns:
    None
"""
def create_seqr(dut_name,tb_path, verilator_mode):
  seqr_file_name=f"{dut_name.strip()}_sequencer.sv"
  global seqr_name
  seqr_name=f"{dut_name.strip()}_sequencer"
  l_seqr_path =os.path.join(tb_path,seqr_file_name)
  with open(l_seqr_path,"a+") as file:
    if verilator_mode:
      file.write("class "+ seqr_name + " extends uvm_sequencer#("+seq_item_name+","+seq_item_name+");\n")
    else:
      file.write("class "+ seqr_name + " extends uvm_sequencer#("+seq_item_name+");\n")
    file.write("\n`uvm_component_utils("+seqr_name+")\n")
    file.write("\nextern function new( string name = \""+seqr_name+"\",uvm_component parent=null);\n")
    file.write("extern function void build_phase(uvm_phase phase);\n")
    file.write("\nendclass //" +seqr_name)
    file.write("\n")
    file.write("\nfunction "+seqr_name+"::new(string name,uvm_component parent);")
    file.write("\n super.new(name,parent);")
    file.write("\nendfunction : new\n")
    file.write("\nfunction void "+seqr_name+"::build_phase(uvm_phase phase);")
    file.write("\n super.build_phase(phase);")
    file.write("\n `uvm_info(get_type_name(),\"In Build Phase ...\",UVM_NONE)")
    file.write("\nendfunction : build_phase\n")
  logging.info(f"Successfully Created -> {l_seqr_path}")
#End of create_seqr

"""
Creates a SystemVerilog driver file based on the sequence item and interface.

This function creates a class extending from uvm_driver and defines the
build phase and run phase. The driver interacts with the interface.

Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
    llm_enabled(bool): enables if gemini should be used
Returns:
    None
"""
def create_driver(dut_name,tb_path,llm_enabled):
  driver_file_name=f"{dut_name.strip()}_driver.sv"
  global driver_name
  driver_name=f"{dut_name.strip()}_driver"
  global l_driver_path
  l_driver_path =os.path.join(tb_path,driver_file_name)
  driver_temp_content = f"""class {driver_name} extends uvm_driver#({seq_item_name});
`uvm_component_utils({driver_name})

virtual {interface_name} vif;

extern function new( string name = "{driver_name}",uvm_component parent);
extern function void build_phase(uvm_phase phase);
extern virtual task run_phase(uvm_phase phase);

endclass // {driver_name}


function {driver_name}::new(string name,uvm_component parent);
 super.new(name,parent);
endfunction : new

function void {driver_name}::build_phase(uvm_phase phase);
 super.build_phase(phase);

 `uvm_info(get_type_name(),"In Build Phase ...",UVM_NONE)
	if(!uvm_config_db#(virtual {interface_name})::get(this, "", "vif", vif))
		begin
		`uvm_fatal("NO_VIF",{{"virtual interface must be set for:" ,get_full_name(),".vif"}});
		end
endfunction : build_phase

task {driver_name}::run_phase(uvm_phase phase);
	super.run_phase(phase);

 `uvm_info(get_type_name(),"In Run Phase ...",UVM_NONE)
	forever begin //{{
		{seq_item_name} tr;
		seq_item_port.get_next_item(tr);
		uvm_report_info(get_type_name(), $sformatf("Got Input Transaction %s",tr.input2string()));
		//Driver Logic
		uvm_report_info(get_type_name(), $sformatf("Got Response %s",tr.output2string()));
		seq_item_port.item_done(tr);
	end //}}

endtask: run_phase
"""
  if llm_enabled:
    prompt = f"Goal is to generate uvm driver for the given design. I will provide the reference uvm driver, please make sure you follow the same template. Here is the uvm driver {driver_temp_content}. Given the following DUT code:\n\n{dut_design_file}\n\n" \
    f"Understand the design and consider the input ports {', '.join(input_declarators)} and output ports {', '.join(output_declarators)}. Based on your understanding, generate ONLY the SystemVerilog UVM driver code.Do not include any comments or explanations. Output only the code.No comments. No explanation. No header or footer."
    driver_logic = call_gemini(prompt)
    driver_logic = re.sub(r"```systemverilog\n?", "", driver_logic)  # Remove opening marker
    driver_logic= re.sub(r"```\n?", "", driver_logic)              # Remove closing marker    
    with open(l_driver_path,"a+") as file:
      file.write(driver_logic)
  else:
    with open(l_driver_path,"a+") as file:
      file.write("\nclass "+ driver_name+ " extends uvm_driver#("+seq_item_name+");\n")
      file.write("\n`uvm_component_utils("+driver_name+")\n")
      file.write("\nvirtual "+interface_name+" vif;\n")
      file.write("\nextern function new( string name = \""+driver_name+"\",uvm_component parent);\n")
      file.write("extern function void build_phase(uvm_phase phase);\n")
      file.write("extern virtual task run_phase(uvm_phase phase);\n")
      file.write("\nendclass //" +driver_name)
      file.write("\n")
      file.write("\nfunction "+driver_name+"::new(string name,uvm_component parent);")
      file.write("\n super.new(name,parent);")
      file.write("\nendfunction : new\n")
      file.write("\nfunction void "+driver_name+"::build_phase(uvm_phase phase);")
      file.write("\n super.build_phase(phase);\n")
      file.write("\n `uvm_info(get_type_name(),\"In Build Phase ...\",UVM_NONE)\n")
      file.write("\tif(!uvm_config_db#(virtual "+interface_name+")::get(this, \"\", \"vif\", vif))\n")
      file.write("\t\tbegin\n")
      file.write("\t\t`uvm_fatal(\"NO_VIF\",{\"virtual interface must be set for: \",get_full_name(),\".vif\"});\n")
      file.write("\t\tend")
      file.write("\nendfunction : build_phase\n")
      file.write("\ntask "+driver_name+"::run_phase(uvm_phase phase);\n")
      file.write("\tsuper.run_phase(phase);\n")
      file.write("\n `uvm_info(get_type_name(),\"In Run Phase ...\",UVM_NONE)\n")
      file.write("\tforever begin //{\n")
      file.write("\t\t"+seq_item_name +" tr;\n")
      file.write("\t\tseq_item_port.get_next_item(tr);\n")
      file.write("\t\tuvm_report_info(get_type_name(), $sformatf(\"Got Input Transaction %s\",tr.input2string()));\n")
      file.write("\t\t// Add your driver logic here using the transaction variable tr.\n")
      file.write("\t\tuvm_report_info(get_type_name(), $sformatf(\"Got Response %s\",tr.output2string()));\n")
      file.write("\t\tseq_item_port.item_done(tr);\n")
      file.write("\tend //}\n")
      file.write("\nendtask: run_phase\n")

  logging.info(f"Successfully Created -> {l_driver_path}")

#End of create_driver

"""
Creates a SystemVerilog monitor file based on the sequence item and interface.

This function creates a class extending from uvm_monitor and defines the
build phase and run phase. The monitor interacts with the interface and uses an analysis port
to broadcast data for the coverage and scoreboard.

Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
Returns:
    None
"""
def create_monitor(dut_name,tb_path,llm_enabled):
  monitor_file_name=f"{dut_name.strip()}_monitor.sv"
  global monitor_name
  monitor_name=f"{dut_name.strip()}_monitor"
  global l_monitor_path
  l_monitor_path =os.path.join(tb_path,monitor_file_name)
  monitor_logic_temp = f"""
class {monitor_name} extends uvm_monitor;

uvm_analysis_port#({seq_item_name}) mon_aport;
{seq_item_name} rx;

`uvm_component_utils({monitor_name})

virtual {interface_name} vif;

extern function new( string name = "{monitor_name}",uvm_component parent);
extern function void build_phase(uvm_phase phase);
extern virtual task run_phase(uvm_phase phase);

endclass //{monitor_name}

function {monitor_name}::new(string name,uvm_component parent);
	super.new(name,parent);
	mon_aport=new("mon_aport", this);
endfunction : new

function void {monitor_name}::build_phase(uvm_phase phase);
 super.build_phase(phase);

 `uvm_info(get_type_name(),"In Build Phase ...",UVM_NONE)	'
 if(!uvm_config_db#(virtual {interface_name})::get(this, "", "vif", vif))
		begin
		`uvm_fatal("NO_MON_VIF",{{"virtual interface must be set for: ",get_full_name(),".vif"}});
		end
endfunction : build_phase

task {monitor_name}::run_phase(uvm_phase phase);
	super.run_phase(phase);

 `uvm_info(get_type_name(),"In Run Phase ...",UVM_NONE)

	rx={seq_item_name}::type_id::create("rx",this);
	forever begin //
	//Monitor Logic
    mon_analysis_port.write(rx);
    end
  endtask
	uvm_report_info(get_type_name(), $sformatf("Printing Transaction %s",rx.convert2string()));
		mon_aport.write(rx);
	end

endtask: run_phase
"""
  with open(l_monitor_path,"a+") as file:
    if llm_enabled:
         prompt = f"Given the following DUT code:\n\n{dut_design_file}\n\n" \
         f"and the input ports {', '.join(input_declarators)} and output ports {', '.join(output_declarators)}, and please keep {monitor_logic_temp} as reference and create the response using the same template andunderstand the design and generate ONLY the SystemVerilog UVM monitor code for the design.  Do not include any comments or explanations. Output only the code . No comments. No explanation. No header or footer."
         monitor_logic = call_gemini(prompt)
         monitor_logic = re.sub(r"```systemverilog\n?", "", monitor_logic)  # Remove opening marker
         monitor_logic = re.sub(r"```\n?", "", monitor_logic)              # Remove closing marker    
         file.write(monitor_logic)
    else:
         file.write("`define MON_VIF vif.MONITOR.monitor_cb")
         file.write("\nclass "+ monitor_name+ " extends uvm_monitor;\n")
         file.write("\nuvm_analysis_port#("+seq_item_name+") mon_aport;")
         file.write("\n"+seq_item_name +" rx;\n")
         file.write("\n`uvm_component_utils("+monitor_name+")\n")
         file.write("\nvirtual "+interface_name+" vif;\n")
         file.write("\nextern function new( string name = \""+monitor_name+"\",uvm_component parent);\n")
         file.write("extern function void build_phase(uvm_phase phase);\n")
         file.write("extern virtual task run_phase(uvm_phase phase);\n")
         file.write("\nendclass //" +monitor_name)
         file.write("\n")
         file.write("\nfunction "+monitor_name+"::new(string name,uvm_component parent);\n")
         file.write("\tsuper.new(name,parent);\n")
         file.write("\tmon_aport=new(\"mon_aport\", this);")
         file.write("\nendfunction : new\n")
         file.write("\nfunction void "+monitor_name+"::build_phase(uvm_phase phase);")
         file.write("\n super.build_phase(phase);\n")
         file.write("\n `uvm_info(get_type_name(),\"In Build Phase ...\",UVM_NONE)")
         file.write("\tif(!uvm_config_db#(virtual "+interface_name+")::get(this, \"\", \"vif\", vif))\n")
         file.write("\t\tbegin\n")
         file.write("\t\t`uvm_fatal(\"NO_MON_VIF\",{\"virtual interface must be set for: \",get_full_name(),\".vif\"});\n")
         file.write("\t\tend")
         file.write("\nendfunction : build_phase\n")
         file.write("\ntask "+monitor_name+"::run_phase(uvm_phase phase);\n")
         file.write("\tsuper.run_phase(phase);\n")
         file.write("\n `uvm_info(get_type_name(),\"In Run Phase ...\",UVM_NONE)\n")
         file.write("\n\trx="+seq_item_name+"::type_id::create(\"rx\",this);\n")
         file.write("\t//forever begin //{\n")
         file.write("\t\t//Monitor Logic\n")
         file.write("\t\t// Add your monitor logic here .\n")
         file.write("\t\tuvm_report_info(get_type_name(), $sformatf(\"Printing Transaction %s\",rx.convert2string()));\n")
         file.write("\t\t//mon_aport.write(rx);\n")
         file.write("\t//end //}\n")
         file.write("\nendtask: run_phase\n")

  logging.info(f"Successfully Created -> {l_monitor_path}")

#End of create_monitor

"""
Creates a SystemVerilog agent file based on the sequencer, driver, and monitor.

This function creates a class extending from uvm_agent and defines the
build and connect phases. It creates the instances of sequencer, driver, and monitor.

Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
Returns:
    None
"""
def create_agent(dut_name,tb_path):
  agent_file_name=f"{dut_name.strip()}_agent.sv"
  global agent_name
  agent_name=f"{dut_name.strip()}_agent"
  l_agent_path =os.path.join(tb_path,agent_file_name)
  with open(l_agent_path,"a+") as file:
    file.write("class "+ agent_name+ " extends uvm_agent;\n")
    file.write("\n`uvm_component_utils("+agent_name+")\n")
    file.write(seqr_name+" u_sqr;\n")
    file.write(driver_name+" u_driver;\n")
    file.write(monitor_name+" u_monitor;\n")
    file.write("\nvirtual "+interface_name+" vif;\n")
    file.write("\nextern function new( string name = \""+agent_name+"\",uvm_component parent);\n")
    file.write("extern function void build_phase(uvm_phase phase);\n")
    file.write("extern function void connect_phase(uvm_phase phase);\n")
    file.write("\nendclass //" +agent_name)
    file.write("\n")
    file.write("\nfunction "+agent_name+"::new(string name,uvm_component parent);\n")
    file.write("\tsuper.new(name,parent);\n")
    file.write("endfunction : new\n")
    file.write("\nfunction void "+agent_name+"::build_phase(uvm_phase phase);")
    file.write("\n super.build_phase(phase);\n")
    file.write("\n `uvm_info(get_type_name(),\"In Build Phase ...\",UVM_NONE)\n")
    file.write("\tu_sqr     ="+seqr_name+"   ::type_id::create(\"u_sqr\",this);\n")
    file.write("\tu_driver  ="+driver_name+" ::type_id::create(\"u_driver\",this);\n")
    file.write("\tu_monitor ="+monitor_name+"::type_id::create(\"u_monitor\",this);")
    file.write("\nendfunction : build_phase\n")
    file.write("\nfunction void "+agent_name+"::connect_phase(uvm_phase phase);")
    file.write("\n super.connect_phase(phase);")
    file.write("\n `uvm_info(get_type_name(),\"In Connect Phase ...\",UVM_NONE)\n")
    file.write("\n u_driver.seq_item_port.connect(u_sqr.seq_item_export);")
    file.write("\n `uvm_info(get_type_name(),\"CONNECT_PHASE:Connected Driver and Sequencer\",UVM_NONE)")
    file.write("\nendfunction : connect_phase\n")
  logging.info(f"Successfully Created -> {l_agent_path}")


#End of create_agent

"""
Creates a SystemVerilog scoreboard file based on the sequence item and interface.

This function creates a class extending from uvm_scoreboard and defines the
build and run phases. It uses an analysis port to collect data broadcasted from the monitor
Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
Returns:
    None
"""
def create_sb(dut_name,tb_path,llm_enabled):
  sb_file_name=f"{dut_name.strip()}_scoreboard.sv"
  global sb_name
  sb_name=f"{dut_name.strip()}_scoreboard"
  l_sb_path =os.path.join(tb_path,sb_file_name)
  with open(l_sb_path,"a+") as file:
    file.write("class "+ sb_name+ " extends uvm_scoreboard;\n")
    file.write("\nvirtual "+interface_name+" vif;\n")
    file.write("uvm_analysis_imp#("+seq_item_name+","+sb_name+") sb_export;\n")
    file.write("\n`uvm_component_utils("+sb_name+")\n")
    file.write("\nextern function new( string name = \""+sb_name+"\",uvm_component parent);\n")
    file.write("extern function void build_phase(uvm_phase phase);\n")
    file.write("extern virtual task run_phase(uvm_phase phase);\n")
    file.write("extern virtual function void write("+seq_item_name+" pkt);")
    file.write("\nendclass //" +sb_name)
    file.write("\n")
    file.write("\nfunction "+sb_name+"::new(string name,uvm_component parent);\n")
    file.write("\tsuper.new(name,parent);\n")
    file.write("\tsb_export=new(\"sb_export\", this);\n")
    file.write("endfunction : new\n")
    file.write("\nfunction void "+sb_name+"::build_phase(uvm_phase phase);")
    file.write("\n super.build_phase(phase);\n")
    file.write("\n `uvm_info(get_type_name(),\"In Build Phase ...\",UVM_NONE)\n")
    file.write("\nendfunction : build_phase\n")
    file.write("\ntask "+sb_name+"::run_phase(uvm_phase phase);\n")
    file.write("\tsuper.run_phase(phase);\n")
    file.write("\n `uvm_info(get_type_name(),\"In Run Phase ...\",UVM_NONE)\n")
    #if llm_enabled:
    #     prompt = f"Given the following DUT code:\n\n{dut_design_file}\n\nSequence Item code:\n\n{l_seq_path}\n\nDriver code:\n\n{l_driver_path}\n\nMonitor code:\n\n{l_monitor_path}\n\nunderstand all design modules and input output ports of DUT , sequence item , driver and monitor. Now create system verilog code for `run_phase` task in UVM scoreboard by considering functionality to compare data send by the Driver to the DUT and data observed by the Monitor from the DUT after DUT processing. Do not include any comments or explanations. Output only the code within the `task run_phase(uvm_phase phase)` ... `endtask` block. No comments. No explanation. No header or footer."
    #     sb_logic = call_gemini(prompt)
    #     file.write(sb_logic)
    #else:
    #     file.write("\t\t// Add your Sb logic here .\n")    
    file.write("\nendtask: run_phase\n")
    file.write("\nfunction void "+sb_name+"::write("+seq_item_name+" pkt);\n")
    file.write("\tpkt.print();\n")
    file.write("endfunction : write\n")


  logging.info(f"Successfully Created -> {l_sb_path}")
#End of create_sb

"""
Creates a SystemVerilog coverage file based on the sequence item.

This function creates a class extending from uvm_subscriber and defines the
build, connect and run phases. It uses an analysis port to get the data from the monitor
and adds coverage points using `CFLAGS` in the make file for verilator.

Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
    verilator_mode (bool): If this is verilator mode
Returns:
    None
"""
def create_coverage(dut_name,tb_path,verilator_mode):
  cov_file_name=f"{dut_name.strip()}_coverage.sv"
  global cov_name
  cov_name=f"{dut_name.strip()}_coverage"
  l_cov_path =os.path.join(tb_path,cov_file_name)
  with open(l_cov_path,"a+") as file:
    file.write("class "+ cov_name+ " extends uvm_subscriber#("+seq_item_name+");\n")
    file.write("\n`uvm_component_utils("+cov_name+")\n")
    file.write(seq_item_name+" item;\n")
    file.write("uvm_analysis_imp#("+seq_item_name+","+cov_name+") cov_export;\n")
    if not verilator_mode:
        file.write("covergroup cg_"+cov_name+";\n")
        file.write("\n\toption.per_instance = 1;")
        file.write("\n\toption.name=\"Coverage for "+dut_name+"\";")
        file.write("\n\toption.comment=\"Add your comment\";")
        file.write("\n\toption.goal=100;\n")
        file.write("\n")
        for cp_iter in ex_cr:
            file.write("\tcp_"+cp_iter+": coverpoint (item."+cp_iter+")\n")
            file.write("\t{\n")
            file.write("\t\toption.auto_bin_max = 2;")
            file.write("\n\t}\n")
            cp_in_list.append("cp_"+cp_iter)
        cross_cp= ", ".join(cp_in_list)
        file.write("\n\tcross_cp: cross "+cross_cp+";\n")
        file.write("\nendgroup: cg_"+cov_name)
    file.write("\nextern function new( string name = \""+cov_name+"\",uvm_component parent);\n")
    file.write("extern function void build_phase(uvm_phase phase);\n")
    file.write("extern function void connect_phase(uvm_phase phase);\n")
    file.write("extern virtual task run_phase(uvm_phase phase);\n")
    file.write("extern virtual function void write("+seq_item_name+" t);\n")
    file.write("extern function void report_phase(uvm_phase phase);\n")
    file.write("\nendclass //" +cov_name)
    file.write("\n")
    file.write("\nfunction "+cov_name+"::new(string name,uvm_component parent);\n")
    file.write("\tsuper.new(name,parent);\n")
    if not verilator_mode:
        file.write("\tcg_"+cov_name+"=new();\n")
    file.write("endfunction : new\n")
    file.write("\nfunction void "+cov_name+"::build_phase(uvm_phase phase);")
    file.write("\n super.build_phase(phase);\n")
    file.write("\tcov_export=new(\"cov_export\", this);\n")
    file.write("\n `uvm_info(get_type_name(),\"In Build Phase ...\",UVM_NONE)\n")
    file.write("\nendfunction : build_phase\n")
    file.write("\nfunction void "+cov_name+"::connect_phase(uvm_phase phase);\n")
    file.write("\tsuper.connect_phase(phase);\n")
    file.write("\n `uvm_info(get_type_name(),\"In Connect Phase ...\",UVM_NONE)\n")
    file.write("\nendfunction: connect_phase\n")
    file.write("\ntask "+cov_name+"::run_phase(uvm_phase phase);\n")
    file.write("\tsuper.run_phase(phase);\n")
    file.write("\n `uvm_info(get_type_name(),\"In Run Phase ...\",UVM_NONE)\n")
    file.write("\nendtask: run_phase\n")
    file.write("\nfunction void "+cov_name+"::write("+seq_item_name+" t);\n")
    file.write("\titem=t;\n")
    if not verilator_mode:
      file.write("\tcg_"+cov_name+".sample();\n")
    file.write("endfunction : write\n")
    file.write("\nfunction void "+cov_name+":: report_phase(uvm_phase phase);\n")
    file.write("\tsuper.report_phase(phase);\n")
    if not verilator_mode:
      file.write("\t`uvm_info(get_full_name(),$sformatf(\"Coverage is %f\",cg_"+cov_name+".get_coverage()),UVM_LOW);\n")
    file.write("endfunction: report_phase")


  logging.info(f"Successfully Created -> {l_cov_path}")

#End of create_cov
"""
Creates a SystemVerilog environment file based on the agent, scoreboard and coverage subscriber.

This function creates a class extending from uvm_env and defines the
build and connect phases. It creates the instances of agent, scoreboard and coverage components.

Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
Returns:
    None
"""
def create_env(dut_name,tb_path):
  env_file_name=f"{dut_name.strip()}_env.sv"
  global env_name
  env_name=f"{dut_name.strip()}_env"
  l_env_path =os.path.join(tb_path,env_file_name)
  with open(l_env_path,"a+") as file:
    file.write("class "+ env_name+ " extends uvm_env;\n")
    file.write("\n`uvm_component_utils("+env_name+")\n")
    file.write(agent_name+" u_agent;\n")
    file.write(sb_name+" u_sb;\n")
    file.write(cov_name+" u_cov;\n")
    file.write("\nextern function new( string name = \""+env_name+"\",uvm_component parent);\n")
    file.write("extern function void build_phase(uvm_phase phase);\n")
    file.write("extern function void connect_phase(uvm_phase phase);\n")
    file.write("\nendclass //" +env_name)
    file.write("\n")
    file.write("\nfunction "+env_name+"::new(string name,uvm_component parent);\n")
    file.write("\tsuper.new(name,parent);\n")
    file.write("endfunction : new\n")
    file.write("\nfunction void "+env_name+"::build_phase(uvm_phase phase);")
    file.write("\n super.build_phase(phase);\n")
    file.write("\n `uvm_info(get_type_name(),\"In Build Phase ...\",UVM_NONE)\n")
    file.write("\tu_agent="+agent_name+"::type_id::create(\"u_agent\",this);\n")
    file.write("\tu_sb="+sb_name+"::type_id::create(\"u_sb\",this);\n")
    file.write("\tu_cov="+cov_name+"::type_id::create(\"u_cov\",this);\n")
    file.write("\nendfunction : build_phase\n")
    file.write("\nfunction void "+env_name+"::connect_phase(uvm_phase phase);")
    file.write("\n super.connect_phase(phase);")
    file.write("\n `uvm_info(get_type_name(),\"Connecting monitor and Scoreboard\",UVM_NONE)\n")
    file.write("\tu_agent.u_monitor.mon_aport.connect(u_sb.sb_export);")
    file.write("\tu_agent.u_monitor.mon_aport.connect(u_cov.cov_export);")
    file.write("\nendfunction : connect_phase\n")
  logging.info(f"Successfully Created -> {l_env_path}")


#End of create_env

"""
Creates a SystemVerilog test file based on the environment.

This function creates a class extending from uvm_test and defines the
build and run phases. It creates an instance of the env and starts the sequence

Args:
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
Returns:
    None
"""
def create_test(dut_name,tb_path):
  test_file_name=f"{dut_name.strip()}_test.sv"
  global test_name
  test_name=f"{dut_name.strip()}_test"
  l_test_path =os.path.join(tb_path,test_file_name)
  with open(l_test_path,"a+") as file:
    file.write("class "+ test_name+ " extends uvm_test;\n")
    file.write("\nvirtual "+interface_name+" vif;\n")
    file.write(env_name+" u_env;\n")
    file.write("\t\t"+seq_name +" u_seq;\n")
    file.write("\n`uvm_component_utils("+test_name+")\n")
    file.write("\nextern function new( string name = \""+test_name+"\",uvm_component parent);\n")
    file.write("extern function void build_phase(uvm_phase phase);\n")
    file.write("extern virtual task run_phase(uvm_phase phase);\n")
    file.write("\nendclass //" +test_name)
    file.write("\n")
    file.write("\nfunction "+test_name+"::new(string name,uvm_component parent);")
    file.write("\n super.new(name,parent);")
    file.write("\nendfunction : new\n")
    file.write("\nfunction void "+test_name+"::build_phase(uvm_phase phase);")
    file.write("\n super.build_phase(phase);\n")
    file.write("\n `uvm_info(get_type_name(),\"In Build Phase ...\",UVM_NONE)\n")
    file.write("\tu_env="+env_name+"::type_id::create(\"u_env\",this);")
    file.write("\nendfunction : build_phase\n")
    file.write("\ntask "+test_name+"::run_phase(uvm_phase phase);\n")
    file.write("\tsuper.run_phase(phase);\n")
    file.write("\n\t\t`uvm_info(get_type_name(),\"In Run Phase ...\",UVM_NONE)\n")
    file.write("\t\tu_seq="+seq_name+"::type_id::create(\"u_seq\",this);\n")
    file.write("\t\tphase.raise_objection( this, \"Starting phase objection\");\n")
    file.write("\n")
    file.write("\t\t`uvm_info(get_type_name(), $sformatf(\"Starting Sequence\"), UVM_LOW)\n")
    #file.write("\t\tuvm_top.print_topology();\n")
    file.write("\t\tu_seq.start(u_env.u_agent.u_sqr);\n")
    file.write("\n")
    file.write("\t\tphase.drop_objection( this, \"Dropping phase objection\");")
    file.write("\nendtask: run_phase\n")

  logging.info(f"Successfully Created -> {l_test_path}")

# End of create_test

"""
Creates a SystemVerilog top level file based on all the created UVM components and design.

This function creates a file which is used to connect all the components including DUT

Args:
    port_list (list): List of port data objects
    dut_name (str): Name of the Design Under Test (DUT)
    tb_path(str)  : path to the tb folder
    verilator_mode(bool) : if this is verilator mode
Returns:
    None
"""
def create_top(port_list,dut_name,tb_path, verilator_mode):
  top_file_name=f"{dut_name.strip()}_top.sv"
  global top_name
  top_name=f"{dut_name.strip()}_top"
  l_top_path =os.path.join(tb_path,top_file_name)
  with open(l_top_path,"a+") as file:
    file.write("import uvm_pkg:: *;\n")
    file.write("`include \"uvm_macros.svh\"\n")

    file.write("`include \""+seq_item_name+".sv\"\n")
    file.write("`include \""+seqr_name+".sv\"\n")
    file.write("`include \""+seq_name+".sv\"\n")
    file.write("`include \""+driver_name+".sv\"\n")
    file.write("`include \""+interface_name+".sv\"\n")
    file.write("`include \""+monitor_name+".sv\"\n")
    file.write("`include \""+agent_name+".sv\"\n")
    file.write("`include \""+sb_name+".sv\"\n")
    file.write("`include \""+cov_name+".sv\"\n")
    file.write("`include \""+env_name+".sv\"\n")
    file.write("`include \""+test_name+".sv\"\n")
    file.write("\nmodule "+ top_name+";\n")
    file.write("\n//--------------------------------------")
    file.write("\n//signal declaration: clock and reset")
    file.write("\n//--------------------------------------")
    for l_ports in input_list:
      replace_to_bit = str(l_ports).replace("input","bit")
      if re.search(r".*.(pclk|clk|clock).*", replace_to_bit, re.IGNORECASE):
        clk_rst_list.append(str(replace_to_bit)) #Containts clock and reset
    for i in clk_rst_list:
      file.write(i)
    file.write("\n")
    file.write("\ninitial begin\n")
    for j in input_declarators:
      #if re.search(r".*.(clk|reset|rst|clock).*",str(j) , re.IGNORECASE):
      #  cr_list.append(j)
      #if re.search(r".*.(clk|clock).*",str(j) , re.IGNORECASE):
      #  only_clk.append(j)
      if re.search(r".*.(reset|rst).*",str(j) , re.IGNORECASE):
        only_rst.append(j)
    clk_rst_initial = "=0;".join(only_clk)
    clk_rst_initial += "=0;"
    file.write(clk_rst_initial)
    file.write("\nend")
    file.write("\n//--------------------------------------")
    file.write("\n//clock Generation")
    file.write("\n//--------------------------------------")
    file.write("\nalways begin\n")
    for l in only_clk:
      only_clk_i = l.strip()
      file.write("\t#5 "+only_clk_i+" <= ~"+only_clk_i+";\n") #TODO Make the delay value as a parameter or configurable one
    file.write("end\n")
    file.write("\n//--------------------------------------")
    file.write("\n//Interface Instance")
    file.write("\n//--------------------------------------")
    ports = ", ".join(cr_list)
    file.write("\n"+interface_name+" intf("+only_clk_i+");\n")
    file.write("\n//--------------------------------------")
    file.write("\n//DUT Instance")
    file.write("\n//--------------------------------------")
    file.write("\n"+dut_name+" UUT(\n")
    intf_ports = []
    for iter_i in all_declarators:
      intf_ports.append(f"\t.{iter_i.lstrip()}(intf.{iter_i.lstrip()})")
    file.write(",\n".join(intf_ports))
    file.write("\n);\n")
    file.write("\ninitial begin\n")
    file.write("\tuvm_config_db#(virtual "+interface_name+")::set(uvm_root::get(), \"*\", \"vif\", intf);\n")
    file.write("\t//enable wave dump\n")
    file.write("\t$dumpfile(\"dump.vcd\");\n")
    file.write("\t$dumpvars;")
    file.write("\nend\n")
    file.write("\ninitial begin\n")
    file.write("\trun_test(\""+test_name+"\");")
    file.write("\nend\n")


    file.write("\nendmodule //"+ top_name+"\n")

  logging.info(f"Successfully Created -> {l_top_path}")


# End of create_top

"""
Creates a Makefile for Verilator simulation.

Args:
    dut_name (str): Name of the Design Under Test (DUT).
    verilator_path (str): Path to the verilator folder where the makefile is created
    coverage_flag (bool): Enables coverage if set to true
    ex_cr (list) : list of all the input signals.

Returns:
    None
"""
def create_makefile(dut_name, verilator_path, coverage_flag, ex_cr):
    makefile_path = os.path.join(verilator_path, "Makefile")
    with open(makefile_path, "w") as file:
        file.write("all: simulate\n\n")
        file.write("NPROC = $$((`nproc`-1))\n\n")
        file.write("# -------------------------------------\n")
        file.write("# Testbench setup\n")
        file.write("# -------------------------------------\n")
        file.write("VERILATOR := verilator\n")
        file.write("ifdef VERILATOR_ROOT\n")
        file.write("VERILATOR := $(VERILATOR_ROOT)/bin/verilator\n")
        file.write("endif\n\n")
        search_dirs = [
            os.getcwd(),
            os.path.join(os.getcwd(), ".."),
        ]
        
        # Add all immediate subdirectories (one level below)
        search_dirs.extend([
            os.path.join(os.getcwd(), d)
            for d in os.listdir(os.getcwd())
            if os.path.isdir(os.path.join(os.getcwd(), d))
        ])
        
        uvm_root = None
        for directory in search_dirs:
            candidate = os.path.join(directory, "uvm_verilator")
            if os.path.isdir(candidate):
                uvm_root = os.path.realpath(candidate)
                break
        
        if uvm_root:
            file.write(f"UVM_ROOT ?= {uvm_root}\n")
        else:
            # Optional: fallback or raise an error
            raise FileNotFoundError("uvm_verilator directory not found in current, parent, or immediate subdirectories.")
        file.write(f"UVM_TEST ?= {test_name}\n\n")
        file.write(f"VERILOG_DEFINE_FILES = ${{UVM_ROOT}}/src/uvm.sv ./tb/{top_name}.sv ./tb/{dut_name}.sv\n")
        file.write("VERILOG_INCLUDE_DIRS = tb ${UVM_ROOT}/src\n\n")
        file.write("# -------------------------------------\n")
        file.write("# Compilation/simulation configuration\n")
        file.write("# -------------------------------------\n")
        file.write(f"SIM_NAME ?= {dut_name}_tb\n")
        file.write("SIM_DIR := ../$(SIM_NAME)-sim\n")
        file.write("COMPILE_ARGS += -fno-gate\n")
        file.write("COMPILE_ARGS += -DUVM_NO_DPI\n")
        file.write("COMPILE_ARGS += --prefix $(SIM_NAME) -o $(SIM_NAME)\n")
        file.write("COMPILE_ARGS += $(addprefix +incdir+, $(VERILOG_INCLUDE_DIRS))\n")
        file.write("EXTRA_ARGS += --timescale 1ns/1ps --error-limit 100\n")
        file.write("WARNING_ARGS += -Wno-lint \\\n")
        file.write("\t-Wno-style \\\n")
        file.write("\t-Wno-SYMRSVDWORD \\\n")
        file.write("\t-Wno-IGNOREDRETURN \\\n")
        file.write("\t-Wno-CONSTRAINTIGN \\\n")
        file.write("\t-Wno-ZERODLY\n\n")

        file.write("# -------------------------------------\n")
        file.write("# VCD Configuration\n")
        file.write("# -------------------------------------\n")
        file.write("VCD_VAR := +VCD_DUMP\n")
        file.write("VCD_FILE := dump.vcd\n\n")
        file.write("# -------------------------------------\n")
        file.write("# Make UVM test with Verilator\n")
        file.write("# -------------------------------------\n")
        if coverage_flag:
            file.write(f"$(SIM_DIR)/$(SIM_NAME).mk: $(wildcard tb/*.sv)\n")
            file.write(f"\t$(VERILATOR) --cc --exe --main --timing --assert --trace-depth 2 -Mdir $(SIM_DIR) \\\n")
            file.write(f"\t--coverage \\\n")  #Added coverage flag
            file.write("\t${COMPILE_ARGS} ${EXTRA_ARGS} \\\n")
            file.write("\t${VERILOG_DEFINE_FILES} \\\n")
            file.write("\t${WARNING_ARGS}\n\n")
        else:
            file.write(f"$(SIM_DIR)/$(SIM_NAME).mk: $(wildcard tb/*.sv) \n")
            file.write(f"\t$(VERILATOR) --cc --exe --main --timing --assert --trace-depth 2 -Mdir $(SIM_DIR) \\\n")
            file.write("\t${COMPILE_ARGS} ${EXTRA_ARGS} \\\n")
            file.write("\t${VERILOG_DEFINE_FILES} \\\n")
            file.write("\t${WARNING_ARGS}\n\n")
        file.write(f"$(SIM_DIR)/$(SIM_NAME): $(SIM_DIR)/$(SIM_NAME).mk\n")
        file.write("\t$(MAKE) -j${NPROC} -C $(SIM_DIR) $(BUILD_ARGS) -f $(SIM_NAME).mk\n\n")
        file.write("simulate: $(SIM_DIR)/$(SIM_NAME).mk $(SIM_DIR)/$(SIM_NAME)\n")
        file.write(f"\t#$(SIM_DIR)/$(SIM_NAME) +UVM_TESTNAME=$(UVM_TEST) $(VCD_VAR) +VCD_FILE=$(VCD_FILE)\n")
        file.write(f"\t$(SIM_DIR)/$(SIM_NAME) +UVM_TESTNAME=$(UVM_TEST)\n\n")
        file.write("view_vcd:\n")
        file.write("\tgtkwave $(VCD_FILE)\n\n")
        file.write("clean:\n")
        file.write("\trm -rf simv*.daidir csrc\n")
        file.write("\trm -rf csrc* simv*\n")
        file.write("\trm -rf $(SIM_DIR)\n\n")
        file.write(".PHONY: simulate clean view_vcd\n")

    logging.info(f"Successfully Created -> {makefile_path}")

"""
Prints detailed information about each port in the design.

Args:
    tree (pyslang.SyntaxTree): The parsed syntax tree of the SystemVerilog code.

Returns:
   None
"""
def print_port_details(tree):
   print("----------------------------------------")
   print("            Port Details                ")
   print("----------------------------------------")
   for scope_i in (tree.root.members):
    if(scope_i.kind.name != "ClassDeclaration"):
        dut_name=str(scope_i.header.name) #Used to embed with tb generated files
        #print(f"\nModule: {dut_name}")
        if (hasattr(scope_i, 'members')): #Check if the scope has the attribute called "members"
          for m_i in (scope_i.members):
              if(m_i.kind.name== "PortDeclaration"):
                port_direction = str(m_i.header.direction)
                port_name = str(m_i.declarators)
                port_data_type= str(m_i.header.dataType)
                print(f"    Direction: {port_direction}    Name: {port_name}   DataType: {port_data_type}")
def create_tb_graph(dut_name, tb_path):
    """
    Generates a graph visualization for generated UVM testbench structure

    Args:
        dut_name (str): Name of the Design Under Test (DUT).
        tb_path (str): Path to the testbench folder.

    Returns:
        None
    """
    try:
        import pygraphviz as pgv
    except ImportError:
        logging.warning("pygraphviz is not installed. Skipping graph creation.")
        print("pygraphviz is not installed. Skipping graph creation.")
        return

    dot = pgv.AGraph(comment=f'UVM Testbench - Ports Inside Components', directed=True, strict=False)
    dot.graph_attr['rankdir'] = 'TB'  # Top-to-Bottom layout
    dot.graph_attr['splines'] = 'ortho'  # Use orthogonal edges

    # Create a top level to put the test sub graph
    with dot.subgraph(name='cluster_top', label=top_name, style='rounded') as top_cluster:
        top_cluster.graph_attr['style'] = 'rounded'
        top_cluster.graph_attr['labeljust'] = 'l'  # Align label to be on top

        dut_interface_name = f"{dut_name}_interface"
        top_cluster.add_node('interface', label=dut_interface_name, shape='box', style='filled', fillcolor='lightgreen')
        top_cluster.add_node('DUT', label="DUT:"+dut_name, shape='box', style='filled', fillcolor='gold')  # Adding DUT under the TOP Cluster.



        # Creating Test subgraph
        with top_cluster.subgraph(name='cluster_test', label=f"{dut_name}_test", style='rounded') as test_cluster:
            test_cluster.graph_attr['style'] = 'rounded'
            test_cluster.graph_attr['labeljust'] = 'l'  # Align label to be on top

            # Create sequence item node, name the nodes based on dut name
            dut_seq_item_name = f"{dut_name}_seq_item"
            dut_sequence_name = f"{dut_name}_sequence"

            test_cluster.add_node('sequence_item', label=dut_seq_item_name + "\n" + dut_sequence_name, shape='note', style='filled', fillcolor='azure')


            # Create Env Subgraph.
            with test_cluster.subgraph(name='cluster_env', label=f"{dut_name}_env", style='rounded') as env_cluster:
                env_cluster.graph_attr['style'] = 'rounded'
                env_cluster.graph_attr['labeljust'] = 'l'  # Align label to be on top

                dut_sb_name = f"{dut_name}_scoreboard"
                env_cluster.add_node('coverage', label="[cov_export]" + "\n" + cov_name, shape='box', style='filled', fillcolor = 'lightpink')
                env_cluster.add_node('scoreboard', label="[sb_export]" + "\n" + dut_sb_name, shape='box', style='filled', fillcolor='lightpink')

                # Adding component inside Agent.
                with env_cluster.subgraph(name='cluster_agent', label=f"{dut_name}_agent", style='rounded') as agent_cluster:
                    agent_cluster.graph_attr['style'] = 'rounded'
                    agent_cluster.graph_attr['labeljust'] = 'l'

                    dut_sequencer_name = f"{dut_name}_sequencer"
                    dut_driver_name = f"{dut_name}_driver"
                    dut_monitor_name = f"{dut_name}_monitor"

                    agent_cluster.add_node('monitor', label=dut_monitor_name + "\n" + "[mon_aport]", shape='box', style='filled', fillcolor='deepskyblue', group = "monitor")
                    agent_cluster.add_node('sequencer', label=dut_sequencer_name, shape='box', style='filled', fillcolor='deepskyblue', group = "monitor") 
                    agent_cluster.add_node('driver', label=dut_driver_name, shape='box', style='filled', fillcolor='deepskyblue', group = "monitor") 

                    #Set the graph attribute to be in the right spot for the pointers
                    agent_cluster.graph_attr["groupsep"] = "1.5"



        env_cluster.add_edge('monitor','coverage')   
        env_cluster.add_edge('monitor','scoreboard') 
        top_cluster.add_edge('driver','interface')   
        env_cluster.add_edge('sequencer','driver')   
        test_cluster.add_edge('sequence_item','sequencer')
        top_cluster.add_edge('interface', 'monitor')
        top_cluster.add_edge('interface', 'DUT')

    # Save the graph to a file
    graph_file_path = os.path.join(tb_path, f"{dut_name}_tb_graph.png")
    try:
        dot.draw(graph_file_path, prog='dot', format='png')  # Use 'dot' layout engine
        logging.info(f"Successfully Created -> {graph_file_path}")
        print(f"Successfully Created -> {graph_file_path}")
    except Exception as e:
        logging.error(f"Error generating graph: {e}")
        print(f"Error generating graph: {e}")




args = eda_argparse()
inp_test_name = args.test
sim_mode = args.mode
llm_enabled = args.llm
coverage_flag = args.coverage

print("Reading RTL: " +inp_test_name)
logging.getLogger().setLevel(logging.INFO) #TODO: Make the verbose parameterized 
start_time = time.time() 
tree = pyslang.SyntaxTree.fromFile(inp_test_name)
dut_design_file= tree.root.members[0] #stores full file
param_flag = 0
for scope_i in (tree.root.members):
  if(scope_i.kind.name != "ClassDeclaration"):
    dut_name=str(scope_i.header.name) #Used to embed with tb generated files
    break #This is only to fetch the top name, so breaking here.
# Sanitize the DUT name for folder creation
sanitized_dut_name = sanitize_dut_name(dut_name)
# Create a folder specific to verilator
if sim_mode == 'verilator':
  verilator_path = f"{sanitized_dut_name}_verilator"
  if not os.path.exists(verilator_path):
    os.makedirs(verilator_path)
  #Create tb folder inside the verilator folder
  tb_path = os.path.join(verilator_path,"tb")
  if not os.path.exists(tb_path):
    os.makedirs(tb_path)
else:
  tb_path = folder_name
# Copy the design file to the tb folder
try:
  shutil.copy(inp_test_name, tb_path)
  logging.info(f"Successfully copied the design file to -> {tb_path}")
except Exception as e:
  logging.error(f"Error copying the design file: {e}")


for scope_i in (tree.root.members):
  if(scope_i.kind.name != "ClassDeclaration"):
    #dut_name=str(scope_i.header.name) #Used to embed with tb generated files
    #print(scope_i.header.ports)
    #for j_port in scope_i.header.ports:
    #  print(j_port)
    if (hasattr(scope_i, 'members')): #Check if the scope has the attribute called "members"
      for m_i in (scope_i.members):
        #This will print the internal name for each and every line in verilog code
        logging.debug(m_i.kind.name)
        #This will print the verilog line corresponds to kind.name
        logging.debug(m_i)
        if(m_i.kind.name== "PortDeclaration"):
          collect_port_data()
        if(m_i.kind.name== "ParameterDeclarationStatement"):
          param_flag = 1
          collect_param_data()

print(f'Printing ALL port list: \n {tabulate(port_list)}')
#print(f'Printing ALL port list: \n {tabulate(input_list)}')
#print(f'Printing ALL port list: \n {tabulate(output_list)}')
'''
Calling a function to create interface
'''
create_interface(port_list,dut_name,tb_path, sim_mode == 'verilator')
create_seqitem(port_list,dut_name,tb_path)
create_sequence(dut_name,tb_path)
create_seqr(dut_name,tb_path, sim_mode == 'verilator')
create_driver(dut_name,tb_path,llm_enabled)
create_monitor(dut_name,tb_path,llm_enabled)
create_agent(dut_name,tb_path)
create_sb(dut_name,tb_path,llm_enabled)
create_coverage(dut_name,tb_path, sim_mode == 'verilator')
create_env(dut_name,tb_path)
create_test(dut_name,tb_path)
create_top(port_list,dut_name,tb_path, sim_mode == 'verilator')
if sim_mode == 'verilator':
    create_makefile(sanitized_dut_name,verilator_path, coverage_flag, ex_cr)

# Create the UVM TB graph
create_tb_graph(dut_name, tb_path)

end_time = time.time()
total_time = end_time - start_time
print(f'\n************ Successfully created the testbench for {dut_name} in {total_time:.2f} seconds ************')
