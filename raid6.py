from raid_code import RSCode
from array import array
from decimal import *
import os, struct, string, math

hsep = '|'
cwd = ''
test_file_dir = ''
data_prefix = 'data'
drives_prefix = 'drives'
part_drive_prefix = ''
part_drive = ''
drive_no = -1
part_no = -1
block_size = -1


def init(part_no_=6, size_=1024):
    global cwd, test_file_dir, part_drive_prefix, drive_no, part_no, part_drive, block_size
    drive_no = part_no_+2
    part_no = part_no_
    block_size = size_ * part_no_

    if drive_no > 256 or part_no <= 0:
        raise Exception, 'Invalid (drive_no,part_no), need 0 < part_no < drive_no < 257.'

    cwd = os.getcwd()
    # setup folder paths
    test_file_dir = os.path.join(cwd, data_prefix)
    part_drive_prefix = os.path.join(cwd, drives_prefix, "drive_")
    part_drive = [str]*drive_no
    # setup drive folder paths and create the drive folders if necessary
    for i in range(drive_no):
        part_drive[i] = part_drive_prefix + repr(i)
        if not os.path.exists(part_drive[i]):
            os.makedirs(part_drive[i])


def get_file_size(fname):
    return os.stat(fname)[6]


def make_header(fname, size, drive_no, part_no, block_size):
    global hsep
    return string.join(['RS_PARITY_PIECE_HEADER', 'FILE', fname,
                        'drive_no', `drive_no`, 'part_no', `part_no`, 'size', `size`, 'block_size', `block_size`, 'piece'],
                       hsep) + hsep


def parse_header(header):
    global hsep
    return string.split(header, hsep)


def read_encode_and_write_block(read_size, in_file, out_files, code):
    global part_no
    buffer = array('B')
    buffer.fromfile(in_file, read_size)

    for i in range(read_size, code.k): # if read_size is lesser than code_en.k
        buffer.append(0)

    code_vec = code.encode(buffer)
    for j in range(code.n):
        out_files[j].write(struct.pack('B', code_vec[j]))


def encode_file(fname):
    global drive_no, part_no, part_drive, block_size
    in_file_name = os.path.join(test_file_dir, fname)

    in_file = open(in_file_name, 'rb')
    in_size = get_file_size(in_file_name)
    header = make_header(fname, in_size, drive_no, part_no, block_size)

    code = RSCode(drive_no,part_no,8)

    for i in range(int( math.ceil( float(in_size) / block_size) )):
        out_files = [file]*drive_no     # out_files[0~part_no-1]: partitions, out_files[part_no~drive_no-1]: parities

        index = 6 - i%(drive_no-1)      # parity block index
        for j in range( index ):
            out_file_name = os.path.join(part_drive[j], fname) + '.pt' + `i`
            out_files[j] = open(out_file_name, 'wb')
            out_files[j].write(header + `j` + '\n')

        out_files[part_no] = open(os.path.join(part_drive[index], fname) + '.p' + `i`, 'wb')
        out_files[part_no].write(header + 'p' + `i` + '\n')
        index += 1
        out_files[part_no+1] = open(os.path.join(part_drive[index], fname) + '.q' + `i`, 'wb')
        out_files[part_no+1].write(header + 'q' + `i` + '\n')
        index += 1

        for j in range(index, drive_no):
            out_file_name = os.path.join(part_drive[j], fname) + '.pt' + `i`
            out_files[j-2] = open(out_file_name, 'wb')
            out_files[j-2].write(header + `(j-2)` + '\n')

        if i < in_size / block_size:
            file_size = block_size
        else:
            file_size = in_size % block_size

        for j in range(0, (file_size / part_no) * part_no, part_no):
            read_encode_and_write_block(part_no, in_file, out_files, code)

        if file_size % part_no > 0:
            read_encode_and_write_block(file_size % part_no, in_file, out_files, code)

        for j in range(drive_no):
            out_files[j].close()


