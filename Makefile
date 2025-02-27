run:
	python3 rtl2uvm.py -t sample_dut.sv -m edaplayground
	python3 rtl2uvm.py -t sample_dut.sv -m edaplayground -llm
	python3 rtl2uvm.py -t sample_dut.sv -m verilator -c 
