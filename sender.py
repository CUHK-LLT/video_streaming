import asyncio
import aiohttp
import av
import cv2
import time
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack

class VideoFrameTrack(VideoStreamTrack):
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.frames = []
        self.timestamps = []
        self.index = 1

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        ret, frame = self.source.read()
        if not ret:
            raise Exception("Could not read frame from video file")
        
        print(f"Get frame {self.index} at {time.time()}")
        self.index += 1

        # Store frame with the current time offset
        self.frames.append(frame)
        self.timestamps.append(time.time())
        
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        av_frame = av.VideoFrame.from_ndarray(frame, format='rgb24')
        av_frame.pts = pts
        av_frame.time_base = time_base
        
        return av_frame

def save_video(frames, timestamps, path='s.mp4',):
    if not frames:
        print("No frames to save.")
        return

    # Initialize video writer
    height, width, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, 100, (width, height))

    # Write frames based on time intervals
    start_time = timestamps[0]
    frame_index = 0
    current_time = start_time
    print(len(frames))

    while frame_index < len(frames):
        # 寻找当前时间点最接近的帧
        closest_frame_index = frame_index
        while (frame_index < len(timestamps) and timestamps[frame_index] <= current_time):
            closest_frame_index = frame_index
            frame_index += 1

        # 写入选定的帧
        out.write(frames[closest_frame_index])
        # 增加10ms到下一个目标时间点
        current_time += 0.010

    out.release()
    print("Video saved with enhanced fps based on timestamps.")


async def main():
    pc = RTCPeerConnection()
    capture = cv2.VideoCapture('/home/qj/Documents/Video/1.mp4')
    width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
    print(width)

    video_track = VideoFrameTrack(capture)
    pc.addTrack(video_track)

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    print("SDP exchange success")

    async with aiohttp.ClientSession() as session:
        async with session.post('http://127.0.0.1:8080/offer', json={
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }) as resp:
            answer = await resp.json()
            await pc.setRemoteDescription(RTCSessionDescription(
                sdp=answer["sdp"],
                type=answer["type"]
            ))

    await asyncio.sleep(15)  # Capture for a specified time
    print("Video upload ended")

    # Process and save video from recorded frames
    save_video(video_track.frames, video_track.timestamps)

    video_track.stop()
    await pc.close()

if __name__ == '__main__':
    asyncio.run(main())