def get_block_info(fnames,headers):
    l = [array]*len(fnames)
    piece_nums = [int]*len(fnames)
    for i in range(len(fnames)):
        l[i] = parse_header(headers[i])
    for i in range(len(fnames)):
        if (l[i][0] != 'RS_PARITY_PIECE_HEADER' or
                    l[i][2] != l[0][2] or l[i][4] != l[0][4] or
                    l[i][6] != l[0][6] or l[i][8] != l[0][8]):
            raise Exception, 'File ' + `fnames[i]` + ' has incorrect header.'
        piece_nums[i] = int(l[i][10])
    (n, k, size) = (int(l[0][4]),int(l[0][6]),long(l[0][8]))
    if len(piece_nums) < k:
        raise Exception, ('Not enough parity for decoding; needed '
                          + `l[0][6]` + ' got ' + `len(fnames)` + '.')
    return n,k,size,piece_nums


def read_decode_and_write_block(write_size, in_files, out_file, code, missed_blocks, missed_list):
    buffer = array('B')
    for j in range(code.k):
        buffer.fromfile(in_files[j],1)
    result = code.decode(buffer.tolist())
    for j in range(write_size):
        out_file.write(struct.pack('B',result[j]))

    if len(missed_list) > 0:
        code_vec = code.encode(result)
        for j in range(len(missed_list)):
            missed_blocks[j].write(struct.pack('B', code_vec[missed_list[j]]))

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
def get_code_info(drives):
    for i in range(len(drives)):
        listfiles = os.listdir(drives[i])
        for j in range(len(listfiles)):
            file_path = os.path.join(drives[i], listfiles[j])
            if os.path.isfile(file_path):
                file = open(file_path, 'rb')
                header = file.readline()
                paras = parse_header(header)
                file.close()
                return int(paras[4]), int(paras[6]), int(long(paras[8])), int(long(paras[10]))


def get_uncorrupted_blocks(fname, drives, drive_no, part_no, block_no):
    block_file_list = [None]*len(drives)
    dec_list = [None]*len(drives)
    missed_list = range(drive_no)
    un_corrupted_count = 0
    for j in range(len(drives)):
        # flexible way to find the files, it only depends on what was wrote in header file
        part_file_name  = os.path.join(drives[j], fname) + '.pt' + `block_no`
        xor_parity_name = os.path.join(drives[j], fname) + '.p' + `block_no`
        rs_parity_name  = os.path.join(drives[j], fname) + '.q' + `block_no`
        if os.path.exists(part_file_name):
            file_name =  part_file_name
        elif os.path.exists(xor_parity_name):
            file_name = xor_parity_name
        elif os.path.exists(rs_parity_name):
            file_name = rs_parity_name
        else:
            continue

        block_file = open(file_name, 'rb')
        header = block_file.readline()
        partition_number = parse_header(header)[12][0]
        block_file_list[un_corrupted_count] = block_file
        if partition_number == 'p':
            dec_list[un_corrupted_count] = part_no
        elif partition_number == 'q':
            dec_list[un_corrupted_count] = part_no+1
        else:
            dec_list[un_corrupted_count] = int(partition_number)
        missed_list.remove(dec_list[un_corrupted_count])
        un_corrupted_count += 1

    if len(block_file_list) < part_no:
        print 'unable to recovery part: ' + `block_no+1` + ', too much blocks are missing'
        return -1
    else:
        print 'found uncorrupted block:'
        list = '    '
        for s in range(len(dec_list)):
            if dec_list[s] < part_no:
                list += `dec_list[s]`
            elif dec_list[s] == part_no:
                list += 'p'
            else:
                list += 'q'
            list += ', '
        print list

    return block_file_list[0:un_corrupted_count], dec_list[0:un_corrupted_count], missed_list


