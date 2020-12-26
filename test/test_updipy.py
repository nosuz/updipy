import os
import unittest
import sys
import os.path as path


class UpdipyTest(unittest.TestCase):
    DEVICE_NAME = "ATtiny202"

    def setUp(self) -> None:
        self.updi = UPDI_FUNC("/dev/ttyUSB1")

    def tearDown(self) -> None:
        self.updi.close()

    def test_erase_key(self):
        self.assertEqual("NVMErase", "".join(
            [chr(c) for c in UPDI.CHIP_ERASE_KEY]))

    def test_nvm_key(self):
        self.assertEqual("NVMProg ", "".join(
            [chr(c) for c in UPDI.NVMPROG_KEY]))

    def test_userrow_key(self):
        self.assertEqual("NVMUs&te", "".join(
            [chr(c) for c in UPDI.USERROW_WRITE_KEY]))

    def test_unlock_nvm(self):
        self.assertEqual(True, self.updi.unlock_nvm())

    def test_read_all_nvm(self):
        memory = self.updi.read_flash()
        self.assertEqual(self.updi.device.FLASH_PAGE_SIZE *
                         self.updi.device.FLASH_PAGE_COUNT, len(memory))

    def test_read_last_nvm(self):
        nvm_size = self.updi.device.FLASH_PAGE_SIZE * self.updi.device.FLASH_PAGE_COUNT
        memory = self.updi.read_flash(addr=(nvm_size - 1))
        self.assertEqual(1, len(memory))

    def test_read_nvm_size(self):
        memory = self.updi.read_flash(
            size=self.updi.device.FLASH_PAGE_SIZE + 1)
        self.assertEqual(self.updi.device.FLASH_PAGE_SIZE + 1, len(memory))

    def test_read_over_nvm(self):
        nvm_size = self.updi.device.FLASH_PAGE_SIZE * self.updi.device.FLASH_PAGE_COUNT
        with self.assertRaisesRegex(Exception, r"^Over NVM size Error$"):
            self.updi.read_flash(addr=nvm_size - 1, size=2)

    def test_device_name(self):
        self.assertEqual(UpdipyTest.DEVICE_NAME, self.updi.get_device_name())


if __name__ == '__main__':
    sys.path.append(path.dirname(__file__) + "/..")
    from updipy.updipy import UPDI_FUNC
    from updipy.updi import UPDI

    if "DEVICE_NAME" in os.environ:
        UpdipyTest.DEVICE_NAME = os.environ.get("DEVICE_NAME")
    elif len(sys.argv) > 1:
        UpdipyTest.DEVICE_NAME = sys.argv.pop()

    unittest.main()
