import threading
import time
import logging
import ctypes
import win32con
import win32gui
import win32ts
from argparse import ArgumentParser


LOGGER = logging.getLogger('DigtoxiPy')
WM_WTS_SESSION_CHANGE = 0x2B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8


class WindowsTerminalSessionMonitor:
    def __init__(self, class_name='WtsMonitor', window_name='WtsMonitor', on_lock=None, on_unlock=None):
        self.class_name = class_name
        self.window_name = window_name
        self.window = None
        if on_lock is not None:
            self._on_lock = on_lock
        if on_unlock is not None:
            self._on_unlock = on_unlock

    def start(self):  # This is a blocking method and must be called in a separate thread
        window_class = win32gui.WNDCLASS()
        window_class.hInstance = win32gui.GetModuleHandle(None)
        window_class.lpszClassName = self.class_name
        window_class.lpfnWndProc = self.message_handler
        self.window = win32gui.CreateWindow(
            win32gui.RegisterClass(window_class), self.window_name, 0, 0, 0, win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT, 0, 0, window_class.hInstance, None
        )
        win32gui.UpdateWindow(self.window)
        win32ts.WTSRegisterSessionNotification(self.window, win32ts.NOTIFY_FOR_THIS_SESSION)
        win32gui.PumpMessages()

    def stop(self):
        win32gui.PostMessage(self.window, win32con.WM_QUIT, 0, 0)
        win32gui.PostQuitMessage(0)
        win32ts.WTSUnRegisterSessionNotification(self.window)

    def message_handler(self, h_window, message, w_param, l_param):
        if message == WM_WTS_SESSION_CHANGE:
            if w_param == WTS_SESSION_LOCK:
                self._on_lock()
            elif w_param == WTS_SESSION_UNLOCK:
                self._on_unlock()

    def _on_lock(self):
        LOGGER.debug('Locked')

    def _on_unlock(self):
        LOGGER.debug('Unlocked')


def auto_lock():
    ctypes.windll.user32.LockWorkStation()


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-s", "--seconds", dest="seconds", action="store", type=int, default=0,
                            help="Detox duration in seconds. Can be used with minutes and hours")
    arg_parser.add_argument("-m", "--minutes", dest="minutes", action="store", type=int, default=0,
                            help="Detox duration in minutes. Can be used with seconds and hours")
    arg_parser.add_argument("-o", "--hours", dest="hours", action="store", type=int, default=0,
                            help="Detox duration in hours. Can be used with seconds and minutes")
    arg_parser.add_argument("-l", "--log-level", dest="log_level", action="store", type=str, default='NOTSET',
                            help="Detox duration in hours. Can be used with seconds and minutes")
    args = arg_parser.parse_args()
    log_level = logging.getLevelName(args.log_level.upper())
    if log_level == f'Level {args.log_level.upper()}':
        arg_parser.error(f'Invalid log {log_level}')
    logging.basicConfig(level=log_level)
    duration = args.hours * 3600 + args.minutes * 60 + args.seconds
    if duration:
        wts_monitor = WindowsTerminalSessionMonitor('Detox', 'SessionLocker', on_unlock=auto_lock)
        detox_thread = threading.Thread(target=wts_monitor.start)
        detox_thread.start()
        auto_lock()
        time.sleep(duration)
        wts_monitor.stop()
