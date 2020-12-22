import re


class IHex:
    ihex_pat = re.compile(
        r"^:(?P<size>[0-9a-fA-F]{2})(?P<addr>[0-9a-fA-F]{4})(?P<type>[0-9a-fA-F]{2})(?P<data>(?:[0-9a-fA-F]{2})*)(?P<checksum>[0-9a-fA-F]{2})$")

    def __init__(self):
        self.pointer = 0x00
        self.memory = {
            0x00: [None for _ in range(0x10000)]
        }

    def read(self, lines):
        for line in [line.strip() for line in lines]:
            # print(line)
            if len(line) == 0:
                continue
            if m := IHex.ihex_pat.search(line):
                if int(m.group("size"), 16) != (len(m.group("data")) / 2):
                    print(line)
                    raise Exception("Data size error")
                checksum = sum([int(line[i:(i+2)], 16)
                                for i in range(1, len(line), 2)]) & 0xFF
                if checksum != 0:
                    #print(line, hex(checksum))
                    raise Exception("Checksum Error")

                if m.group("type") == "00":
                    addr = int(m.group("addr"), 16)
                    data = m.group("data")
                    for p, d in enumerate([int(data[i:(i+2)], 16) for i in range(0, len(data), 2)]):
                        self.memory[self.pointer][addr + p] = d
                elif m.group("type") == "01":
                    break
                elif m.group("type") == "04":
                    self.pointer = int(m.group("data")[:4], 16)
                    if self.pointer not in self.memory:
                        self.memory[self.pointer] = [
                            None for _ in range(0x10000)]
                else:
                    raise Exception("Unknow Hex type")
            else:
                print(line)
                raise Exception("IHex format Error")

    def read_file(self, file):
        with open(file) as f:
            lines = f.readlines()
            self.read(lines)

    def get_memory(self, ext_addr=0x00):
        if ext_addr in self.memory:
            return self.memory[ext_addr]
        else:
            return [None for _ in range(0x10000)]

    def has_addr(self, ext_addr):
        return ext_addr in self.memory


if __name__ == '__main__':
    ihex = IHex()
    # ihex.read_file("./test.hex")
    ihex.read([':0B0010006164647265737320676170A7\n', ':02000004FFFFFC\n',
               ':050000000001020304F1\n', ':00000001FF\n', '\n'])
    print(ihex.get_memory(0x0)[0x10:0x20])
