








# read the process control file
def parse_control_file(process_file):
    size = 5
    input_data = [None] * size # [ timecode_file, source_file, source_type, output_file, split_bool]
    try:
        with open(process_file, 'r') as file:
            for line in file:
                # handle comment
                if (line[0] == "#"):
                    continue
                # Split the line by a delimiter (e.g., space, tab, etc.)
                parts = line.strip().split()
                key = parts[0].lower()
                if (key == "split"):
                    input_data[4] = True
                elif (parts[1] == "="):
                    _text =  string_data = ' '.join(parts[2:]).strip() # Join the rest of the parts into a string
                    if (key == "time"): # time code file
                        input_data[0] = _text
                    elif (key == "source"): # source file
                        input_data[1] = _text
                    elif (key == "type"): # video / audio type
                        input_data[2] = _text
                    elif (key == "output"): # output file
                        input_data[3] = _text
    except FileNotFoundError:
        print(f"Error: File not found at {process_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return input_data


# read and process the timecode data
def read_timecode_data(timecode_file):
    """
    Reads an ASCII file where the first column is a time code and the rest is a string.

    Args:
        file_path: The path to the ASCII file.

    Returns:
        A list of tuples, where each tuple contains the time code and the string.
    """

    time_data = []
    try:
        timecode_file = timecode_file.strip("'")
        timecode_file =timecode_file.strip('"')
        with open(timecode_file, 'r') as file:
            for line in file:
                # Split the line by a delimiter (e.g., space, tab, etc.)
                parts = line.strip().split()

                # Check if the line has at least one part (time code)
                if len(parts) >= 1:
                    time_code = parts[0]  # First part is the time code

                    hours, minutes, seconds = map(int, time_code.split(':')) # split time code into h, m, s

                    string_data = ' '.join(parts[1:]) # Join the rest of the parts into a string
                    time_data.append((time_code, string_data, hours, minutes, seconds))
    except FileNotFoundError:
        print(f"Error: File not found at {timecode_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return time_data


# process the chapter information
def process_chapters(process_input):

    # process the chapter times in the original file
    filepath = process_input[0]
    chapter_data = read_timecode_data(filepath)

    # process the input file using ffmpeg at those chapter markers
    srcfile = process_input[1]
    filetype = process_input[2]
    outfile = process_input[3]
    splitfile = process_input[4]

    # call underlying routine
    do_chapters(chapter_data, srcfile, outfile, splitfile, filetype)



# cut source file into chapters
def do_chapters(chapter_data, src_file, out_file, split_file, file_type):
    """
    add chapter markers or cut video or audio source file into chapters using ffmpeg

    Args:
        data: list of the starting time codes and the chapter names
        src_file: path of the source file
        out_file: base name of the chapter tagged output file
        split_file: bool for create individual chapter files
        file_type: audio or video
    """
    
    # processing bools
    do_full = (out_file != None)
    do_audio = (file_type == "audio")

    # create lag of lists
    import itertools
    chapter_data_lead_1 = itertools.islice(chapter_data, 1, None, 1)

    # get source file extension
    import os
    src_filename, src_extension = os.path.splitext(src_file)

    # contant strings
    chapterkey = '[CHAPTER]'
    timedef = 'TIMEBASE=1/1000'
    emptyline = ''
    ffcmd = 'ffmpeg '
    ext = src_extension.rstrip('"') # original extension is the source file
    ffopt = ' -codec copy '

    # adjust strings for audio processing
    if (do_audio == True):
        ext = '.mp3'
        ffopt = ' '

    # replace output extension handling closing double quotes
    out_filename, out_extension = os.path.splitext(out_file)
    if (out_filename[-1:] == '"'):
        out_file = out_filename.rstrip('"') + ext + '"' # add the extension inside the closing double quote
    else:
        out_file = out_filename + ext # add the extension y


    # open the metadata and batch files clearing out contents if necessary
    cmd = ffcmd + ' -i ' + src_file + ' -f ffmetadata xx_ffmetadatafile.txt'
    os.system(cmd)
    if (do_full == True):
        with open('xx_ffmetadatafile.txt', 'a') as f:
            pass

    if (split_file == True):
        with open('xx_ffmpeg_batch.bat', 'w') as g:
            pass


    # process each of the timecodes in the list
    i = 1
    for (element, element_1) in zip(chapter_data, chapter_data_lead_1):

        # extract list elements
        time_code, string, hours, minutes, seconds = element
        time_code_1, string_1, hours_1, minutes_1, seconds_1 = element_1

        #print(element_1)

        # add to map file for chapter encoding
        if (do_full == True):

            # start times
            startsec = seconds + minutes*60 + hours*60*60 # total seconds
            startmsec = startsec * 1000 # total milliseconds
            startkey = 'START=' + str(startmsec)

            # end times
            endsec = seconds_1 + minutes_1*60 + hours_1*60*60 # total seconds
            endmsec = endsec * 1000 # total milliseconds
            endkey = 'END=' + str(endmsec)
        
            # title
            title = 'TITLE=' + string

            with open('xx_ffmetadatafile.txt', 'a') as f:
                f.write(emptyline + '\n')
                f.write(chapterkey + '\n')
                f.write(timedef + '\n')
                f.write(startkey + '\n')
                f.write(endkey + '\n')
                f.write(title + '\n')
    
        # add to batch file for split
        if (split_file == True):

            # ffmpeg command
            ffmpegname = '\"' + str(i).zfill(2) + ' ' + string + ext + '\"'
            ffmpegcmd = ffcmd + ' -ss ' + str(startsec) + ' -to ' + str(endsec) + ' -i ' + src_file + ffopt + ffmpegname
            with open('xx_ffmpeg_batch.bat', 'a') as g:
                 g.write(ffmpegcmd + '\n')
  
        # increment
        i = i + 1

    # take those chapter times and the created by this program and encode the original file 
    # with chapter markers
    if (do_full == True):
        if (do_audio == True):
           typeopt = ' -i xx_ffmetadatafile.txt -map_metadata 1 -vn -acodec libmp3lame '            
        else:
           typeopt = ' -i xx_ffmetadatafile.txt -map_metadata 1 -c copy '
        cmd = 'ffmpeg -i ' + src_file + typeopt + out_file
        os.system(cmd)
        
    # do splitting and cleanup batch file
    if (split_file == True):
        cmd = 'xx_ffmpeg_batch.bat'
        os.system(cmd)
        cmd = 'del ' + cmd
        os.system(cmd)

   # cleanup chapter metadata file
    if (do_full == True):
        cmd = 'del xx_ffmetadatafile.txt'
        os.system(cmd)


######################################################################################3333

cmdfile = "chapter_tag.txt"
try:
    with open(cmdfile, 'r') as file:
        for line in file:
            if len(line) > 0:
                procinput = line
                break
except FileNotFoundError:
    print(f"Error: File not found at {"cmdfile"}")
except Exception as e:
    print(f"An error occurred: {e}")          


# parse the control file
process_input = parse_control_file(procinput)

#print(process_input)

# process the chapter information
process_chapters(process_input)