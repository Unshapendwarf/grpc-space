# SuperFastPython.com
# example of sharing data with all workers via the initializer
from time import sleep
from multiprocessing.pool import Pool

# task executed in a worker process
def task():
    # declare global variable
    global custom_data
    # report a message with global variable
    print(f"Worker executing with: {custom_data}", flush=True)
    # block for a moment
    sleep(1)


def _reserve_port():
    """Find and reserve a port for all subprocesses to use"""
    for i in range(0, 5):
        yield 50051


# initialize a worker in the process pool
def worker_init(custom):
    # declare global variable
    global custom_data
    # assign the global variable
    custom_data = custom
    # print(custom_data)
    # report a message
    print(f"Initializing worker with: {custom_data}", flush=True)


# protect the entry point
if __name__ == "__main__":
    # define data to share with all workers
    data = "Global State"
    # create and configure the process pool
    with Pool(2, initializer=worker_init, initargs=(next(_reserve_port()),)) as pool:
        # issue tasks to the process pool
        for _ in range(4):
            pool.apply_async(task)
        # close the process pool
        pool.close()
        # wait for all tasks to complete
        pool.join()
