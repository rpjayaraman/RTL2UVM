module adder(clk, reset,in1, in2,out);
input clk;
input reset; 
input [7:0] in1;
input [7:0] in2; 
output reg [8:0] out;
  always@(posedge clk or posedge reset) begin 
    if(reset) out <= 0;
    else out <= in1 + in2;
  end
endmodule
//Form https://vlsiverify.com/uvm/uvm-adder-example/
