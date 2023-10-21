import datetime
from google.cloud import videointelligence_v1 as videointelligence
import os
import io
import cv2
import logging
from pytube import YouTube
import subprocess

# Replace with your file, downloaded from Google Cloud Video Intelligence API
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'GOOGLE_APPLICATION_CREDENTIALS.json'

def analyze_shots(path, video):
    fps = float(video.get(cv2.CAP_PROP_FPS))
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    print("FPS: ",fps)
    print("Total Frames: ", total_frames)

    # Read the video file as binary and convert to bytes
    with io.open(path, "rb") as f:
        input_content = f.read()

    # Use the VideoIntelligenceServiceClient from videointelligence_v1
    video_client = videointelligence.VideoIntelligenceServiceClient()
    features = [videointelligence.Feature.SHOT_CHANGE_DETECTION]

    # Use annotate_video method from videointelligence_v1, not VideoIntelligenceServiceClient
    operation = video_client.annotate_video(
        request={"features": features, "input_content": input_content}
    )

    print("\nProcessing video for shot change annotations:")

    # result method is not available in videointelligence_v1
    result = operation.result(timeout=90)

    print("\nFinished processing.")

    shot_frames = []  # Store the frame numbers where shot changes occur

    # Iterate through the shot annotations and store the frame numbers
    for i, shot in enumerate(result.annotation_results[0].shot_annotations):
        start_time = (
                shot.start_time_offset.seconds + shot.start_time_offset.microseconds / 1e6
        )
        start_frame = int(start_time * fps)
        shot_frames.append(start_frame)

    print("Saved Frames after Shot Change Detection: ", shot_frames)
    return shot_frames

def FrameCapture(video,lst_frame_shot): 
  
    # Path to video file 
    # vidObj = cv2.VideoCapture(path) 
  
    # Used as counter variable 
    count = 0
    index_photo = 0
    # checks whether frames were extracted 
    success = 1
  
    while success: 
        # vidObj object calls read 
        # function extract frames 
        success, image = video.read() 
        if count in lst_frame_shot:
            index_photo += 1
            lst_frame_shot.remove(count)
            # Saves the frames with frame-count 
            cv2.imwrite("photo/frame%d.jpg" % index_photo, image) 
  
        count += 1
        
    #print("so frame la: ", count)

def delete_files_in_directory(directory_path):
   try:
     files = os.listdir(directory_path)
     for file in files:
       file_path = os.path.join(directory_path, file)
       if os.path.isfile(file_path):
         os.remove(file_path)
     print("All files deleted successfully.")
   except OSError:
     print("Error occurred while deleting files.")

def video_file_name_by_time():
   # Lấy thời gian hiện tại
    current_time = datetime.datetime.now()

    # Tạo tên tệp dựa trên thời gian hiện tại (ví dụ: yyyy_mm_dd_hh_mm_ss)
    file_name = current_time.strftime("%Y%m%d%H%M%S")
    file_name = "video_" + file_name + ".mp4"
    return file_name

def make_video_by_images(image_folder, video_name):
    # Đọc tất cả tệp hình ảnh từ thư mục và sắp xếp chúng theo tên
    images = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]
    images.sort()

    # Thiết lập các thông số của video
    frame = cv2.imread(os.path.join(image_folder, images[0]))
    height, width, layers = frame.shape

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec để ghi video dưới định dạng MP4
    video = cv2.VideoWriter(video_name, fourcc, 1.5, (width, height))  # 1.5 frame mỗi giây

    for image in images:
        video.write(cv2.imread(os.path.join(image_folder, image)))

    cv2.destroyAllWindows()
    video.release()

    delete_files_in_directory(image_folder)

def download_yt(VIDEO_ID):
    # Đường dẫn URL của video YouTube
    # youtube_url = 'https://www.youtube.com/watch?v=' + VIDEO_ID
    
    # Tạo đối tượng YouTube
    yt = YouTube(VIDEO_ID)

    # Lấy stream có sẵn cho video với định dạng MP4 và chất lượng 480p
    stream = yt.streams.filter(file_extension='mp4', res='720p').first()

    # Kiểm tra xem có stream phù hợp không
    if stream:
        # Đặt tên cho video tải về
        video_name = "Video_Download_" + video_file_name_by_time()
        # Tải video xuống với tên đã đặt
        stream.download(output_path='inputs/', filename=video_name)
        print(f"Video đã được tải về và đặt tên là: {video_name}")
    else:
        print("Không có stream MP4 480p cho video này.")
    return 'inputs/' + video_name

def convert_mp4v_to_h264(input_video, output_video):
    try:
        # Mở video gốc để đọc
        cap = cv2.VideoCapture(input_video)

        # Lấy thông tin về video (chiều rộng, chiều cao, tỷ lệ khung hình, ...)
        frame_width = int(cap.get(3))
        frame_height = int(cap.get(4))
        frame_rate = int(cap.get(5))

        # Tạo VideoWriter với codec h264 và tên tệp đầu ra
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        out = cv2.VideoWriter(output_video, fourcc, frame_rate, (frame_width, frame_height))

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Ghi khung hình đã chuyển đổi vào tệp đầu ra
            out.write(frame)

        # Giải phóng tài nguyên
        cap.release()
        out.release()

        print(f"Video converted and saved as {output_video}")

    except Exception as ex:
        print(f"An error occurred: {ex}")

def convert_video_shot_change(VIDEO_ID):
    path = download_yt(VIDEO_ID)
    video = cv2.VideoCapture(path)
    try:
        shot_frames = analyze_shots(path, video)
        FrameCapture(video,shot_frames)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        video.release()

    # Đường dẫn đến thư mục chứa các hình ảnh JPG
    image_folder = 'photo/'

    # Tên của tệp video đầu ra
    video_name_mp4v = "outputs/" + video_file_name_by_time()
    video_name_h264 = "outputs/" + video_file_name_by_time()
    make_video_by_images(image_folder, video_name_mp4v)
    convert_mp4v_to_h264(video_name_mp4v, video_name_h264)
    delete_files_in_directory("outputs/")
    return video_name_h264

