from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, ReadOnly
from cocotb_tools.runner import Icarus


from cocotbext.apb import APBRequesterDriver, APBTransaction


@cocotb.test
async def smoke_test(dut):
    clk = Clock(dut.pclk, 1, units="ns")
    cocotb.start_soon(clk.start(start_high=False))
    driver = APBRequesterDriver(dut, "", dut.pclk)

    dut.reset_n.value = 0
    await Timer(3, units="ns")
    dut.reset_n.value = 1
    dut._log.debug("reset complete")

    dut.enable.value = 1
    tx = APBTransaction(0x10, 0x8)
    await driver._driver_send(tx)

    tx = APBTransaction(0x10)
    await driver._driver_send(tx)
    assert tx.read_data == 0x8


def test_requester_runner():
    proj_path = Path(__file__).resolve().parent

    sources = [proj_path / "hdl" / "apb_regs.v"]

    runner = Icarus()
    runner.build(
        sources=sources,
        hdl_toplevel="apb_regs",
        waves=True,
        clean=True,
        timescale=("1ns", "100ps"),
    )

    runner.test(hdl_toplevel="apb_regs", test_module="test_requester,", waves=True)
