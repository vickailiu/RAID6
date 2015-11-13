from raid_code import RSCode
from array import array
import os, struct, string, math

hsep = '|'
test_file_dir = ''
data_prefix = 'data'
drives_prefix = 'drives'
drive_prefix = ''
drives = ''
drive_count = -1
part_count = -1
block_size = -1


def init(part_no_=6, size_=1024):
    global test_file_dir, drive_prefix, drive_count, part_count, drives, block_size
    drive_count = part_no_ + 2
    part_count = part_no_
    block_size = size_ * part_no_

    if drive_count > 256 or part_count <= 0:
        raise Exception, 'Invalid (drive_count,part_count), need 0 < part_count < drive_count < 257.'

    # setup folder paths
    test_file_dir = os.path.join(os.getcwd(), data_prefix)
    drive_prefix = os.path.join(os.getcwd(), drives_prefix, "drive_")
    drives = [str]*drive_count
    # setup drive folder paths and create the drive folders if necessary
    for i in range(drive_count):
        drives[i] = drive_prefix + repr(i)
        if not os.path.exists(drives[i]):
            os.makedirs(drives[i])


def get_file_size(fname):
    return os.stat(fname)[6]


def make_header(fname, size, drive_count, part_count, block_size):
    global hsep
    return string.join(['RS_PARITY_PIECE_HEADER', 'FILE', fname,
                        'drive_no', `drive_count`, 'part_no', `part_count`,
                        'size', `size`, 'block_size', `block_size`,
                        'piece'],
                       hsep) + hsep


def parse_header(header):
    global hsep
    return string.split(header, hsep)


def read_encode_and_write_block(read_size, in_file, out_files, code):
    buffer = array('B')
    buffer.fromfile(in_file, read_size)

    for i in range(read_size, code.k): # if read_size is lesser than code_en.k
        buffer.append(0)

    code_vec = code.encode(buffer)
    for j in range(code.n):
        out_files[j].write(struct.pack('B', code_vec[j]))


def encode_file(fname):
    global drive_count, part_count, drives, block_size
    in_file_name = os.path.join(test_file_dir, fname)

    in_file = open(in_file_name, 'rb')
    in_size = get_file_size(in_file_name)
    header = make_header(fname, in_size, drive_count, part_count, block_size)

    code = RSCode(drive_count, part_count,8)

    for i in range(int( math.ceil( float(in_size) / block_size) )):
        out_parts = [file]*drive_count     # out_files[0~part_no-1]: partitions, out_files[part_no~drive_no-1]: parities

        parity_index = 6 - i%(drive_count-1)      # parity block index
        for j in range( parity_index ):
            out_part_name = os.path.join(drives[j], fname) + '.pt' + `i`
            out_parts[j] = open(out_part_name, 'wb')
            out_parts[j].write(header + `j` + '\n')

        out_parts[part_count] = open(os.path.join(drives[parity_index], fname) + '.p' + `i`, 'wb')
        out_parts[part_count].write(header + 'p' + `i` + '\n')
        parity_index += 1
        out_parts[part_count+1] = open(os.path.join(drives[parity_index], fname) + '.q' + `i`, 'wb')
        out_parts[part_count+1].write(header + 'q' + `i` + '\n')
        parity_index += 1

        for j in range(parity_index, drive_count):
            out_part_name = os.path.join(drives[j], fname) + '.pt' + `i`
            out_parts[j-2] = open(out_part_name, 'wb')
            out_parts[j-2].write(header + `(j-2)` + '\n')

        # calculate current block size
        if i < in_size / block_size:
            file_size = block_size
        else:
            file_size = in_size % block_size

        # encode file by field with field size == part_count
        for j in range(0, (file_size / part_count) * part_count, part_count):
            read_encode_and_write_block(part_count, in_file, out_parts, code)
        if file_size % part_count > 0:
            read_encode_and_write_block(file_size % part_count, in_file, out_parts, code)

        for j in range(drive_count):
            out_parts[j].close()

    print 'done!'


