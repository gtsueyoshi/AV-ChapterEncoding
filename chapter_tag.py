
# read the process control file
def parse_control_file(process_file):
    """
    parse the chapter tag control flie

    syntax for each line:

    . leading "#" is a comment line

    . [key] = [arg]

        where key = { "time", "source", "type", "output" } and
            : time [arg] is the name of the timecode file with lines of the form "hh:mm:ss {chaptername}
            : source [arg] is the original audio or video source file
            : type [arg] is { "audio", "video" } for encoding
            : output [arg] is the name of the base of the output flie
            : metaname [arg] is the optional name of the metadata temp file
            : batchname [arg] is the optional name of the ffmpet split batch file

    . "split" is provided if you wish to split the output into individual chapter files
    . "keep" is provided if you wish to keep the metadata file and the batch file

    . all other lines are ignored

    """

    size = 8
    input_data = [None] * size # [ timecode_file, source_file, source_type, output_file, split_bool, keep_temps]
    process_file_nq = process_file.strip('"') # remove surrounding double quote because open doesn't like
    try:
         with open(process_file_nq, 'r') as file:
            for line in file:
                # handle comment
                if (line[0] == "#"):
                    continue
                # split the line by a delimiter (e.g., space, tab, etc.)
                parts = line.strip().split()
                key = parts[0].lower()
                if (key == "split"):
                    input_data[4] = True
                elif (key == "keep"):
                    input_data[5] = True
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
                    elif (key == "metafile"): # metadata file
                        input_data[6] = _text
                    elif (key == "batchfile"): # ffmpeg batch file
                        input_data[7] = _text

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
         timecode_file_nq = timecode_file.strip('"') # remove surrounding double quote because open doesn't like
         with open(timecode_file_nq, 'r') as file:
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



# cut source file into chapters
def process_chapters(chapter_data, process_input):
    """
    add chapter markers or cut video or audio source file into chapters using ffmpeg

    Args:
        chapter_data: list of the starting time codes and the chapter names
        process_input: the parsed input

    """
    # analyze the chapter times file
    chapter_path = process_input[0] # chapter information
    chapter_data = read_timecode_data(chapter_path)

    # create lag of chapter time lists
    import itertools
    chapter_data_lead_1 = itertools.islice(chapter_data, 1, None, 1)

     # assign the basic information
    src_file = process_input[1] # source file
    src_type = process_input[2] # source type ("audio", "video")
    out_file = process_input[3] # output base name
    split_file = process_input[4] # flag for splitting into individual files
    keep_flag = process_input[5] # flag for keeping the temporary flies

    # assign conversion files
    meta_file = "ffmetadatfile.txt"
    batch_file = "ffmpegbatch.bat"
    if (process_input[6] != None): # metadata file name
        meta_file = process_input[6]
    if (process_input[7] != None): # batch file name
        batch_file = process_input[7] 
    
    # no quote versions for open commands
    meta_file_nq = meta_file.strip('"')
    batch_file_nq = batch_file.strip('"')

    # processing bools
    do_full = (out_file != None)
    do_audio = (src_type == "audio")
                                   
    # get source file extension and directory
    import os
    src_file_nq = src_file.strip('"') # remove surrounding double quote because os.path doesn't use
    src_filename, src_extension = os.path.splitext(src_file_nq)
    src_dir = os.path.dirname(src_file_nq)
    src_dir_nq = src_dir.strip('"')
 
    # contant strings
    chapterkey = '[CHAPTER]'
    timedef = 'TIMEBASE=1/1000'
    emptyline = ''
    ffcmd = 'ffmpeg '
    ext = src_extension # original extension is the source file
    ffopt = ' -codec copy '

    # adjust strings for audio processing
    if (do_audio == True):
        ext = '.mp3'
        ffopt = ' '

    # add or replace output extension
    if (do_full == True):
        out_file_nq = out_file.strip('"') # remove surrounding double quote because os.path doesn't use
        out_filename, out_extension = os.path.splitext(out_file_nq)
        out_file = '"' + out_filename + ext + '"' # add back surrounding double quote because ffmpeg requires

    # open the metadata file, clearing out contents if necessary
    try:
        if (do_full == True):
            cmd = ffcmd + ' -i ' + src_file + ' -f ffmetadata ' + meta_file
            os.system(cmd)
            with open(meta_file_nq, 'a') as f:
                pass

        # open the batch file, clearing out contents if necessary
        if (split_file == True):
            with open(batch_file_nq, 'w') as g:
                pass

    except Exception as e:
        print(f"An error occurred in creating conversion files: {e}")


    # process each of the timecodes in the list
    i = 1
    for (element, element_1) in zip(chapter_data, chapter_data_lead_1):

        # extract list from element and element_1
        time_code, chapter_name, hours, minutes, seconds = element
        time_code_1, chapter_name_1, hours_1, minutes_1, seconds_1 = element_1

        # start times
        startsec = seconds + minutes*60 + hours*60*60 # total seconds
        startmsec = startsec * 1000 # total milliseconds

        # end times
        endsec = seconds_1 + minutes_1*60 + hours_1*60*60 # total seconds
        endmsec = endsec * 1000 # total milliseconds
        
        # add to map file for chapter encoding
        if (do_full == True):
            title = 'TITLE=' + chapter_name
            startkey = 'START=' + str(startmsec)
            endkey = 'END=' + str(endmsec)
            try:
                with open(meta_file_nq, 'a') as f:
                    f.write(emptyline + '\n')
                    f.write(chapterkey + '\n')
                    f.write(timedef + '\n')
                    f.write(startkey + '\n')
                    f.write(endkey + '\n')
                    f.write(title + '\n')
            except Exception as e:
                print(f"An error occurred in reading conversion metadata file file: {e}")

        # add to batch file for split
        if (split_file == True):
            # make ffmpeg command where the chapter name and the source directory are used to create a filename for output
            chapter_name = chapter_name.translate({ord(i): None for i in '<>:/\\|?'}) # remove special windows file characters
            ffmpegname = '"' + src_dir_nq + '\\' + str(i).zfill(2) + ' ' + chapter_name.strip('"') + ext + '"'
            ffmpegcmd = ffcmd + ' -ss ' + str(startsec) + ' -to ' + str(endsec) + ' -i ' + src_file + ffopt + ffmpegname

            # append command to the batch flie
            try:
                with open(batch_file_nq, 'a') as g:
                    g.write(ffmpegcmd + '\n')
            except Exception as e:
                print(f"An error occurred in reading conversion batch file: {e}")

        # increment
        i = i + 1

    # take those chapter times and the created by this program and encode the original file 
    # with chapter markers
    if (do_full == True):
        baseopt = ' -i ' + meta_file + ' -map_metadata 1 '
        if (do_audio == True):
           typeopt = '-vn -acodec libmp3lame '           
        else:
           typeopt = '-c copy '
        cmd = 'ffmpeg -i ' + src_file + baseopt + typeopt + out_file
        os.system(cmd)
        
    # do splitting and cleanup batch file
    if (split_file == True):
        os.system(batch_file)
        if (keep_flag != True):
            cmd = 'del ' + batch_file
            os.system(cmd)

   # cleanup chapter metadata file
    if (do_full == True and keep_flag != True):
        cmd = 'del ' + meta_file
        os.system(cmd)




######################################################################################3333

# open the fixed file which points to the control file for this project
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

######################################################################################3333
