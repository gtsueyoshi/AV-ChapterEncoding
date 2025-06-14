
# read the process control file
def parse_control_file(cmd_file, allowed_keys):
    """
    parse the chapter tag command flie

    syntax for each line:

    . leading "#" is a comment line

    . [key] = [arg]

        where key = { "time", "source", "type", "output" } and
            : chapters [arg] is the name of the timecode file with lines of the form "hh:mm:ss {chaptername}
            : source [arg] is the original audio or video source file
            : srctype [arg] is { "audio", "video" } for encoding
            : output [arg] is the name of the base of the output flie
            : metaname [arg] is the optional name of the metadata temp file
            : batchname [arg] is the optional name of the ffmpet split batch file

    . "split" is provided if you wish to split the output into individual chapter files
    . "keep" is provided if you wish to keep the metadata file and the batch file

    """

    # initialize the input data dictionary
    input_data = {}

    # remove surrounding quotes because open doesn't like
    cmd_file_nq = cmd_file.strip('"').strip("'")
    try:
         with open(cmd_file_nq, 'r') as file:
            for line in file:
                 # remove leading and trailing whitespace
                line = line.strip()

                # skip empty or comment line
                if (line == '' or line[0] == "#" or line[0:1] == "//"):
                    continue
    
                # process the line with '='
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if allowed_keys is None or key in allowed_keys:
                        input_data[key] = value # dictionary style key=value pair
                
                # process the line without '='
                else:
                    line.strip().lower()
                    if allowed_keys is None or line in allowed_keys:
                        input_data[line] = True  # flag-style keyword

    except FileNotFoundError:
        print(f"Error: File not found at {cmd_file}")

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
         timecode_file_nq = timecode_file.strip('"').strip("'") # remove surrounding quotes because open doesn't like
         with open(timecode_file_nq, 'r') as file:
            for line in file:
                # Split the line by a delimiter (e.g., space, tab, etc.)
                parts = line.strip().split()

                # Check if the line has at least one part (time code)
                if len(parts) >= 1:
                    time_code = parts[0]  # First part is the time code

                    hours, minutes, seconds = map(int, time_code.split(':')) # split time code into h, m, s

                    string_data = ' '.join(parts[1:]) # Join the rest of the parts into a string
                    time_data.append((time_code, string_data, hours, minutes, seconds)) # add entry to list

    except FileNotFoundError:
        print(f"Error: File not found at {timecode_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

    return time_data


# cut source file into chapters
def process_chapters(cmdfile):
    """
    wrapper to first parse the control file and information on allowed keys
    and to create a parsed control dictionary, and then to process the chapter information 
    using the parsed control dictionary and the allowed keys

    Args:
        cmdfile: the command file that contains the process command

    """

    # allowed keys in the control file
    allowed_keys = ["chapters", "source", "srctype", "output", "split", "keep", "metaname", "batchname"]

    # parse the control file and return processing input dictionary
    process_input = parse_control_file(cmdfile, allowed_keys)
    control_values = [process_input.get(key, None) for key in allowed_keys]

    # process the chapter information
    do_chapters(control_values)


# process the chapter information
def do_chapters(control_values):
    
    """
    add chapter markers or cut video or audio source file into chapters using ffmpeg
    and the ordered list of control values

    Args:
        control_values: the ordered list of values from the process input dictionary
 
    The control values are expected to be in the following order:

    control_values = [ chapter_file, src_file, src_type, out_file, split_file, keep_flag, meta_file, batch_file ]

    where:  
        1. chapter_file: the name of the timecode file with lines of the form "hh:mm:ss {chaptername}"
        2. src_file: the original audio or video source file
        3. src_type: { "audio", "video" } for encoding
        4. out_file: the name of the base of the output file
        5. split_file: True if you wish to split the output into individual chapter files
        6. keep_flag: True if you wish to keep the metadata file and the batch file
        7. meta_file: optional name of the metadata temp file
        8. batch_file: optional name of the ffmpeg split batch file

    """
        
    # unpack the process input dictionary
    if len(control_values) != 8:
        print("Error: Invalid number of control values. Expected 8 values.")
        return 
    chapter_file, src_file, src_type, out_file, split_file, keep_flag, meta_file, batch_file = control_values

    # processing bools
    do_full = (out_file != None)
    do_audio = (src_type == "audio")
 
    # get chapter file name for open
    chapter_file_nq = chapter_file.strip('"').strip("'") # remove surrounding quotes because open doesn't like
                                  
    # read the chapter data from the timecode file
    chapter_data = read_timecode_data(chapter_file_nq)
    if (len(chapter_data) == 0):
        print(f"Error: No chapter data found in {chapter_file}")
        return
    
    # create lag of chapter time lists
    import itertools
    chapter_data_lead_1 = itertools.islice(chapter_data, 1, None, 1)

    # get source file extension and directory
    import os
    src_file_nq = src_file.strip('"').strip("'") # remove surrounding quotes because os.path doesn't use
    src_filename, src_extension = os.path.splitext(src_file_nq)
    src_dir = os.path.dirname(src_file_nq)
    src_dir_nq = src_dir.strip('"').strip("'") # remove surrounding quotes
 
    # contant strings
    ffcmd = 'ffmpeg'
    chapterkey = '[CHAPTER]'
    timedef = 'TIMEBASE=1/1000'
    emptyline = ''
    ext = src_extension # original extension is the source file
    ffopt = ' -codec copy '

    # adjust strings for audio processing
    if (do_audio == True):
        ext = '.mp3'
        ffopt = ' '

    # add or replace output extension
    if (do_full == True):
        # update the output file name to have the correct extension
        out_file_nq = out_file.strip('"') # remove surrounding quotes because os.path doesn't use
        out_filename, out_extension = os.path.splitext(out_file_nq)
        out_file = '"' + out_filename + ext + '"' # add back surrounding quotes because ffmpeg requires

        # update the metafile name
        if (meta_file == None): # metadata file name
            meta_file = "ffmetadatafile.txt"
 
        # use ffmpeg to create the metadata file and open for appending
        meta_file_nq = meta_file.strip('"').strip("'") # no quote versions for open commands
        cmd = ffcmd + ' -i ' + src_file + ' -f ffmetadata ' + meta_file
        os.system(cmd)
        with open(meta_file_nq, 'a') as f:
            pass

    # open the batch file, clearing out contents if necessary
    if (split_file == True):

        # update the batch file name
        if (batch_file == None): # batch file name
            batch_file = "ffbatchfile.bat"
        
        # open the batch file for writing
        batch_file_nq = batch_file.strip('"').strip("'")  # no quote versions for open commands
        with open(batch_file_nq, 'w') as g:
            pass

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
            with open(meta_file_nq, 'a') as f:
                f.write(emptyline + '\n')
                f.write(chapterkey + '\n')
                f.write(timedef + '\n')
                f.write(startkey + '\n')
                f.write(endkey + '\n')
                f.write(title + '\n')
 
        # add to batch file for split
        if (split_file == True):
            # make ffmpeg command where the chapter name and the source directory are used to create a filename for output
            chapter_name = chapter_name.translate({ord(j): None for j in '<>:/\\|?'}) # remove special windows file characters
            ffmpegname = '"' + src_dir_nq + '\\' + str(i).zfill(2) + ' ' + chapter_name.strip('"') + ext + '"'
            ffmpegcmd = ffcmd + ' -ss ' + str(startsec) + ' -to ' + str(endsec) + ' -i ' + src_file + ffopt + ffmpegname

            # append command to the batch flie
            with open(batch_file_nq, 'a') as g:
                g.write(ffmpegcmd + '\n')

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
        if (keep_flag != True):
            cmd = 'del ' + meta_file
            os.system(cmd)

    # do splitting and cleanup batch file
    if (split_file == True):
        os.system(batch_file)
        if (keep_flag != True):
            cmd = 'del ' + batch_file
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


# process the video/audio file chapter information
process_chapters(procinput)



######################################################################################3333
