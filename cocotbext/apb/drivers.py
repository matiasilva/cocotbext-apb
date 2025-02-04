from cocotb_bus.bus import Bus
from cocotb.handle import LogicObject, SimHandleBase
from cocotb.types import Logic, LogicArray
from cocotb.triggers import RisingEdge

from enum import Enum, auto
from typing import NamedTuple
from functools import cached_property
from dataclasses import dataclass, field
import logging


class APBPhase(Enum):
    IDLE = auto()
    SETUP = auto()
    ACCESS = auto()


class APBWriteTxFrame(NamedTuple):
    paddr: LogicArray
    pwdata: LogicArray
    pstrb: LogicArray = LogicArray(0b1111, 4)
    pwrite: Logic = Logic(True)
    psel: Logic = Logic(True)
    penable: Logic = Logic(False)


class APBReadTxFrame(NamedTuple):
    paddr: LogicArray
    pwrite: Logic = Logic(False)
    psel: Logic = Logic(True)
    penable: Logic = Logic(False)
    pstrb: LogicArray = LogicArray(0b0000, 4)


class APBIdleFrame(NamedTuple):
    psel: Logic = Logic(False)
    penable: Logic = Logic(False)
    pstrb: LogicArray = LogicArray(0b0000, 4)


@dataclass
class APBTransaction:
    address: int
    data: int | None = None
    is_read: bool = field(init=False)
    error: bool = False
    read_data: int = 0

    def __post_init__(self):
        self.is_read = self.data is None

    def as_frame(self, bus: "APBBus") -> APBReadTxFrame | APBWriteTxFrame:
        """Convert the transaction into a valid read/write frame"""
        if self.is_read:
            return APBReadTxFrame(
                LogicArray.from_unsigned(self.address, len(bus.paddr))
            )
        else:
            return APBWriteTxFrame(
                LogicArray.from_unsigned(self.address, len(bus.paddr)),
                LogicArray(self.data, len(bus.pwdata)),
            )


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

    Note: we do not inherit from cocotb-bus' `BusDriver` as it does not use an async queue
    and has some legacy code from <2.0. To be reevaluated..
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

        self._bus.drive(APBIdleFrame())

    @cached_property
    def log(self) -> logging.Logger:
        """Access the logger for this driver, cached as creating a logger is expensive"""
        return logging.getLogger(f"cocotb.{self.__name__}")

    async def _driver_send(self, transaction: APBTransaction) -> APBTransaction:
        """
        Initiate a transaction on the APB bus using parameters from `frame`.

        Low-level implementation of the send method.

        Returns:
            None if the transaction was a write, else the read value if it was a
            read transaction.
        """

        self._state = APBPhase.SETUP
        setup_frame = transaction.as_frame(self._bus)

        self._bus.drive(setup_frame)
        await RisingEdge(self._clock)

        self._state = APBPhase.ACCESS
        access_frame = setup_frame._replace(penable=Logic(True))
        self._bus.drive(access_frame)
        await RisingEdge(self._clock)

        # stall for any wait states
        while not self._bus.pready.value:
            await RisingEdge(self._clock)

        # cleanup
        self.log.info(
            f"APB {'read' if transaction.is_read else 'write'} transaction OK"
        )
        self._bus.drive(APBIdleFrame())
        self._state = APBPhase.IDLE

        transaction.error = bool(self._bus.pslverr.value)
        if transaction.error:
            self.log.error(f"Transaction {transaction} got error!")
        if transaction.is_read:
            transaction.read_data = self._bus.prdata.value.to_unsigned()

        return transaction


class APBCollectorDriver:
    pass
