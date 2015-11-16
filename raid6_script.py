import raid6

raid6.encode_file('RAID.png', 6, 2, 3*256)

raid6.decode_file('RAID.png', 'RAID_r.png')
print raid6.test('RAID.png', 'RAID_r.png')
