# cocotb APB VIP

This repo houses an APB driver extension for cocotb. It has first-class support for cocotb 2.0 features. For a pre 2.0 VIP, see https://github.com/SystematIC-Design/cocotbext-apb.

Provided components:

* APB requester driver

Planned components:

* APB collector driver
* APB bus monitor

## Getting started

An APB requester driver requires a working clock and a `dut` with [mandatory APB signals](https://github.com/matiasilva/cocotbext-apb/blob/master/cocotbext/apb/drivers.py#L67). Optional signals are allowed but are not driven. The naming scheme used is the same as that of the [standard cocotb-bus component](https://github.com/cocotb/cocotb-bus/blob/master/src/cocotb_bus/bus.py#L18).

```python
from cocotb.ext.apb import APBRequesterDriver

clk = Clock(dut.pclk, 1, units="ns")
cocotb.start_soon(clk.start(start_high=False))
driver = APBRequesterDriver(dut, "apbs", dut.pclk)
```

The above code initializes an APB requester using signals prefixed with `apbs`. To read and write data:

```python

async def setup_dut(dut):
  await apb.write(CTRL_OFFSET, 0b101)
  rx = await apb.read(STATUS_OFFSET)
  print(rx.read_data)
```

All APB read/write operations return an instance of `APBTransaction`, which you can use to check for any slave errors or in the case of a read, the read data.

The width of the data bus is automatically detected but can be adjusted manually (do at your own peril). 

## Development

This repo follows the [standard cocotb extension structure](https://docs.cocotb.org/en/latest/extensions.html) and thus should be easy to start hacking on.

Tests can be run with `uv run pytest`, or simply `pytest` if you have sourced an appropriate virtual environment.

> [!IMPORTANT]  
> You must have a SystemVerilog simulator installed to run the tests. As the APB VIP is small, Icarus is sufficient.

## License

MIT

## Author

Matias Wang Silva, 2025