def read_decode_and_write_block(write_size, in_parts, out_file, code, missed_parts, missed_list):
    buffer = array('B')
    for i in range(code.k):
        buffer.fromfile(in_parts[i],1)
    result = code.decode(buffer.tolist())
    for i in range(write_size):
        out_file.write(struct.pack('B',result[i]))

    if len(missed_list) > 0:
        code_vec = code.encode(result)
        for i in range(len(missed_list)):
            missed_parts[i].write(struct.pack('B', code_vec[missed_list[i]]))


# scan for drives
def get_drives():
    drives = [None]*256
    drives_count = 0
    listdir = os.listdir(os.path.join(os.getcwd(), drives_prefix))
    for i in range(len(listdir)):
        drive_path = os.path.join(os.getcwd(), drives_prefix, listdir[i])
        if os.path.isdir(drive_path):
            drives[drives_count] = drive_path
            drives_count += 1

    print 'Storage nodes available:'
    for i in range(drives_count):
        print '    ' + os.path.relpath(drives[i])
    print ''
    print ''
    return drives[0:drives_count]


# try get the infos from one of the available files
def get_code_info(drives, fname):
    for i in range(len(drives)):
        listfiles = os.listdir(drives[i])
        for j in range(len(listfiles)):
            if listfiles[j].find(fname + '.') == 0:                 # find fname's parts
                file_path = os.path.join(drives[i], listfiles[j])
                if os.path.isfile(file_path):
                    file = open(file_path, 'rb')
                    header = file.readline()
                    paras = parse_header(header)
                    file.close()
                    return int(paras[4]), int(paras[6]), int(long(paras[8])), int(long(paras[10]))
    assert False


def get_uncorrupted_parts(fname, drives, drive_count, part_count, block_no):
    part_list = [None]*len(drives)
    dec_list = [None]*len(drives)
    missed_list = range(drive_count)
    un_corrupted_count = 0
    for i in range(len(drives)):
        # flexible way to find the files, it only depends on what was wrote in header file
        part_file_name  = os.path.join(drives[i], fname) + '.pt' + `block_no`
        xor_parity_name = os.path.join(drives[i], fname) + '.p' + `block_no`
        rs_parity_name  = os.path.join(drives[i], fname) + '.q' + `block_no`
        if os.path.exists(part_file_name):
            part_name =  part_file_name
        elif os.path.exists(xor_parity_name):
            part_name = xor_parity_name
        elif os.path.exists(rs_parity_name):
            part_name = rs_parity_name
        else:
            continue

        part_file = open(part_name, 'rb')
        header = part_file.readline()
        part_index = parse_header(header)[12][0]       # part_index is the index describing whether the part is a #
                                                       # partition or parity
        part_list[un_corrupted_count] = part_file
        if part_index == 'p':
            dec_list[un_corrupted_count] = part_count
        elif part_index == 'q':
            dec_list[un_corrupted_count] = part_count+1
        else:
            dec_list[un_corrupted_count] = int(part_index)
        missed_list.remove(dec_list[un_corrupted_count])
        un_corrupted_count += 1

    if len(part_list) < part_count:
        print 'unable to recovery part: ' + `block_no+1` + ', too many parts are missing'
        return -1
    else:
        print 'found uncorrupted parts:'
        list = '    '
        for s in range(len(dec_list)):
            if dec_list[s] < part_count:
                list += `dec_list[s]`
            elif dec_list[s] == part_count:
                list += 'p'
            else:
                list += 'q'
            list += ', '
        print list

    return part_list[0:un_corrupted_count], dec_list[0:un_corrupted_count], missed_list


# rebuild the failure drives, assuming the drives are drive_0, drive_1, drive_2, .... drive_{drive_count-1} previously
# then create replacement drives: drive_{drive_count}, drive_{drive_count+1}
def detect_and_rebuild_drives(drives, drive_count):
    recovered_drives = [None]*(drive_count-len(drives))
    missing_drives = range(drive_count)
    for i in range(len(drives)):
        number = int(drives[i][len(drives[i])-1])
        missing_drives.remove(number)
    assert len(missing_drives) == drive_count-len(drives)
    print 'missing drive: ' + `missing_drives`

    print 'create replacement storage node'
    drive_mapper = range(drive_count)
    if len(missing_drives) > 0:
        for i in range(len(missing_drives)):
            recovered_drives[i] = os.path.join(os.getcwd(), drives_prefix, "drive_") + `drive_count+i`
            os.makedirs(recovered_drives[i])
            drive_mapper[missing_drives[i]] = drive_count+i
    print 'done!'
    print ''
    print ''
    return recovered_drives, missing_drives, drive_mapper


