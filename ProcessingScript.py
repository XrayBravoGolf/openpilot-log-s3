import os
import shutil
recordingFiles = ['fcamera.hevc', 'ecamera.hevc', 'dcamera.hevc', 'qcamera.ts']
logFiles = ['qlog', 'rlog']

USING_NEW_TIMEINDEPENDENT_SESSION = True

def generateFilelists(sourceVidDir, fileNames):
    filelists = {}
    dirs = os.listdir(sourceVidDir)
    #remove boot and crash
    dirs_to_remove = ['boot', 'crash', 'params']
    dirs = list(set(dirs) - set(dirs_to_remove))

    for subdir in sorted(dirs, key=lambda x: int(x.split('--')[-1])):
        subdirPath = os.path.join(sourceVidDir, subdir)
        assert os.path.isdir(subdirPath)
        recordingSessionName = '--'.join(subdir.split('--')[:-1])  # Extract the timestamp part
        if USING_NEW_TIMEINDEPENDENT_SESSION:
            recordingSessionName = convertBootCounterToDecimal(recordingSessionName)
        # otherwise sessionname is a timestamp
        
        if recordingSessionName not in filelists:
            filelists[recordingSessionName] = {file_type: [] for file_type in fileNames}
        for fileType in fileNames:
            # if a directory does not contain a, say, .hevc file, it will not be added to the list
            if fileType not in os.listdir(subdirPath):
                continue
            filelists[recordingSessionName][fileType].append(os.path.join('..','..', sourceVidDir, subdir, f'{fileType}'))
    return filelists

def convertBootCounterToDecimal(recordingSessionName):
    [bootCounter, sessionID] = recordingSessionName.split('--')
        # convert boot counter to 8 digits decimal
    bootCounter = int(bootCounter, 16)
    bootCounter = str(bootCounter).zfill(8)
    recordingSessionName = bootCounter + '--' + sessionID
    return recordingSessionName

def moveLogFiles(destinationDir, filelists):
    for reccordingSessionName, filelist in sorted(filelists.items()):
        # filelist is a dictionary of {'qlog': 'dir/dir/qlog', 'rlog': 'dir/dir/rlog'}
        # copy each file to destinationDir/timestamp
        for fileType, originFilesList in filelist.items():
            #also rename each file to qlog-0, qlog-1, etc after move (copy, keep original files untouched)
            for i in range(len(originFilesList)):
                print(f'Copying {originFilesList[i]} to {os.path.join(destinationDir, reccordingSessionName, f"{fileType}-{i}")}')
                os.makedirs(os.path.join(destinationDir, reccordingSessionName), exist_ok=True)
                shutil.copy(originFilesList[i], os.path.join(destinationDir, reccordingSessionName, f'{fileType}-{i}'))
        print(f'Finished copying {reccordingSessionName}')

def writeFilelists(filelists, outputDirectory):
    for reccordingSessionName, filelist in sorted(filelists.items()):
        for fileType, files in filelist.items():
            recordingSessionPath = os.path.join(outputDirectory, reccordingSessionName)
            os.makedirs(recordingSessionPath, exist_ok=True)
            output_file = os.path.join(recordingSessionPath, f'{fileType}.txt')
            with open(output_file, 'w') as f:
                for file_path in files:
                    f.write(f'file \'{file_path}\'\n')

def concatVideosScript(listdir, outdir):
    scriptFile = open('concat_videos.sh', 'w')
    currentProgress = 0
    for recordingSessionName in sorted(os.listdir(listdir)):
        scriptFile.write(f"echo 'Processing {recordingSessionName}'\n")
        scriptFile.write(f"echo 'Progress: {currentProgress}/{len(os.listdir(listdir))}'\n")
        scriptFile.write(f"mkdir {outdir}{os.sep}{recordingSessionName} > $null\n")
        currentProgress += 1
        listsubdirpath = os.path.join(listdir, recordingSessionName)
        assert(os.path.isdir(listsubdirpath))
        for listFile in os.listdir(listsubdirpath):
            assert(listFile.endswith('.txt'))
            listFilePath = os.path.join(listsubdirpath, listFile)
            outputFileType = listFile[0:-4]  # Assuming the first character represents the file type (A, B, or C)
            outputFilePath = os.path.join(outdir, recordingSessionName, outputFileType)
            
            concat_command = f"ffmpeg -loglevel error -f concat -safe 0 -i {listFilePath} -c copy {outputFilePath}.mp4"
            scriptFile.write(concat_command + '\n')
            pass
        scriptFile.write(f"echo 'Finished processing {recordingSessionName}'\n")
    scriptFile.write(f"echo 'Finished processing all videos'\n")
    scriptFile.write(f"aws s3 sync {outdir} {S3_DESTINATION_URI}")

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
        scriptFile.close()


if __name__ == "__main__":
    input_directory = 'D:\\dch'
    output_directory = 'D:\\dashcamfilelistoutput'
    # log_raw_directory = '/home/xux8/dashcamprocessing/logs'
    # log_compressed_directory = '/home/xux8/dashcamprocessing/logscompressed'
    filelists = generateFilelists(input_directory, fileNames=recordingFiles)
    writeFilelists(filelists, output_directory)
    concatVideosScript(output_directory, 'D:\\schconsolidatedfiles')

    #filelists = generate_filelists(input_directory, fileNames=logFiles)
    #moveLogFiles(log_raw_directory, filelists)
    #logFileScript7z(log_raw_directory, log_compressed_directory)