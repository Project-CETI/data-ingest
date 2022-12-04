from argparse import Namespace
import os
import time
import shutil

import boto3
import botocore 

BUCKET_NAME = os.getenv("CETI_BUCKET") or 'ceti-data'
DEVICE_ID_FILE = "Device ID List.txt"
DATA_FOLDER = os.path.join(os.getcwd(), "data")
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


def offload_files(s3client, files_to_offload, data_directory, device_id):

    # Prepare the local storage to accept the files

    local_video_data = os.path.join(DATA_FOLDER, device_id)
    if not os.path.exists(local_video_data):
        os.makedirs(local_video_data)
    local_files = os.listdir(local_video_data)


    for file in files_to_offload:

        #Get the epoch time of when the file was created
        storage_device_filepath = os.path.join(data_directory, file)
        ext = os.path.splitext(storage_device_filepath)[1][1:] #Extract the file extension
        epoch_time = int(os.path.getctime(storage_device_filepath))
        epoch_name = f'{epoch_time}.{ext}'

        #Copy and rename file if it is not in directory already
        if not epoch_name in local_files:
            shutil.copy(os.path.join(storage_device_filepath), local_video_data)
            os.rename(os.path.join(local_video_data, file), os.path.join(local_video_data, epoch_name))
            print(f'{file} -> {local_video_data}/{epoch_name}')
        else:
            print(f'{file} has already been saved to local directory as {local_video_data}/{epoch_name}')

def get_registered_devices(s3client):
   
    id_file = s3client.get_object(Bucket=BUCKET_NAME, Key=DEVICE_ID_FILE)
    device_ids = id_file['Body'].read().decode('utf-8').splitlines()
    stripped_device_ids = [id.strip() for id in device_ids]
    return stripped_device_ids
    
    


def cli(args: Namespace):
    
    print()
    s3client = boto3.client('s3')
    registered_device_ids = get_registered_devices(s3client)

    if not os.path.exists(args.data_dir):
        print(f'Path \"{args.data_dir}\" does not exist')
        return
    elif not args.id:
        print('No data capture device ID was specified')
        return
    elif not args.id in registered_device_ids:
        print(f'Device ID \"{args.id}\" has not been registered. The registered IDs are: ')
        print(*registered_device_ids, sep = '\n')
        print()
        print("If you are offloading from a shared ceti device, look for a device ID label on the device")
        return

    video_files = get_video_files(args.data_dir)

    if args.dry_run:
        print (f'Found {len(video_files)} files from {args.id} at {args.data_dir}:')
        for file in video_files:
            print (file)
    else:
        offload_files(s3client, video_files, args.data_dir, args.id)
