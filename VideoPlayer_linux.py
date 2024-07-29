import asyncio
import cv2
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCRtpCodecCapability
from aiortc.contrib.media import MediaRelay
import time
import logging

relay = MediaRelay()

# Dictionary to hold information about peer connections
peers = {}
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


# Process and display the video frames
async def process_track(track):
    logging.info("Track wait!")

    try:
        frame_index = 0  # 假设有一个变量记录帧序号
        while True:
            try:
                # 设置10秒超时，接收新帧
                frame = await asyncio.wait_for(track.recv(), timeout=10)
                current_time = time.time()
                logging.info(f"Received a frame: {frame_index} at {current_time:.6f}")
                frame_index += 1
            except asyncio.TimeoutError:
                # 如果超过10秒没有接收到新的帧，抛出异常
                raise Exception("Frame reception timed out after 10 seconds")

            # 假设frame.to_ndarray(format="bgr24")是转换帧为ndarray的方法
            img = frame.to_ndarray(format="bgr24")
    except Exception as e:
        logging.error(f"Caught an exception: {type(e).__name__}, message: {e}")
    finally:
        logging.info("This connection closed !")


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
            # 创建一个任务以处理接收到的视频轨
            asyncio.create_task(process_track(track))

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
app.router.add_post('/offer', offer)

if __name__ == '__main__':
    web.run_app(app, port=8080)
