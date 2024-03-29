# Python std lib
import time
import os
import atexit
import multiprocessing
import typing as tp

import sys
import logging
import argparse
import glob

# 3rd party libs
import cv2 as cv
import grpc
import numpy as np

sys.path.append("./grpc_proto")
import data_feed_pb2
import data_feed_pb2_grpc

# import grpc_proto.data_feed_pb2 as data_feed_pb2
# import grpc_proto.data_feed_pb2_grpc as data_feed_pb2_grpc

NUM_CLIENTS = 10
NUM_IMAGES = 12

# *********************** arg parser: start **************************
parser = argparse.ArgumentParser(description="configuration for clients")  # 인자값을 받을 수 있는 인스턴스 생성
# 입력받을 인자값 등록
parser.add_argument(
    "--video_path",
    # required=True,
    default="/data/hong/k400/reduced/train/",
    help="A directory path where videos are stored in ",
)
args = parser.parse_args()  # 입력받은 인자값을 args에 저장 (type: namespace)
# *********************** art parser: done ***************************

# **************** setting log: started ********************
logger = logging.getLogger()  # 로그 생성
logger.setLevel(logging.INFO)  # 로그의 출력 기준 설정

# log 출력 형식
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# log 출력
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# log를 파일에 출력
file_handler = logging.FileHandler("client.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# **************** setting log: done *************************

csv_file = os.path.join("./index_files/train.csv")
video_path = "/data/hong/k400/reduced/train/"
video_names = []

_worker_channel_singleton = None
_worker_stub_singleton = None


def _shutdown_worker():
    """
    Close the open gRPC channel.

    Returns:
        None

    """
    if _worker_channel_singleton is not None:
        _worker_channel_singleton.stop()


def _initialize_worker(server_address: str) -> None:
    """
    Setup a grpc stub if not available.

    Args:
        server_address (str)

    Returns:
        None
    """
    global _worker_channel_singleton
    global _worker_stub_singleton
    _worker_channel_singleton = grpc.insecure_channel(
        server_address,
        options=[
            ("grpc.max_send_message_length", -1),
            ("grpc.max_receive_message_length", -1),
            ("grpc.so_reuseport", 1),
            ("grpc.use_local_subchannel_pool", 1),
        ],
    )
    try:
        logger.info("init workers")
        _worker_stub_singleton = data_feed_pb2_grpc.DataFeedStub(_worker_channel_singleton)
    except grpc.RpcError as e:
        logger.error("Error creating stub: {}".format(e.details()))
    else:
        print("init done")
    # print(type(_worker_channel_singleton)
    atexit.register(_shutdown_worker)


def _run_worker_query(get_tuple: tuple) -> str:
    """
    Execute the call to the gRPC server.

    Args:
        img (bytes): bytes representation of the image

    Returns:
        detected text on the image

    """
    index, imgname = get_tuple
    # print(f"send {imgname}, ", end="")

    response: data_feed_pb2.Sample = _worker_stub_singleton.get_sample(
        data_feed_pb2.Config(index=index, filename=imgname)
    )

    num_fr, size_fr = response.num_fr, response.size_fr
    reconstruction = (num_fr, size_fr, size_fr, 3)
    frame1 = np.frombuffer(response.frames.frame1, dtype=np.uint8).reshape(reconstruction)
    frame2 = np.frombuffer(response.frames.frame1, dtype=np.uint8).reshape(reconstruction)
    # print(f"received frame: {frame1}")

    # print(list(response.st_times.st_time1))
    frames = [frame1, frame2]
    st_time = [list(response.st_times.st_time1), list(response.st_times.st_time2)]
    tdiff = [list(response.tdiffs.tdiff1), list(response.tdiffs.tdiff2)]

    return "1"
    # return response.image


def compute_detections(batch: tp.List[tuple]) -> tp.List:
    """
    Start a pool of process to parallelize data processing across several workers.

    Args:
        batch: a list of images.

    Returns:
        the list of detected texts.

    Inspired from https://github.com/grpc/grpc/blob/master/examples/python/multiprocessing/client.py

    """
    server_address = "localhost:50051"
    # server_address = "143.248.53.54:50051"

    with multiprocessing.Pool(
        processes=NUM_CLIENTS,
        initializer=_initialize_worker,
        initargs=(server_address,),
    ) as worker_pool:

        ocr_results = worker_pool.map(
            _run_worker_query,
            batch,
        )
        # print(ocr_results)
        return [txt for txt in ocr_results]


def prepare_batch() -> tp.List[str]:
    """
    Generate a batch of image data to process.

    Returns:
        batch: (tp.List[bytes])
    """
    logger.info("Get image names...")
    with open(csv_file, "r") as fr:
        for line in fr.readlines():
            n_name = os.path.basename(line)
            video_names.append(os.path.splitext(n_name)[0])
    # batch: tp.List[str] = [os.path.basename(x) for x in glob.glob(os.path.join(video_path, "*.mp4"))]
    batch: tp.List[tuple] = [(i, videoname) for i, videoname in enumerate(video_names)]
    return batch


# def prepare_batch_origin() -> tp.List[bytes]:
#     """
#     Generate a batch of image data to process.

#     Returns:
#         batch: (tp.List[bytes])
#     """
#     logger.info("Reading src image...")
#     source = "sample.png"
#     img = cv.imread(source)
#     batch: tp.List[bytes] = []
#     for _ in range(NUM_IMAGES):
#         batch.append(img)
#     # FIll last batch with remaining
#     return batch


def run():
    logger.info("My test client started.")
    batch = prepare_batch()
    logger.info("Batch ready, calling grpc server...")

    start = time.perf_counter()
    results = compute_detections(batch)
    duration = time.perf_counter() - start
    logger.info(
        f"gRPC server answered. Processed {NUM_IMAGES} images in {round(duration,2)} UA ({NUM_CLIENTS} clients)"
    )
    logger.info(f"Text  detected on the first image: {results[0]}")


if __name__ == "__main__":
    run()
