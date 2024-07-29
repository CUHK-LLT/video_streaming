# client.py
import asyncio
import logging
import time

import aiohttp
import av
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCRtpSender

"""
用于小车采集视频并发包,基于aiortc。基于aiohttp发起web请求。
"""
relay = []
webcam = []
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def force_codec(pc, sender, forced_codec):
    kind = forced_codec.split("/")[0]
    codecs = RTCRtpSender.getCapabilities(kind).codecs
    transceiver = next((t for t in pc.getTransceivers() if t.sender == sender), None)
    if transceiver:
        transceiver.setCodecPreferences([codec for codec in codecs if codec.mimeType == forced_codec])


class VideoFrameTrack(VideoStreamTrack):
    """
    A video stream track that relays frames from OpenCV's VideoCapture.
    """

    def __init__(self, source):
        super().__init__()  # don't forget to initialize base class
        self.source = source
        self.read_count = 0  # Counter to track the number of frames read

    async def recv(self):
        while True:
            pts, time_base = await self.next_timestamp()

            # Read frame from OpenCV
            ret, frame = self.source.read()
            if not ret:
                raise Exception("Could not read frame from OpenCV VideoCapture after resetting")

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create a raw pyav.VideoFrame from the RGB frame
            av_frame = av.VideoFrame.from_ndarray(frame, format='rgb24')
            av_frame.pts = pts
            av_frame.time_base = time_base

            self.read_count += 1
            current_time = time.time()
            logging.info(f"Send a frame: {self.read_count} at {current_time:.6f}")

            return av_frame


async def main():
    # 创建 RTCPeerConnection 实例时传入配置
    pc = RTCPeerConnection()

    # 获取视频源
    # 打开默认摄像头
    capture = cv2.VideoCapture(0)  # 0通常是默认的摄像头

    # 尝试设置摄像头的分辨率和帧率
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    capture.set(cv2.CAP_PROP_FPS, 30)

    # 检查分辨率是否设置成功
    width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = capture.get(cv2.CAP_PROP_FPS)
    print(f"Set resolution: {width} x {height} : {fps}")
    # Create the video track
    video_track = VideoFrameTrack(capture)
    # 获取rtcrtpsender类的实例
    video_sender = pc.addTrack(video_track)

    # Force the video codec
    # force_codec(pc, video_sender, "video/H264")

    # Create an offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    # Send the offer to the server
    async with aiohttp.ClientSession() as session:
        # 请修改IP地址以匹配自己的服务器
        async with session.post('http://127.0.0.1:8080/offer', json={
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }) as resp:
            answer = await resp.json()
            print("Received answer")

            # Set the remote description
            await pc.setRemoteDescription(RTCSessionDescription(
                sdp=answer["sdp"],
                type=answer["type"]
            ))

    print("Begin Video capture AND rtp transmission")

    await asyncio.sleep(0.1)
    await asyncio.sleep(10)
    print("That's all")

    # Close the track and connection
    print(video_track.read_count)
    video_track.stop()
    await pc.close()


if __name__ == '__main__':
    asyncio.run(main())
