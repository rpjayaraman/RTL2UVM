# RTL2UVM
Automated UVM testbench generator from Verilog RTL with optional LLM integration for advanced logic creation.

## Youtube Link: https://www.youtube.com/@Random_dv_guy

## Overview

`RTL2UVM` is a Python-based tool that automates the creation of SystemVerilog UVM (Universal Verification Methodology) testbenches directly from your Verilog RTL (Register Transfer Level) design.  It parses your Verilog code using `pyslang`, extracts port information, and generates a complete UVM testbench framework, significantly reducing the manual effort involved in verification setup.

![Gist of RTL2UVMM](https://raw.githubusercontent.com/rpjayaraman/RTL2UVM/refs/heads/main/Screenshot/rtl2uvm.png)

**Key Features:**

*   **Automated UVM Generation:**  Generates a complete UVM testbench structure, including:
    *   Interface
    *   Sequence Item
    *   Sequencer
    *   Driver
    *   Monitor
    *   Agent
    *   Scoreboard
    *   Coverage Subscriber
    *   Environment
    *   Test
    *   Top-level module
*   **LLM Integration (Optional):**  Leverages Large Language Models (LLMs) like Gemini (via the `google.generativeai` library) to generate intelligent driver/monitor/scoreboard logic, based on your DUT design.  *Note: Requires a valid LLM API key.*
*   **Verilator Support:** Generates a Makefile for Verilator simulation, with optional coverage analysis.
*   **Configurable:**  Easily customizable through command-line arguments for test selection, simulation mode (Verilator/EDA Playground), and coverage options.
*   **Testbench Visualization:** Creates a visual representation of the generated UVM testbench structure using `pygraphviz` (if installed).
![Visualization output](https://raw.githubusercontent.com/rpjayaraman/RTL2UVM/refs/heads/main/Screenshot/FIFO_memory_tb_graph.png)

## Requirements

*   Python 3.6+
*   `pyslang`
*   `argparse`
*   `re`
*   `logging`
*   `tabulate`
*   `os`
*   `shutil`
*   `time`
*   `google.generativeai` (optional, for LLM integration)
*   `pygraphviz` (optional, for graph visualization)

**Installation:**

```bash
pip install pyslang argparse tabulate pygraphviz google-generativeai
```

## Usage

```bash
python rtl2uvm.py -t <your_verilog_file.v> -m <verilator|edaplayground> -c -llm
```

* -t / --test: (Required) Path to your Verilog RTL design file.
* -m / --mode: Simulation mode: verilator or edaplayground (default: edaplayground).
* -c / --coverage: Enable coverage analysis in Verilator mode.
* -llm / --llm: Enable LLM-assisted logic generation (requires Gemini API key).

## Generated Files:

The tool creates a tb folder (or a <design_name>_verilator/tb folder in Verilator mode) containing the following SystemVerilog files:

* <design_name>_interface.sv
* <design_name>_seq_item.sv
* <design_name>_base_sequence.sv
* <design_name>_sequencer.sv
* <design_name>_driver.sv
* <design_name>_monitor.sv
* <design_name>_agent.sv
* <design_name>_scoreboard.sv
* <design_name>_coverage.sv
* <design_name>_env.sv
* <design_name>_test.sv
* <design_name>_top.sv
* Makefile (Verilator mode only)
* <design_name>_tb_graph.png (Testbench Visual)


