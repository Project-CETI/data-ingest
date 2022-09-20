from argparse import Namespace
import os
import time
import shutil

LOCAL_VIDEO_DATA = os.path.join(os.getcwd(), "video_data")
SUPPORTED_FILE_EXTENSIONS = ["mp4", "mov", "mks", "avi"]

def get_video_files(data_directory):
    files = os.listdir(data_directory)
    video_files = []
    for file in files:
        filepath = os.path.join(data_directory, file)
        ext = os.path.splitext(filepath)[1][1:].lower() #Extract the file extension
        if ext in SUPPORTED_FILE_EXTENSIONS:
            video_files.append(file)
    return video_files


def offload_files(files_to_offload, data_directory):

    # Prepare the local storage to accept the files
    if not os.path.exists(LOCAL_VIDEO_DATA):
        os.makedirs(LOCAL_VIDEO_DATA)
    local_files = os.listdir(LOCAL_VIDEO_DATA)


    for file in files_to_offload:

        #Get the epoch time of when the file was created
        storage_device_filepath = os.path.join(data_directory, file)
        ext = os.path.splitext(storage_device_filepath)[1][1:] #Extract the file extension
        epoch_time = int(os.path.getctime(storage_device_filepath))
        epoch_name = f'{epoch_time}.{ext}'

        #Copy and rename file if it is not in directory already
        if not epoch_name in local_files:
            shutil.copy(os.path.join(storage_device_filepath), LOCAL_VIDEO_DATA)
            os.rename(os.path.join(LOCAL_VIDEO_DATA, file), os.path.join(LOCAL_VIDEO_DATA, epoch_name))
            print(f'{file} -> {epoch_name}')
        else:
            print(f'{file} has already been saved to local directory as {epoch_name}')


def cli(args: Namespace):
    if not os.path.exists(args.data_directory):
        print(f'Path {args.data_directory} does not exist')
        return

    video_files = get_video_files(args.data_directory)

    if args.dry_run:
        print (f'Found {len(video_files)} files at {args.data_directory}:')
        for file in video_files:
            print (file)
    else:
        offload_files(video_files, args.data_directory)