# initialize files to be recovered
def create_recover_parts(fname, missed_part_no, part_count, block_index, drive_mapper, parity_index, header):
    if missed_part_no < part_count:    # it is one of the partitions
        drive_index = missed_part_no if missed_part_no < parity_index else missed_part_no + 2
        part = open(os.path.join(os.getcwd(), drives_prefix, "drive_"+`drive_mapper[drive_index]`, fname) + '.pt' + `block_index`, 'wb')
        part.write(header + `missed_part_no` + '\n')
    elif missed_part_no == part_count: # p partition
        drive_index = parity_index
        part = open(os.path.join(os.getcwd(), drives_prefix, "drive_"+`drive_mapper[drive_index]`, fname) + '.p' + `block_index`, 'wb')
        part.write(header + 'p' + `block_index` + '\n')
    else:                           # q partition
        drive_index = parity_index + 1
        part = open(os.path.join(os.getcwd(), drives_prefix, "drive_"+`drive_mapper[drive_index]`, fname) + '.q' + `block_index`, 'wb')
        part.write(header + '1' + `block_index` + '\n')
    return part


def decode_file(fname, out_name):
    out_file = open(os.path.join(os.getcwd(), data_prefix, out_name), 'wb')

    drives = get_drives()
    (drive_count, part_count, file_size, block_size) = get_code_info(drives, fname)
    (recovered_drives, missing_drives, drive_mapper) = detect_and_rebuild_drives(drives, drive_count)

    # generate the code
    code = RSCode(drive_count, part_count, 8)
    # start to decode
    recovered_size = 0
    i = 0
    while recovered_size < file_size:
        print 'trying to recover part ' + `i+1` + ' of ' + `int( math.ceil( float(file_size)/block_size) )` + '...'
        (block_file_list, dec_list, missed_list) = get_uncorrupted_parts(fname, drives, drive_count, part_count, i)
        code.prepare_decoder(dec_list[0:min(len(dec_list), part_count)])

        # initialize files to be recovered
        missed_parts= [None]*(len(missed_list))
        index = 6 - i % (drive_count - 1)      # parity block index, used to determine the drive index
        for j in range(len(missed_list)):
            header = make_header(fname, file_size, drive_count, part_count, block_size)
            missed_parts[j] = create_recover_parts(fname, missed_list[j], part_count, i, drive_mapper, index, header)

        # decode and write to out_file
        if recovered_size + block_size <= file_size:
            decode_size = block_size
        else:
            decode_size = file_size % block_size

        for j in range(0, (decode_size / part_count) * part_count, part_count):
            read_decode_and_write_block(part_count, block_file_list[0:min(len(dec_list), part_count)], out_file, code,
                                        missed_parts, missed_list)
        if decode_size % part_count > 0:
            read_decode_and_write_block(decode_size % part_count, block_file_list[0:min(len(dec_list), part_count)], out_file, code,
                                        missed_parts, missed_list)

        for j in range(len(missed_list)):
            missed_parts[j].close()
        i += 1
        recovered_size += block_size
        print 'done!'
        print ''

    if len(missing_drives) > 0:
        var = raw_input("Do you want to rename the replacement storage back to failed storage name? (Y/N): ")
        if (var == 'Y'):
            for i in range(len(missing_drives)):
                os.rename(recovered_drives[i], os.path.join(os.getcwd(), drives_prefix, "drive_") + `missing_drives[i]`)
            print "done!"

    return 0


def test(original_name, recovered_name):
    original = open(os.path.join(os.getcwd(), data_prefix, original_name), 'rb')
    recovered = open(os.path.join(os.getcwd(), data_prefix, recovered_name), 'rb')
    match =  original.read() == recovered.read()
    return match