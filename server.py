import logging
import argparse
# multiprocess and grpc modules
import os
import multiprocessing as mp
from concurrent import futures

import grpc
import sys
import socket
import pickle
import glob

import torch
# # for pytorch modules 
# from torch.utils.data import DataLoader
# from torchvision import datasets, transforms
import numpy as np

from PIL import Image
import contextlib
import random
import math

# decoder, containers, utilities
from decoder import decoder
from decoder import video_container as container
from decoder import utils as utils


# from partial_slow.config.defaults import assert_and_infer_cfg
# from partial_slow.utils.misc import launch_job
# from partial_slow.utils.parser import load_config, parse_args

sys.path.append("./grpc_proto")
import data_feed_pb2_grpc
import data_feed_pb2

# ------------- setting log, config: started ---------------
parser = argparse.ArgumentParser(description='configuration for servers')  # 인자값을 받을 수 있는 인스턴스 생성
# 입력받을 인자값 등록
parser.add_argument('--video_path', default='/mnt/nvme0n1/data/k400/reduced/train', \
                    help='A directory path where videos stored in ')
                    
args = parser.parse_args()  # 입력받은 인자값을 args에 저장 (type: namespace)


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

# configurations
TRAIN_CROP_SIZE = 96
TARGET_FPS = 30
TRAIN_JITTER_SCALES = [256, 320]
TRAIN_JITTER_FPS = 0.0
NUM_ENSEMBLE_VIEWS = 10  # cfg.TEST.NUM_ENSEMBLE_VIEWS

NUM_WORKERS = int(os.environ.get("NUM_WORKERS", 4))
savepoint = os.path.join("/data/hong/savepoint")  # mango3
# savepoint = os.path.join("/mnt/nvme0n1/data/savepoint")  # AGX Xavier

preview_cfg = 16

csv_file = os.path.join("./index_files/train.csv")
video_path = "/data/hong/k400/reduced/train/"
# video_path = args.video_path  # for agx machine
video_names = []


def set_video_index():
    with open(csv_file, 'r') as fr:
        for line in fr.readlines():
            n_name = os.path.basename(line)
            video_names.append(os.path.splitext(n_name)[0])


# ---------------------------------------------------------
def GetDecoded(index, filename):
    # check hashmap to get filename and its infomation
    i = 0
    trgt_fname = os.path.join(savepoint, f"{filename}_{i}_st.pckl")
    while not os.path.exists(trgt_fname):
        i+=1
        if i>=preview_cfg:
            break  # or return immediately
        trgt_fname = os.path.join(savepoint, f"{filename}_{i}_st.pckl")

    if i>=preview_cfg:
        return None, None, None
    else:
        # filename in frame_list == decoded frames are there
        trgt_path = os.path.join(savepoint, f"{filename}_{i}")
        
        decoded_data = [trgt_path+x for x in ["_a.png", "_b.png", "_st.pckl", "_tdiff.pckl"]]

        img_a, img_b = Image.open(decoded_data[0]), Image.open(decoded_data[1])
        total_w, total_h = img_a.size
        curr_frames_a, curr_frames_b = [], []

        for w in range(int(total_w/TRAIN_CROP_SIZE)):
            for h in range(int(total_h/TRAIN_CROP_SIZE)):
                position = (w*TRAIN_CROP_SIZE, h*TRAIN_CROP_SIZE,(w+1)*TRAIN_CROP_SIZE, (h+1)*TRAIN_CROP_SIZE)
                
                cropped_a, cropped_b = img_a.crop(position), img_b.crop(position)
                np_cropped_a, np_cropped_b = np.array(cropped_a), np.array(cropped_b)
                curr_frames_a.append(cropped_a)
                curr_frames_b.append(cropped_b)
        
        ret_frames = [torch.as_tensor(np.stack(curr_frames_a)), torch.as_tensor(np.stack(curr_frames_b))]

        with open(decoded_data[2], 'rb') as f2:
            ret_st = pickle.load(f2)
        with open(decoded_data[3], 'rb') as f3:
            ret_tdiff = pickle.load(f3)

        # remove storage data after loading is complete
        for u_file in decoded_data:
            if os.path.exists(u_file):
                os.remove(u_file)
            else:
                print("error to remove" + u_file)

        return ret_frames, ret_st, ret_tdiff
    


