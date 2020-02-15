import threading
import socket
from gi.repository import GLib

TRANSFER_SEND_DATA = "data"
TRANSFER_SEND_ABORT = "aborted"

TRANSFER_RECEIVE_STATUS_OK = "ok"
TRANSFER_RECEIVE_STATUS_ERROR = "error"

TRANSFER_REQUEST_PENDING = "pending"
TRANSFER_REQUEST_GRANTED = "granted"
TRANSFER_REQUEST_DECLINED = "declined"
TRANSFER_REQUEST_EXISTING = "existing"

# Used as a decorator to run things in the background
def _async(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

# Used as a decorator to run things in the main loop, from another thread
def _idle(func):
    def wrapper(*args, **kwargs):
        GLib.idle_add(func, *args, **kwargs)
    return wrapper

def getmyip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        ans = s.getsockname()[0]
        return ans

class ProgressCallbackInfo():
    def __init__(self, progress=0, speed="", time_left="", finished=False,
                 sender_awaiting_approval=False, count=0, transfer_starting=False, transfer_cancelled=False):
        self.progress = progress
        self.speed = speed
        self.time_left = time_left
        self.finished = finished
        self.sender_awaiting_approval = sender_awaiting_approval
        self.count = count
        self.transfer_starting = transfer_starting
        self.transfer_cancelled = transfer_cancelled

