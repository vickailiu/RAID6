# this is for testing the original script
# import file_ecc, os

# from rs_code import RSCode
# from array import array
#
# n = 8
# k = 6
# code = RSCode(n,k,8,shouldUseLUT=-(k!=1))
# decode = RSCode(n,k,8)
#
#
# testFile = os.path.join(os.getcwd(), 'data', 'ls')
# prefix = os.path.join(os.getcwd(), 'data', 'ls_backup')
# names = file_ecc.EncodeFile(testFile,prefix,8,6)
#
# decList = map(lambda x: prefix + '.p_' + `x`,[0,1,3,2,6,7])
#
# decodedFile = os.path.join(os.getcwd(), 'data', 'ls.r')
# file_ecc.DecodeFiles(decList,decodedFile)
# fd1 = open(testFile,'rb')
# fd2 = open(decodedFile,'rb')
# fd1.read() == fd2.read()

import raid6

# raid6.init(6, 3*256)
#
# raid6.encode_file('RAID.png')
raid6.decode_file('RAID.png', 'RAID.png.r')
print raid6.test('RAID.png', 'RAID.png.r')