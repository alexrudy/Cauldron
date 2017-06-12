import threading
import atexit

event = threading.Event()
def target(event, *args):
    """Thread target"""
    event.wait(*args)
    print("Done waiting.")

thread = threading.Thread(target=target, args=(event, 5,))
thread.daemon = True

def exitfunc():
    """Exit function"""
    print("Setting event.")
    event.set()
    thread.join()
    print("Done exiting.")

atexit.register(exitfunc)

thread.start()
print("Done with main thread.")