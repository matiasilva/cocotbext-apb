from cocotb_bus.bus import Bus
from cocotb.handle import LogicObject, SimHandleBase
from cocotb.types import Logic, LogicArray
from cocotb.triggers import RisingEdge

from enum import Enum, auto
from typing import NamedTuple
from functools import cached_property
import logging


class APBPhase(Enum):
    IDLE = auto()
    SETUP = auto()
    ACCESS = auto()


class APBWriteTxFrame(NamedTuple):
    paddr: LogicArray
    pwrite: Logic
    psel: Logic
    penable: Logic
    pwdata: LogicArray


class APBWriteRxFrame(NamedTuple):
    pready: Logic


class APBReadTxFrame(NamedTuple):
    paddr: LogicArray
    pwrite: Logic
    psel: Logic
    penable: Logic
    prdata: LogicArray


class APBReadRxFrame(NamedTuple):
    paddr: LogicArray
    pwrite: Logic
    psel: Logic
    penable: Logic
    prdata: LogicArray


class APBTransaction(NamedTuple):
    address: int
    data: int | None = None


class APBBus(Bus):
    _signals = [
        "paddr",
        "pprot",
        "psel",
        "penable",
        "pwrite",
        "pready",
        "pwdata",
        "prdata",
    ]

    _optional_signals = ["pstrb", "pslverr", "pwakeup"]

    def __init__(
        self,
        entity: SimHandleBase,
        name: str,
        **kwargs,
    ):
        super().__init__(entity, name, self._signals, self._optional_signals, **kwargs)


class APBRequesterDriver:
    """
    Class for an APB requester, formerly known as a master.

    Note: we do not inherit from cocotb-bus' `BusDriver` as it does not use an async queue.
    """

    def __init__(self, entity: SimHandleBase, name: str, clock: LogicObject, **kwargs):
        """
        Create an APB requester.

        Optionally pass in an `APBBus` object as a key-word argument or one will be
        created using the `name` parameter.
        """
        bus = kwargs.get("bus")
        self._bus: APBBus = bus if bus is not None else APBBus(entity, name, **kwargs)

        self._state = APBPhase.IDLE
        self._clock = clock
        self._address_bus_size = len(self._bus.paddr)  # type: ignore[reportAttributeAccessIssue]
        self._data_bus_size = len(self._bus.pwdata)  # type: ignore[reportAttributeAccessIssue]

        self.__name__ = f"{entity._name}.{type(self).__qualname__} {name}"

        # TODO: set initial values for signals

    @cached_property
    def log(self) -> logging.Logger:
        """Access the logger for this driver, cached as creating a logger is expensive"""
        return logging.getLogger(f"cocotb.{self.__name__}")

    async def _driver_send(self, transaction: APBTransaction):
        """
        Initiate a transaction on the APB bus using parameters from `frame`.

        Low-level implementation of the send method.
        """
        LogicArray.from_unsigned(0xA, 4)

        self._state = APBPhase.SETUP
        if transaction.data is not None:
            setup_frame = APBWriteTxFrame(
                LogicArray.from_unsigned(transaction.address, self._address_bus_size),
                Logic(True),
                Logic(True),
                Logic(False),
                LogicArray(transaction.data, self._data_bus_size),
            )
            self._bus.drive(setup_frame)
            await RisingEdge(self._clock)
            self._state = APBPhase.ACCESS
            access_frame = setup_frame._replace(penable=Logic(True))
            self._bus.drive(access_frame)
            while not self._bus.pready.value:
                await RisingEdge(self._clock)
            self.log.info("APB write transaction OK")


class APBCollectorDriver:
    pass
