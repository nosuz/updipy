class Device:
    @classmethod
    def select(self, device_name):
        device = Device
        if not device_name:
            return device

        device_name = device_name.upper()
        if device_name == "ATTINY202":
            device = TN202
        elif device_name == "ATTINY402":
            device = TN402

        return device

    DEVICE_NAME = "AVR base"

    STATUSA = 0x00
    CTRLB = 0x03
    ASI_KEY_STATUS = 0x07
    ASI_RESET_REQ = 0x08
    ASI_SYS_STATUS = 0x0B

    ASI_KEY_STATUS_UROWWRITE_mask = 0b00100000
    ASI_KEY_STATUS_NVMPROG_mask = 0b00010000
    ASI_KEY_STATUS_CHIPERASE_mask = 0b0001000

    ASI_SYS_STATUS_NVMPROG_mask = 0b00001000
    ASI_SYS_STATUS_UROWPROG_mask = 0b00000100
    ASI_SYS_STATUS_LOCKSTATUS_mask = 0b00000001

    RSTREQ_KEY = 0x59

    NVMCTRL_base = 0x1000
    NVMCTRL_CTRLA = NVMCTRL_base
    NVMCTRL_DATA = NVMCTRL_base + 0x06
    NVMCTRL_ADDRL = NVMCTRL_base + 0x08
    NVMCTRL_ADDRH = NVMCTRL_base + 0x09

    NVMCTRL_CTRLA_CMD_WP = 0x01
    #NVMCTRL_CTRLA_CMD_ER = 0x02
    NVMCTRL_CTRLA_CMD_ERWP = 0x03
    NVMCTRL_CTRLA_CMD_WFU = 0x07

    SIGROW_base = 0x1100
    FUSES_base = 0x1280
    USERROW_base = 0x1300

    SIG_BYTES = {
        "ATtiny202": [0x1E, 0x91, 0x23],
        "ATtiny402": [0x1E, 0x92, 0x27]
    }

    NAME_BY_SIG = {
        "".join([f"{sig:02X}" for sig in v]): k for k, v in SIG_BYTES.items()
    }


class TNx02(Device):
    FLASH_PAGE_SIZE = 64
    FLASH_START_ADDR = 0x8000

    EEPROM_START_ADDR = 0x1400
    EEPROM_PAGE_SIZE = 32

    FUSES = {
        "WDTCFG": 0x00,
        "BODCFG": 0x01,
        "OSCCFG": 0x02,
        "SYSCFG0": 0x05,
        "SYSCFG1": 0x06,
        "APPEND": 0x07,
        "BOOTEND": 0x08,
        "LOCKBIT": 0x0A
    }

    FUSE_BY_ADDR = {v: k for k, v in FUSES.items()}


class TN202(TNx02):
    DEVICE_NAME = "ATtiny202"
    FLASH_PAGE_COUNT = 32
    EEPROM_PAGE_COUNT = 2


class TN402(TNx02):
    DEVICE_NAME = "ATtiny402"
    FLASH_PAGE_COUNT = 63
    EEPROM_PAGE_COUNT = 4
