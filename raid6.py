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


def make_header(fname, size):
    global hsep, drive_no, part_no, block_size
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
    header = make_header(fname, in_size)

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


def read_decode_and_write_block(write_size, in_files, out_file, code):
    buffer = array('B')
    for j in range(code.k):
        buffer.fromfile(in_files[j],1)
    result = code.decode(buffer.tolist())
    for j in range(write_size):
        out_file.write(struct.pack('B',result[j]))


def decode_file(fname, out_name):
    out_file = open(os.path.join(os.getcwd(), data_prefix, out_name), 'wb')

    # scan for drives
    drives = [None]*256
    drives_count = 0
    listdir = os.listdir(os.path.join(os.getcwd(), drives_prefix))
    for i in range(len(listdir)):
        drive_path = os.path.join(os.getcwd(), drives_prefix, listdir[i])
        if os.path.isdir(drive_path):
            drives[drives_count] = drive_path
            drives_count += 1

    n = 256
    k = 256
    file_size = Decimal('Infinity')
    recovered_size = 0
    block_size = -1
    code = None

    i = 0
    while recovered_size < file_size:
        block_file_list = [None]*drives_count
        dec_list = [None]*drives_count
        un_corrupted_count = 0
        for j in range(drives_count):
            # flexible way to find the files, it only depends on what was wrote in header file
            part_file_name  = os.path.join(drives[j], fname) + '.pt' + `i`
            xor_parity_name = os.path.join(drives[j], fname) + '.p' + `i`
            rs_parity_name  = os.path.join(drives[j], fname) + '.q' + `i`
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

            if n == 256: # first time reading a block, setup the parameters
                paras = parse_header(header)
                n = int(paras[4])
                k = int(paras[6])
                file_size = int(paras[8])
                block_size = int(paras[10])
                code = RSCode(n, k, 8)

            partition_number = parse_header(header)[12][0]
            block_file_list[un_corrupted_count] = block_file
            if partition_number == 'p':
                dec_list[un_corrupted_count] = k
            elif partition_number == 'q':
                dec_list[un_corrupted_count] = k+1
            else:
                dec_list[un_corrupted_count] = int(partition_number)
            un_corrupted_count += 1

        code.prepare_decoder(dec_list[0:min(un_corrupted_count, k)])

        # decode and write to out_file
        if recovered_size + block_size <= file_size:
            decode_size = block_size
        else:
            decode_size = file_size % block_size

        for j in range(0, (decode_size / k) * k, k):
            read_decode_and_write_block(k, block_file_list, out_file, code)

        if decode_size % k > 0:
            read_decode_and_write_block(decode_size % k, block_file_list, out_file, code)

        i+= 1
        recovered_size += block_size

def test(original_name, recovered_name):
    original = open(os.path.join(os.getcwd(), data_prefix, original_name), 'rb')
    recovered = open(os.path.join(os.getcwd(), data_prefix, recovered_name), 'rb')
    match =  original.read() == recovered.read()
    return match