# rebuild the failure drives, assuming the drives are drive_0, drive_1, drive_2, .... drive_(drive_no) previously
def detect_rebuild_drives(drives, drive_no):
    recovered_drives = [None]*(drive_no-len(drives))
    missing_drives = range(drive_no)
    for i in range(len(drives)):
        number = int(drives[i][len(drives[i])-1])
        missing_drives.remove(number)
    assert len(missing_drives) == drive_no-len(drives)
    print 'missing drive: ' + `missing_drives`

    print 'create replacement storage node'
    drive_mapper = range(drive_no)
    if len(missing_drives) > 0:
        for i in range(len(missing_drives)):
            recovered_drives[i] = os.path.join(os.getcwd(), drives_prefix, "drive_") + `drive_no+i`
            os.makedirs(recovered_drives[i])
            drive_mapper[missing_drives[i]] = drive_no+i
    return recovered_drives, missing_drives, drive_mapper


# initialize files to be recovered
def create_recover_blocks(fname, missed_part_no, block_index, drive_mapper, parity_index, header):
    if missed_part_no < part_no:    # it is one of the partitions
        drive_index = missed_part_no if missed_part_no < parity_index else missed_part_no + 2
        block = open(os.path.join(os.getcwd(), drives_prefix, "drive_"+`drive_mapper[drive_index]`, fname) + '.pt' + `block_index`, 'wb')
        block.write(header + `missed_part_no` + '\n')
    elif missed_part_no == part_no: # p partition
        drive_index = parity_index
        block = open(os.path.join(os.getcwd(), drives_prefix, "drive_"+`drive_mapper[drive_index]`, fname) + '.p' + `block_index`, 'wb')
        block.write(header + 'p' + `block_index` + '\n')
    else:                           # q partition
        drive_index = parity_index + 1
        block = open(os.path.join(os.getcwd(), drives_prefix, "drive_"+`drive_mapper[drive_index]`, fname) + '.q' + `block_index`, 'wb')
        block.write(header + '1' + `block_index` + '\n')
    return block


def decode_file(fname, out_name):
    out_file = open(os.path.join(os.getcwd(), data_prefix, out_name), 'wb')

    drives = get_drives()
    (drive_no, part_no, file_size, block_size) = get_code_info(drives)
    (recovered_drives, missing_drives, drive_mapper) = detect_rebuild_drives(drives, drive_no)

    # generate the code
    code = RSCode(drive_no, part_no, 8)
    # start to decode
    recovered_size = 0
    i = 0
    while recovered_size < file_size:
        print 'trying to recover part ' + `i+1` + ' of ' + `int( math.ceil( float(file_size)/block_size) )` + '...'
        (block_file_list, dec_list, missed_list) = get_uncorrupted_blocks(fname, drives, drive_no, part_no, i)
        code.prepare_decoder(dec_list[0:min(len(dec_list), part_no)])

        # initialize files to be recovered
        missed_blocks = [None]*(len(missed_list))
        index = 6 - i % (drive_no - 1)      # parity block index, used to determine the drive index
        for j in range(len(missed_list)):
            header = make_header(fname, file_size, drive_no, part_no, block_size)
            missed_blocks[j] = create_recover_blocks(fname, missed_list[j], i, drive_mapper, index, header)

        # decode and write to out_file
        if recovered_size + block_size <= file_size:
            decode_size = block_size
        else:
            decode_size = file_size % block_size

        for j in range(0, (decode_size / part_no) * part_no, part_no):
            read_decode_and_write_block(part_no, block_file_list[0:min(len(dec_list), part_no)], out_file, code,
                                        missed_blocks, missed_list)
        if decode_size % part_no > 0:
            read_decode_and_write_block(decode_size % part_no, block_file_list[0:min(len(dec_list), part_no)], out_file, code,
                                        missed_blocks, missed_list)

        i += 1
        recovered_size += block_size
        for j in range(len(missed_list)):
            missed_blocks[j].close()

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