#!/usr/bin/python3

import time
import logging
import shutil
import argparse

from .updi import UPDI
from .device import Device
from .ihex import IHex


class UPDI_FUNC:
    def __init__(self, port, speed=115200, device_name=None):
        self.chip_erased = False
        self.device = Device.select(device_name)
        self.updi = UPDI(port=port, speed=speed, device=self.device)
        if device_name:
            connected_dev = self.get_device_name()
            if device_name.upper() != connected_dev.upper():
                self.reset()
                raise Exception(
                    f"Device ID Error: not {device_name} but {connected_dev}")
        else:
            device_name = self.get_device_name()

            logging.debug(f"Connected device: {device_name}")
            self.device = Device.select(device_name)
            self.updi.set_device(self.device)

    def close(self):
        self.updi.req_reset()
        self.updi.close()

    def unlock_nvm(self):
        status = self.updi.ldcs(self.device.ASI_SYS_STATUS)
        if (status[0] & self.device.ASI_SYS_STATUS_NVMPROG_mask) != 0:
            logging.debug("Not Locked")
            return True

        self.updi.set_key(UPDI.NVMPROG_KEY)
        self.updi.req_reset()
        # self.updi.ldcs(self.device.ASI_KEY_STATUS)
        count = 0
        while True:
            status = self.updi.ldcs(self.device.ASI_SYS_STATUS)
            if (status[0] & self.device.ASI_SYS_STATUS_NVMPROG_mask) != 0:
                break
            elif count > 3:
                raise Exception("Unlock Error")
            else:
                time.sleep(0.2)
                count += 1
        logging.info("Unlocked NVM")
        return True

    def get_device_name(self):
        self.unlock_nvm()

        self.updi.st(UPDI.SET_PTR, Device.SIGROW_base)
        self.updi.repeat(0x02)
        dev_id = self.updi.ld(UPDI.AT_PTR_INC)
        dev_id += self.updi.repeat_read(0x02)
        sig = "".join([f"{sig:02X}" for sig in dev_id])
        logging.info(f"Device ID: {sig}")
        dev_name = Device.NAME_BY_SIG[sig]
        logging.info(f"Device name: {dev_name}")
        return dev_name

    def reset(self):
        self.updi.req_reset()

    def chip_erase(self, force=False):
        if (not force) and self.chip_erased:
            return

        self.updi.set_key(UPDI.CHIP_ERASE_KEY)
        self.updi.req_reset()
        count = 0
        while True:
            status = self.updi.ldcs(self.device.ASI_SYS_STATUS)[0]
            if (status & self.device.ASI_SYS_STATUS_LOCKSTATUS_mask) == 0:
                logging.info("Chip erased")
                break
            elif count > 3:
                raise Exception("Chip erase Error")
            else:
                count += 1
                time.sleep(0.2)
        self.chip_erased = True

    def read_fuses(self):
        self.unlock_nvm()

        self.updi.st(UPDI.SET_PTR, self.device.FUSES_base)
        data = []
        repeat_count = max(self.device.FUSE_BY_ADDR)
        self.updi.repeat(repeat_count)
        data += self.updi.ld(UPDI.AT_PTR_INC)
        data += self.updi.repeat_read(repeat_count)
        return data

    def write_fuse(self, addr, data):
        if addr not in self.device.FUSE_BY_ADDR:
            logging.error(f"No fuse at {addr:02X}")
            raise Exception("Fuse address Error")

        self.unlock_nvm()

        ph_addr = self.device.FUSES_base + addr
        # updi.sts(device.NVMCTRL_ADDRL, addr) # writing word not write high byte
        self.updi.sts(self.device.NVMCTRL_ADDRL, ph_addr & 0xFF)
        self.updi.sts(self.device.NVMCTRL_ADDRH, ph_addr >> 8)
        self.updi.sts(self.device.NVMCTRL_DATA, data & 0xFF)
        self.updi.sts(self.device.NVMCTRL_CTRLA,
                      self.device.NVMCTRL_CTRLA_CMD_WFU)

        self.reset()

    def write_fuses(self, memory):
        self.unlock_nvm()

        max_len = max([len(k) for k in self.updi.device.FUSES.keys()])
        for addr in self.device.FUSE_BY_ADDR:
            if addr not in self.device.FUSE_BY_ADDR:
                continue
            data = memory[addr]
            if data is None:
                continue
            fuse_name = self.updi.device.FUSE_BY_ADDR[addr]
            print(
                f"{fuse_name:<{max_len}}({addr:02X}): {data >> 4:04b} {data & 0x0F:04b} ({data:02X})")
            ph_addr = self.device.FUSES_base + addr
            # updi.sts(device.NVMCTRL_ADDRL, addr) # writing word not write high byte
            self.updi.sts(self.device.NVMCTRL_ADDRL, ph_addr & 0xFF)
            self.updi.sts(self.device.NVMCTRL_ADDRH, ph_addr >> 8)
            self.updi.sts(self.device.NVMCTRL_DATA, data & 0xFF)
            self.updi.sts(self.device.NVMCTRL_CTRLA,
                          self.device.NVMCTRL_CTRLA_CMD_WFU)

        self.reset()

    def read_eeprom(self, addr=0x0000, size=None):
        return self.read_nvm(
            self.device.EEPROM_PAGE_SIZE,
            self.device.EEPROM_PAGE_COUNT,
            self.device.EEPROM_START_ADDR,
            addr, size)

    def write_eeprom(self, memory):
        self.write_nvm(
            self.device.EEPROM_PAGE_SIZE,
            self.device.EEPROM_PAGE_COUNT,
            self.device.EEPROM_START_ADDR,
            memory)

    def read_flash(self, addr=0x0000, size=None):
        return self.read_nvm(
            self.device.FLASH_PAGE_SIZE,
            self.device.FLASH_PAGE_COUNT,
            self.device.FLASH_START_ADDR,
            addr, size)

    def write_flash(self, memory):
        self.write_nvm(
            self.device.FLASH_PAGE_SIZE,
            self.device.FLASH_PAGE_COUNT,
            self.device.FLASH_START_ADDR,
            memory)

    def read_nvm(self, page_size, page_count, page_start, addr=0x0000, size=None):
        self.unlock_nvm()

        nvm_size = page_size * page_count
        if not size:
            size = nvm_size - addr
        if not(0 < size <= nvm_size):
            raise Exception(f"Read size Error: {size}")

        last_addr = addr + size - 1
        if last_addr >= nvm_size:
            raise Exception(f"Over segment Error: {last_addr}")

        ph_addr = addr + page_start
        logging.info(f"Read from {addr:04X} ({ph_addr:04X})")
        self.updi.st(UPDI.SET_PTR, ph_addr)

        pages = int(size / page_size)
        remain_size = size % page_size
        logging.info(
            f"Read size: {size:04X} bytes ({pages:2X} pages + {remain_size:2X} bytes)")

        memory = []
        repeat_size = page_size - 1
        logging.debug(f"repeat cout: {repeat_size}")
        for page in range(pages):
            self.updi.repeat(repeat_size)
            memory += self.updi.ld(UPDI.AT_PTR_INC)
            memory += self.updi.repeat_read(repeat_size)
        if remain_size > 0:
            repeat_size = remain_size - 1
            logging.debug(f"repeat cout: {repeat_size}")
            self.updi.repeat(repeat_size)
            memory += self.updi.ld(UPDI.AT_PTR_INC)
            memory += self.updi.repeat_read(repeat_size)

        return memory

    def write_nvm(self, page_size, page_count, page_start, memory):
        self.chip_erase()

        self.unlock_nvm()

        col_size = shutil.get_terminal_size().columns
        col_size = col_size - col_size % page_count - 10
        for page in range(page_count):
            prog_addr = page * page_size
            ph_addr = page_start + prog_addr
            raw_data = memory[prog_addr:prog_addr +
                              page_size]
            if raw_data.count(None) == page_size:
                # break
                continue
            else:
                progress = (page + 1) / page_count
                print(f"{int(progress * 100):>3}%", "[" + "#" * int(col_size * progress) + "." * (
                    col_size - int(col_size * progress)) + "]", end="\r")
                data = [0xFF if d is None else d for d in raw_data]
            logging.info(f"Write address: {prog_addr:04X}, {ph_addr:04X}")
            logging.debug(", ".join([f"{d:02X}" for d in data]))
            self.updi.st(UPDI.SET_PTR, ph_addr)
            self.updi.repeat(page_size - 1)
            self.updi.st(UPDI.AT_PTR_INC, data[0])
            self.updi.repeat_write(data[1:])

            self.updi.sts(self.device.NVMCTRL_ADDRL, ph_addr & 0xFF)
            self.updi.sts(self.device.NVMCTRL_ADDRH, ph_addr >> 8)
            #self.updi.sts(self.device.NVMCTRL_CTRLA, self.device.NVMCTRL_CTRLA_CMD_ERWP)
            self.updi.sts(self.device.NVMCTRL_CTRLA,
                          self.device.NVMCTRL_CTRLA_CMD_WP)

        print("100%", "[" + "#" * col_size + "]")
        self.reset()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--line", help="port path", required=True)
    parser.add_argument("-d", "--device", help="Device name")
    parser.add_argument("-rf", "--read-fuse",
                        help="read fuse", action='store_true')
    parser.add_argument(
        "-wf", "--write-fuse", help="write fuse ADDR:VAL ...", action="extend", nargs="+", type=str)
    parser.add_argument("-ce", "--chip-erase",
                        help="Chip erase", action='store_true')
    parser.add_argument("-i", "--hex", help="hex file")
    parser.add_argument("-v", "--verify",
                        help="Verify FLASH and EEPROM memory", action='store_true')
    parser.add_argument("-de", "--dump-eeprom", help="Dump EEPROM memory",
                        nargs='?', type=int, const=-1, default=0)
    parser.add_argument("-df", "--dump-flash", help="Dump FLASH memory",
                        nargs='?', type=int, const=-1, default=0)
    parser.add_argument("--debug", help="Set debug mode", action='store_true')

    args = parser.parse_args()

    if args.debug:
        logging.root.setLevel(logging.NOTSET)
    else:
        logging.root.setLevel(logging.WARNING)

    updi = UPDI_FUNC(args.line, device_name=args.device)

    if args.hex:
        hex = IHex()
        hex.read_file(args.hex)

        if hex.has_addr(0x0):
            print("Programing Flash memory ...")
            bin = hex.get_memory(0x0)
            updi.write_flash(bin)
            if args.verify:
                read_size = 0x10000 - bin.count(None)
                read = updi.read_flash(size=read_size)
                if bin[:read_size] == read:
                    print("Flash memory OK.")
                else:
                    logging.error("Writing Flash memory Error")
                    raise Exception("Writing Flash memory Error")

        if hex.has_addr(0x81):
            print("Writing EEPROM memory ...")
            bin = hex.get_memory(0x81)
            updi.write_eeprom(bin)
            if args.verify:
                read_size = 0x10000 - bin.count(None)
                read = updi.read_eeprom(size=read_size)
                if bin[:read_size] == read:
                    print("EEPROM memory OK.")
                else:
                    print(bin[:read_size])
                    print(read)
                    logging.error("Writing EEPROM memory Error")
                    raise Exception("Writing EEPROM memory Error")

        if hex.has_addr(0x82):
            bin = hex.get_memory(0x82)
            updi.write_fuses(bin)

    if args.write_fuse:
        for fuse in args.write_fuse:
            kv = fuse.split(':')
            if len(kv) == 2:
                addr = int(kv[0], 16)
                val = int(kv[1], 16)
                updi.write_fuse(addr, val)
            else:
                logging.error(f"Format Error: {kv}")

    if args.read_fuse:
        max_len = max([len(k) for k in updi.device.FUSES.keys()])
        for addr, fuse in enumerate(updi.read_fuses()):
            if addr not in updi.device.FUSE_BY_ADDR:
                continue
            fuse_name = updi.device.FUSE_BY_ADDR[addr]
            print(
                f"{fuse_name:<{max_len}}({addr:02X}): {fuse >> 4:04b} {fuse & 0x0F:04b} ({fuse:02X})")

    if args.dump_eeprom:
        if 0 < args.dump_eeprom <= updi.device.EEPROM_PAGE_COUNT:
            page_count = args.dump_eeprom
        else:
            page_count = updi.device.EEPROM_PAGE_COUNT
        read_size = page_count * updi.device.EEPROM_PAGE_SIZE
        print(f"Reading {read_size} bytes of EEPROM memory")
        memory = updi.read_eeprom(size=read_size)
        for page in range(page_count):
            print(" " * 5, " ".join([f"{x:2X}" for x in range(16)]))
            for p in range(0, updi.device.EEPROM_PAGE_SIZE, 0x10):
                block_start = page * updi.device.EEPROM_PAGE_SIZE + p
                block = memory[block_start:block_start + 0x10]
                print(f"{block_start:04X}:", " ".join(
                    [f"{x:02X}" for x in block]))

    if args.dump_flash:
        if 0 < args.dump_flash <= updi.device.FLASH_PAGE_COUNT:
            page_count = args.dump_flash
        else:
            page_count = updi.device.FLASH_PAGE_COUNT
        read_size = page_count * updi.device.FLASH_PAGE_SIZE
        print(f"Reading {read_size} bytes of FLASH memory")
        memory = updi.read_flash(size=read_size)
        for page in range(page_count):
            print(" " * 5, " ".join([f"{x:2X}" for x in range(16)]))
            for p in range(0, updi.device.FLASH_PAGE_SIZE, 0x10):
                block_start = page * updi.device.FLASH_PAGE_SIZE + p
                block = memory[block_start:block_start + 0x10]
                print(f"{block_start:04X}:", " ".join(
                    [f"{x:02X}" for x in block]))

    if args.chip_erase:
        updi.chip_erase(force=True)

    updi.close()


if __name__ == '__main__':
    main()
