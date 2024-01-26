import sys
import time
import threading
import signal


class Cursor:
    @staticmethod
    def show(signal_received=None, frame=None):
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        if signal_received:
            sys.exit(0)

    @staticmethod
    def hide():
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()


signal.signal(signal.SIGINT, Cursor.show)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, Cursor.show)  # Handle termination


class Loader:
    def __init__(
        self,
        symbols=["⣾", "⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽"],
        delay=0.1,
    ):
        self.symbols = symbols
        self.delay = delay
        self.running = False
        self.thread = threading.Thread(target=self.run)

    def start(self):
        self.running = True
        Cursor.hide()
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()
        sys.stdout.flush()
        Cursor.show()

    def run(self):
        while self.running:
            for symbol in self.symbols:
                sys.stdout.write(symbol)
                sys.stdout.flush()
                time.sleep(self.delay)
                sys.stdout.write("\b")
                sys.stdout.flush()
