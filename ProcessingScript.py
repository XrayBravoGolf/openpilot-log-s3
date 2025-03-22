import os
import shutil
recordingFiles = ['fcamera.hevc', 'ecamera.hevc', 'dcamera.hevc', 'qcamera.ts']
logFiles = ['qlog', 'rlog']
def generate_filelists(sourceVidDir, fileNames):
    filelists = {}
    dirs = os.listdir(sourceVidDir)
    #remove boot and crash
    dirs_to_remove = ['boot', 'crash', 'params']
    dirs = list(set(dirs) - set(dirs_to_remove))

    for subdir in sorted(dirs, key=lambda x: int(x.split('--')[-1])):
        subdir_path = os.path.join(sourceVidDir, subdir)
        # assert os.path.isdir(subdir_path):
        timestamp = '--'.join(subdir.split('--')[:-1])  # Extract the timestamp part
        if timestamp not in filelists:
            filelists[timestamp] = {file_type: [] for file_type in fileNames}
        # files = sorted(os.listdir(subdir_path), key=lambda x: int(x.split('--')[-1]))
        for file_type in fileNames:
            if file_type not in os.listdir(subdir_path):
                continue
            filelists[timestamp][file_type].append(os.path.join('..','..',sourceVidDir, subdir, f'{file_type}'))
    return filelists

def moveLogFiles(destinationDir, filelists):
    for timestamp, filelist in sorted(filelists.items()):
        # filelist is a dictionary of {'qlog': 'dir/dir/qlog', 'rlog': 'dir/dir/rlog'}
        # copy each file to destinationDir/timestamp
        for file_type, originFilesList in filelist.items():
            #also rename each file to qlog-0, qlog-1, etc after move (copy, keep original files untouched)
            for i in range(len(originFilesList)):
                print(f'Copying {originFilesList[i]} to {os.path.join(destinationDir, timestamp, f"{file_type}-{i}")}')
                os.makedirs(os.path.join(destinationDir, timestamp), exist_ok=True)
                shutil.copy(originFilesList[i], os.path.join(destinationDir, timestamp, f'{file_type}-{i}'))
        print(f'Finished copying {timestamp}')

def write_filelists(filelists, output_directory):
    for timestamp, filelist in sorted(filelists.items()):
        for file_type, files in filelist.items():
            timestamp_directory = os.path.join(output_directory, timestamp)
            os.makedirs(timestamp_directory, exist_ok=True)
            output_file = os.path.join(timestamp_directory, f'{file_type}.txt')
            with open(output_file, 'w') as f:
                for file_path in files:
                    f.write(f'file \'{file_path}\'\n')

def concat_videos_script(listdir, outdir):
    scriptFile = open('concat_videos.sh', 'w')
    currentProgress = 0
    for timestamp in sorted(os.listdir(listdir)):
        scriptFile.write(f"echo 'Processing {timestamp}'\n")
        scriptFile.write(f"echo 'Progress: {currentProgress}/{len(os.listdir(listdir))}'\n")
        scriptFile.write(f"mkdir {outdir}{os.sep}{timestamp} > $null\n")
        currentProgress += 1
        listsubdirpath = os.path.join(listdir, timestamp)
        assert(os.path.isdir(listsubdirpath))
        for list_file in os.listdir(listsubdirpath):
            assert(list_file.endswith('.txt'))
            list_file_path = os.path.join(listsubdirpath, list_file)
            output_file_type = list_file[0:-4]  # Assuming the first character represents the file type (A, B, or C)
            output_file_path = os.path.join(outdir, timestamp, output_file_type)
            
            concat_command = f"ffmpeg -loglevel error -f concat -safe 0 -i {list_file_path} -c copy {output_file_path}.mp4"
            scriptFile.write(concat_command + '\n')
            # os.system(concat_command)
            # print(f"Concatenation for {list_file} completed.")

def logFileScript7z(log_raw_directory, log_compressed_directory):
    # compress all log files in log_raw_directory to log_compressed_directory
    # compress rlogs and qlogs separately
    # compress rlogs-0, rlogs-1, etc together to rlogs.7z, same for qlogs
    scriptFile = open('compress_logs.sh', 'w')
    currentProgress = 0
    for timestamp in sorted(os.listdir(log_raw_directory)):
        scriptFile.write(f"echo 'Processing {timestamp}'\n")
        scriptFile.write(f"echo 'Progress: {currentProgress}/{len(os.listdir(log_raw_directory))}'\n")
        scriptFile.write(f"cd {os.path.join(log_raw_directory, timestamp)}\n")
        scriptFile.write(f"mkdir {log_compressed_directory}\{timestamp} > $null\n")
        currentProgress += 1
        logsubdirpath = os.path.join(log_raw_directory, timestamp)
        # assert(os.path.isdir(logsubdirpath))
        for file_type in logFiles:
            output_file_path = os.path.join(log_compressed_directory, timestamp, file_type)
            files_to_compress = list(filter(lambda x: x.startswith(file_type), os.listdir(logsubdirpath)))
            if len(files_to_compress) == 0:
                continue
            files_to_compress = sorted(files_to_compress, key=lambda x: int(x.split('-')[-1]))
            compress_command = f"7z a -t7z -m0=lzma2 -mx=9 -mfb=64 -md=64m -ms=on {output_file_path}.7z {' '.join(files_to_compress)}"
            scriptFile.write(compress_command + '\n')


if __name__ == "__main__":
    input_directory = 'D:\\dch'
    output_directory = '/home/xux8/dashcamprocessing/vidlist'
    log_raw_directory = '/home/xux8/dashcamprocessing/logs'
    log_compressed_directory = '/home/xux8/dashcamprocessing/logscompressed'
    filelists = generate_filelists(input_directory, fileNames=recordingFiles)
    write_filelists(filelists, output_directory)
    concat_videos_script(output_directory, '/mnt/e/dashcamvids')

    #filelists = generate_filelists(input_directory, fileNames=logFiles)
    #moveLogFiles(log_raw_directory, filelists)
    #logFileScript7z(log_raw_directory, log_compressed_directory)