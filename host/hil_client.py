import time
import serial

class PicoClient:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)

    def close(self):
        self.ser.close()

    def read_line(self) -> str:
        line = self.ser.readline().decode("utf-8", errors="replace").strip()
        return line

    def cmd(self, s: str, wait: float = 0.05) -> str:
        self.ser.write((s.strip() + "\n").encode("utf-8"))
        self.ser.flush()
        time.sleep(wait)
        return self.read_line()

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", required=True, help="Example: COM5 or /dev/ttyACM0")
    args = p.parse_args()

    dut = PicoClient(args.port)

    boot = dut.read_line()
    print(f"BOOT: {boot}")

    print(dut.cmd("PING"))
    print(dut.cmd("VERSION"))
    print(dut.cmd("GET_STATE"))
    print(dut.cmd("SET_STATE 1"))
    print(dut.cmd("GET_STATE"))
    print(dut.cmd("SET_STATE 9"))

    dut.close()

if __name__ == "__main__":
    main()
