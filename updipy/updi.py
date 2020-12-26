import serial
import logging
import time
import sys

from .device import Device


class LinkTimeoutError(Exception):
    pass


class UPDI:
    BREAK = 0x00
    SYNC = 0x55

    LDS = 0b00000000
    STS = 0b01000000
    ADDR_SIZE_1 = 0b0  # 1 byte
    ADDR_SIZE_2 = 0b1  # 2 bytes
    DATA_SIZE_1 = 0b0  # 1 byte
    DATA_SIZE_2 = 0b1  # 2 bytes

    LD = 0b00100000
    ST = 0b01100000
    AT_PTR = 0b00
    AT_PTR_INC = 0b01
    SET_PTR = 0b10

    LDCS = 0b10000000
    STCS = 0b11000000

    REPEAT = 0b10100000
    REPEAT_SIZE_1 = 0b0  # 1 byte
    REPEAT_SIZE_2 = 0b1  # word or 2 bytes

    KEY_SET = 0b11100000  # we __Send__ KEY
    KEY_GET = 0b11100100  # we __Receive__ KEY
    KEY_SIZE_8 = 0b00  # 8 bytes
    KEY_SIZE_16 = 0b01  # 16 bytes

    INIT_SEQ = [BREAK, SYNC, 0xC3, 0x08]  # important set CTRLB.CCDETDIS=1

    CHIP_ERASE_KEY = [0x4E, 0x56, 0x4D, 0x45, 0x72, 0x61, 0x73, 0x65]
    NVMPROG_KEY = [0x4E, 0x56, 0x4D, 0x50, 0x72, 0x6F, 0x67, 0x20]
    USERROW_WRITE_KEY = [0x4E, 0x56, 0x4D, 0x55, 0x73, 0x26, 0x74, 0x65]

    def __init__(self, port, speed=115200, device=Device):
        self.link = None
        self.port = port
        self.speed = speed
        self.device = device
        self.open()

    def set_device(self, device):
        self.device = device

    def open_link(self):
        logging.info("Open " + self.port)
        if self.link:
            self.link.close()

        try:
            self.link = serial.Serial(port=self.port, baudrate=self.speed,
                                      bytesize=serial.EIGHTBITS,
                                      parity=serial.PARITY_EVEN,
                                      stopbits=serial.STOPBITS_TWO,
                                      timeout=0.2
                                      )
        except AttributeError as e:
            print("Error: You might installed a wrong package named serial.")
            print(
                "Uninstall both pyserial and serial packages, then install pyserial again.")
            logging.error(
                "AttributeError: May be installed package named serial.")
            sys.exit()

    def close_link(self):
        if self.link:
            self.link.close()

    def write_link(self, data, sync=True):
        if sync:
            data = [UPDI.SYNC] + data
        self.link.write(data)
        _echo = self.link.read(len(data))
        logging.debug("TxD:" + ", ".join(["{:02X}".format(c) for c in _echo]))

    def read_link(self, size):
        _read = self.link.read(size)
        if not _read:
            logging.error("Link read Timeout")
            raise LinkTimeoutError("Timeout")
        logging.debug("RxD:" + ", ".join(["{:02X}".format(c) for c in _read]))
        return _read

    def line_break(self):
        self.close_link()

        comm = serial.Serial(port=self.port, baudrate=300,
                             bytesize=serial.EIGHTBITS,
                             parity=serial.PARITY_EVEN,
                             stopbits=serial.STOPBITS_TWO)
        logging.debug("Send double break")
        comm.write([UPDI.BREAK, UPDI.BREAK])
        comm.read(2)
        comm.close()

        self.open_link()

    def open(self):
        self.open_link()
        self.write_link(UPDI.INIT_SEQ, sync=False)
        cmd = [UPDI.LDCS | self.device.STATUSA]  # read STATUSA any reg. OK
        self.write_link(cmd)
        try:
            self.read_link(1)
        except LinkTimeoutError:
            self.line_break()

            self.write_link(cmd)
            self.read_link(1)

    def close(self):
        data = [0xC3, 0x04]  # set CTRLB.UPDIDIS=1
        self.write_link(data)
        self.close_link()

    def req_reset(self):
        self.stcs(self.device.ASI_RESET_REQ, self.device.RSTREQ_KEY)
        self.stcs(self.device.ASI_RESET_REQ, 0x00)

    def get_key(self, long=False):
        if long:
            cmd = UPDI.KEY_GET | UPDI.KEY_SIZE_16
            self.write_link([cmd])
            key = self.read_link(16)
        else:
            cmd = UPDI.KEY_GET | UPDI.KEY_SIZE_8
            self.write_link([cmd])
            key = self.read_link(8)
        return key

    def set_key(self, key):
        cmd = [UPDI.KEY_SET | UPDI.KEY_SIZE_8] + [c for c in reversed(key)]
        self.write_link(cmd)

    # UPDI instructions
    def ldcs(self, addr):
        cmd = [UPDI.LDCS | addr]
        self.write_link(cmd)
        return self.read_link(1)

    def stcs(self, addr, data):
        cmd = [UPDI.STCS | addr, data]
        self.write_link(cmd)

    def lds(self, addr, data_size=DATA_SIZE_1):
        if addr > 0xFF:
            addr_size = UPDI.ADDR_SIZE_2
            cmd = [UPDI.LDS | (addr_size << 2) | data_size,
                   addr & 0xFF, addr >> 8]
        else:
            addr_size = UPDI.ADDR_SIZE_1
            cmd = [UPDI.LDS | (addr_size << 2) | data_size, addr]
        self.write_link(cmd)
        return self.read_link(data_size + 1)

    def sts(self, addr, data):
        if data > 0xFF:
            data_size = UPDI.DATA_SIZE_2
            data_array = [data & 0xFF, data >> 8]
        else:
            data_size = UPDI.DATA_SIZE_1
            data_array = [data]

        if addr > 0xFF:
            addr_size = UPDI.ADDR_SIZE_2
            cmd = [UPDI.STS | (addr_size << 2) | data_size,
                   addr & 0xFF, addr >> 8]
        else:
            addr_size = UPDI.ADDR_SIZE_1
            cmd = [UPDI.STS | (addr_size << 2) | data_size, addr]
        self.write_link(cmd)
        self.read_link(1)

        self.write_link(data_array, sync=False)
        self.read_link(1)

    def ld(self, pt_access, data_size=DATA_SIZE_1):
        cmd = [UPDI.LD | (pt_access << 2) | data_size]
        self.write_link(cmd)
        return self.read_link(data_size + 1)

    def st(self, pt_access, data):
        if data > 0xFF:
            data_size = UPDI.DATA_SIZE_2
            cmd = [UPDI.ST | (pt_access << 2) | data_size,
                   data & 0xFF, data >> 8]
        else:
            data_size = UPDI.DATA_SIZE_1
            cmd = [UPDI.ST | (pt_access << 2) | data_size, data]
        self.write_link(cmd)
        self.read_link(1)

    def repeat(self, data_size):
        cmd = [UPDI.REPEAT | UPDI.DATA_SIZE_1, data_size & 0xFF]
        self.write_link(cmd)

    def repeat_write(self, data):
        for d in data:
            self.write_link([d & 0xFF], sync=False)
            self.read_link(1)

    def repeat_read(self, data_size):
        return self.read_link(data_size)
