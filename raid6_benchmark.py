import random

import raid6
import time
import shutil
import os

file = open("decoding_time_0_failure.txt", "w")

for n in [6, 7, 8, 9, 10]:
    for r in [2, 3, 4, 5, 6]:
        cumulative_time = 0.0
        counter = 0
        for i in range(0,100):
            raid6.encode_file('RAID.png', n, r, 3*256)
            # n1 = random.randint(0,n+r-1)
            # s = (n+r) / 2
            # n2 = ( n1 + s ) % (n+r-1)
            # shutil.rmtree(os.path.join("drives/drive_" + str(n1)))
            # shutil.rmtree(os.path.join("drives/drive_" + str(n2)))
            start_time = time.time()
            raid6.decode_file('RAID.png', 'RAID_r.png')
            if raid6.test('RAID.png', 'RAID_r.png') == True:
                cumulative_time = cumulative_time + time.time() - start_time
                counter = counter + 1
            shutil.rmtree('drives')
            os.makedirs('drives')
        file.write("{0} + {1} : {2} seconds\n".format(n, r, (cumulative_time/counter)))

file.close()

# raid6.decode_file('RAID.png', 'RAID_r.png')
# print raid6.test('RAID.png', 'RAID_r.png')
