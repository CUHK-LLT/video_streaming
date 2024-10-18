# server.py
import asyncio

import cv2
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCRtpCodecCapability
from aiortc.contrib.media import MediaRelay
import time
import matplotlib.pyplot as plt


relay = MediaRelay()

# Dictionary to hold information about peer connections
peers = {}


async def process_track(track):
    print("Track started!")
    frame_index = 1
    frames = []  # 用于存储帧数据
    timestamps = []  # 用于存储时间戳

    try:
        while True:
            frame = await track.recv()
            img = frame.to_ndarray(format="bgr24")
            frames.append(img)
            timestamps.append(time.time())
            print(f"Received frame {frame_index} at {timestamps[-1]}")
            frame_index += 1

    except Exception as e:
        print(f"Caught an exception: {type(e).__name__}, message: {e}")
        # 轨道结束，保存视频和时间戳
        save_video(frames, timestamps)
    finally:
        print("End the frame recv()")

def save_video(frames, timestamps):
    if not frames:
        print("No frames to save.")
        return

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 使用MP4编码器
    out = cv2.VideoWriter("r.mp4", fourcc, 100.0, (1920, 1080))  # 假设分辨率为1080P或2K，帧率设为100fps

    start_time = timestamps[0]
    frame_index = 0
    current_time = start_time
    print(len(frames))
    
    while frame_index < len(frames) - 1:
        # 寻找当前时间点最接近的帧
        closest_frame_index = frame_index
        while (frame_index < len(timestamps) - 1 and timestamps[frame_index] <= current_time):
            closest_frame_index = frame_index
            frame_index += 1

        # 写入选定的帧
        out.write(frames[closest_frame_index])
        # 增加10ms到下一个目标时间点
        current_time += 0.010

    out.release()
    print("Video saved with enhanced fps based on timestamps.")


async def index(request):
    content = open('index.html', 'r').read()
    return web.Response(content_type='text/html', text=content)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = "peer_connection_{}".format(len(peers))
    peers[pc_id] = pc

    @pc.on("track")
    async def on_track(track):
        print("Video Track is established")

        if track.kind == "video":
            original_track = track
            # 创建一个任务以处理接收到的视频轨
            asyncio.create_task(process_track(original_track))

        @track.on("ended")
        async def on_ended():
            print("Video track ended")

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


# 启动web服务器
app = web.Application()
app.router.add_get('/', index)
# offer响应视频轨道请求
app.router.add_post('/offer', offer)

if __name__ == '__main__':
    web.run_app(app, port=8080)
