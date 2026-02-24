module sample_dut (clk,
    reset,
    din,
    read,
    write,
    dout,
    empty,
    full,
    ale,
    alf
   ); 


parameter DATA_WIDTH=8;
parameter ADDR_WIDTH=4;

input clk; 
input reset; 
input [DATA_WIDTH-1:0]din;    
input read; 
input write; 


output [DATA_WIDTH-1:0]dout; 
output empty;      
output full; 
output ale; 
output alf; 


endmodule 
