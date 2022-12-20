from argparse import Namespace
from datetime import datetime, timezone
import os
import subprocess
import time
import shutil

import boto3
import botocore 

BUCKET_NAME = os.getenv("CETI_BUCKET") or 'ceti-data'
DEVICE_ID_FILE = "Device ID List.txt"
DATA_FOLDER = os.path.join(os.getcwd(), "data")
OFFLOAD_DATE_UTC = datetime.now(timezone.utc).strftime('%Y-%m-%d')
CREATION_TIME_IDENTIFIER = "Birth:"
CREATION_TIME_FORMAT = 'Birth: %Y-%m-%d %H:%M:%S.%f %z'


#Get the epoch time of creation for a given file

def get_epoch_time(file):
    result = subprocess.check_output(['stat', f'{file}']).decode('utf-8') #Attempt to get the creationTime using 'stat' for linux based os
    lines = str(result).splitlines()                                      #Unable to get st_birthtime attribute using os.stat

    creationTimeString = ''

    #Extract line with the st_birthtime attribute
    for line in lines:
        line = line.strip()
        if CREATION_TIME_IDENTIFIER in line:
            creationTimeString = line
            break

    creationTime = ''

    try:
        #Trim nanoseconds to millisenconds             EXAMPLE 
        strComponents = creationTimeString.split('.') #Split "Birth: 2022-12-19 15:43:41.463041586 -0500"
        splitStrComponents = strComponents[1].split() #Split "463041586 -0500"
        creationTimeString = strComponents[0] + '.' + splitStrComponents[0][0:3] + ' ' + splitStrComponents[1] #Combine "Birth: 2022-12-19 15:43:41" + ".463" + " -0500"
        creationTime = int(datetime.strptime(creationTimeString, CREATION_TIME_FORMAT).timestamp()*1000) #Convert to milliseconds
    except:
        print(f'WARNING: Could not obtain creation time for file {file}')
        print('Using ctime instead which tracks the last time some file metadata was changed. THIS MAY BE INNACURATE IF NOT USING WINDOWS OS\n')
        creationTime = int(os.path.getctime(file)*1000) #Millisecond epoch time

    return creationTime




def offload_files(s3client, files_to_offload, data_directory, device_id):

    # Prepare the local storage to accept the files

    local_data = os.path.join(DATA_FOLDER, OFFLOAD_DATE_UTC)
    local_data = os.path.join(local_data, device_id)
    if not os.path.exists(local_data):
        os.makedirs(local_data)
    local_files = os.listdir(local_data)


    for file in files_to_offload:
        filepath = os.path.join(data_directory, file)
        ext = os.path.splitext(filepath)[1][1:] #Extract the file extension
        epoch_time = get_epoch_time(filepath) #Get the epoch time of when the file was created
        epoch_name = f'{epoch_time}.{ext}'

        #Copy and rename file if it is not in directory already
        if not epoch_name in local_files:
            shutil.copy(os.path.join(filepath), local_data)
            os.rename(os.path.join(local_data, file), os.path.join(local_data, epoch_name))
            print(f'{file} -> {local_data}/{epoch_name}')
        else:
            print(f'{file} has already been saved to local directory as {local_data}/{epoch_name}')

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

    file_list = os.listdir(args.data_dir)

    if args.dry_run:
        print (f'Found {len(file_list)} files from {args.id} at {args.data_dir}:')
        for file in file_list:
            print (file)
    else:
        offload_files(s3client, file_list, args.data_dir, args.id)
