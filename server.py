import logging
import argparse

parser = argparse.ArgumentParser(description='configuration for servers')  # 인자값을 받을 수 있는 인스턴스 생성
# 입력받을 인자값 등록
parser.add_argument('--video_path', default='/mnt/nvme0n1/k400/reduced/train', \
                    help='A directory path where videos stored in ')
args = parser.parse_args()  # 입력받은 인자값을 args에 저장 (type: namespace)

import os
import multiprocessing as mp
from concurrent import futures

import grpc
import grpc_proto.data_feed_pb2
import grpc_proto.data_feed_pb2_grpc
import sys
import socket

# # for pytorch modules 
# import torch
# from torch.utils.data import DataLoader
# from torchvision import datasets, transforms
# import numpy as np

# from PIL import Image
import contextlib


# **************** setting log: started ********************
logger = logging.getLogger()  # 로그 생성
logger.setLevel(logging.INFO)  # 로그의 출력 기준 설정

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# # log를 파일에 출력
# file_handler = logging.FileHandler('my.log')
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)
# **************** setting log: done *************************

NUM_WORKERS = int(os.environ.get("NUM_WORKERS", 2))

def GetFromStorage(filename):
    print('get decoded frames')

def decodeVideo(fpath):
    None

def saveFrame(frames):
    None
    
# def 

# The following class implements the data feeding servie
class DataFeedService(data_feed_pb2_grpc.DataFeedServicer):
    def __init__(self, video_dir, sample_q):
        '''
        param q: A shared queue containing data batches
        '''
        self.video_dir = video_dir
        self.sample_q = sample_q

    def get_sample(self, request, Context):
        filename = request.filename
        GetFromStorage(filename=filename)
        print('already decoded')
        # else:

        return data_feed_pb2.Config(filename=filename)
        # return request.filename
            
    
@contextlib.contextmanager
def _reserve_port():
    """Find and reserve a port for all subprocesses to use"""
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    if sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT) == 0:
        raise RuntimeError("Failed to set SO_REUSEPORT.")
    sock.bind(("", 50051))
    try:
        yield sock.getsockname()[1]
    finally:
        sock.close()


def _run_server(bind_address):
    logger.info(f"Server started. Awaiting jobs with {bind_address}...")
    
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=1),
        options=[
            ("grpc.max_send_message_length", -1),
            ("grpc.max_receive_message_length", -1),
            ("grpc.so_reuseport", 1),
            ("grpc.use_local_subchannel_pool", 1),
        ],
    )
    # data_q = "/mnt/nvme0n1/k400/reduced/train"  # only for AGX Xavier wth 
    data_q = args.video_path
    sample_q = 2
    
    data_feed_pb2_grpc.add_DataFeedServicer_to_server(
        DataFeedService(data_q, sample_q), server)
    
    server.add_insecure_port(bind_address)
    server.start()
    server.wait_for_termination()


def serve():
    """
    Inspired from https://github.com/grpc/grpc/blob/master/examples/python/multiprocessing/server.py
    """
    logger.info(f"Initializing server with {NUM_WORKERS} workers")
    with _reserve_port() as port:
        bind_address = f"[::]:{port}"
        logger.info(f"Binding to {bind_address}")
        sys.stdout.flush()
        workers = []
        for _ in range(NUM_WORKERS):
            worker = mp.Process(target=_run_server, args=(bind_address,))
            worker.start()
            workers.append(worker)
        for worker in workers:
            worker.join()
    

if __name__ == '__main__':
    serve()
    