def Decode(index, videoname):
    # same as the function in decoder.py of slowfast
    min_scale, max_scale, crop_size = TRAIN_JITTER_SCALES, 320, 96
    min_scale, max_scale, crop_size = [min_scale], [max_scale], [crop_size]
    num_decode = 2  # num_decode = self.cfg.DATA.TRAIN_CROP_NUM_TEMPORAL if self.mode in ["train"] else 1
    if len(min_scale) < num_decode:
        min_scale += [TRAIN_JITTER_SCALES[0]] * (num_decode - len(min_scale))
        max_scale += [TRAIN_JITTER_SCALES[1]] * (num_decode - len(max_scale))
        crop_size += (
            [TRAIN_CROP_SIZE] * (num_decode - len(crop_size))
        )
    
    video_container = None
    assert video_names[index] == videoname
    path_to_video = os.path.join(video_path, videoname+".mp4")
    try:
        video_container = container.get_video_container(path_to_video, False, 'pyav')
    except Exception as e:
        logger.info("Failed to load video from {} with error {}".format(path_to_video, e))
        index = random.randint(0, len(video_names) - 1)
        # continue  # Select a random video if the current video was not able to access.
    
    if video_container is None:
        logger.warning("Failed to meta load video idx {} from {};".format(index, os.path.join(video_path, videoname+".mp4")))

    frames_decoded, time_idx_decoded = (
        [None] * num_decode,
        [None] * num_decode,
    )
    
    # for i in range(num_decode):
    # num_frames = [self.cfg.DATA.NUM_FRAMES]
    num_frames = [8]
    sampling_rate = 8
    sampling_rate = [sampling_rate]
    
    if len(num_frames) < num_decode:
        num_frames.extend([num_frames[-1] for i in range(num_decode - len(num_frames))])
        # base case where keys have same frame-rate as query
        sampling_rate.extend([sampling_rate[-1] for i in range(num_decode - len(sampling_rate))])
    elif len(num_frames) > num_decode:
        num_frames = num_frames[:num_decode]
        sampling_rate = sampling_rate[:num_decode]
    
    target_fps = TARGET_FPS
    if TRAIN_JITTER_FPS > 0.0:
        target_fps += random.uniform(0.0, TRAIN_JITTER_FPS)

    # Decode video. Meta info is used to perform selective decoding.
    temporal_sample_index = -1  # -1 indicate random sampling
    frames, time_idx, tdiff = decoder.my_decode(
        video_container,
        sampling_rate,
        num_frames,
        temporal_sample_index,
        NUM_ENSEMBLE_VIEWS,
        target_fps=target_fps,
        use_offset=False,
        max_spatial_scale=min_scale[0] if all(x == min_scale[0] for x in min_scale) else 0,  # if self.mode in ["test"] else 0,
        time_diff_prob=0.0, #  self.p_convert_dt if self.mode in ["train"] else 0.0,
        temporally_rnd_clips=True,
        min_delta=-math.inf,
        max_delta=math.inf,
        num_preview=preview_cfg,
        save_path=os.path.join(savepoint, videoname),
    )
    if frames == None:
        print("failed to decode")
        return None, None, None
    
    frames_decoded = frames
    time_idx_decoded = time_idx
    tdiff_decoded = tdiff

    return frames_decoded, time_idx_decoded, tdiff_decoded


# The following class implements the data feeding servie
class DataFeedService(data_feed_pb2_grpc.DataFeedServicer):
    def __init__(self, video_dir, sample_q):
        '''
        param q: A shared queue containing data batches
        '''
        self.video_dir = video_dir
        self.sample_q = sample_q

    def get_sample(self, request, Context):
        idx = request.index
        filename = request.filename
        
        frames, st_list, tdiffs= GetDecoded(index=idx, filename=filename)
        if frames==None:
            print(f"decode: {filename}")
            frames, st_list, tdiffs = Decode(idx, filename)
        
        if frames==None:
            return data_feed_pb2.Sample(frames=None,
                                    st_times=None,
                                    tdiffs=None,
                                    num_fr=1,
                                    size_fr=TRAIN_CROP_SIZE,
                                    )
            

        ret_frames = [frame.numpy().tobytes() for frame in frames]        
        
        ret_f = data_feed_pb2.Frames(frame1 = ret_frames[0], frame2 = ret_frames[1])
        ret_s = data_feed_pb2.ST_times(st_time1 = st_list[0], st_time2 = st_list[1])
        ret_t = data_feed_pb2.Tdiffs(tdiff1 = tdiffs[0], tdiff2 = tdiffs[1])
        
        return data_feed_pb2.Sample(frames=ret_f,
                                    st_times=ret_s,
                                    tdiffs=ret_t,
                                    num_fr=8,
                                    size_fr=TRAIN_CROP_SIZE,
                                    )
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
    set_video_index()
    serve()
    