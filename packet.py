# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import time
import struct


class Short_Comanda_KU:
    def __init__(self, type_ku, cod_ku, num_param=0, fmt_ku='HHIH'):
        self.pack = 2
        self.num_param = num_param
        self.type_ku = type_ku
        self.cod_ku = cod_ku
        self.fmt_ku = fmt_ku
        self.mess_ku = self.pack_pk(self.fmt_ku, self.pack, self.type_ku, self.cod_ku, self.num_param)
        self.size_ku = struct.calcsize('q' + self.fmt_ku)
        self.key = {1: 'B', 2: 'b', 3: 'H', 4: 'h', 5: 'I'}

    @staticmethod
    def pack_pk(fmt_pk='h', *data_pk):
        mess_pk = b''
        for ii in range(len(fmt_pk)):
            mess_pk += struct.pack('<' + fmt_pk[ii], data_pk[ii])
        return mess_pk

    def message(self):
        tt_time = int(time.time_ns() / 100)
        return self.pack_pk('H', self.size_ku) + self.pack_pk('Q', tt_time) + self.mess_ku

    def set_ustavka(self, zn_ust, type_param=5):
        # type_param most be '5' - dword, '4' - word sign, '3' - word
        self.size_ku = struct.calcsize('Q' + self.fmt_ku + 'H' + self.key[type_param])
        return self.message() + self.pack_pk('H' + self.key[type_param], type_param, zn_ust)


class Atm_Packet:
    def __init__(self):
        self.data_packet = b''
        self.mft_atm = '<HQHH'
        self.mft_qvit = '<HQHHHH'
        self.mft_param = '<HHB'
        self.len_atm = struct.calcsize(self.mft_atm)
        self.len_data_packet = len(self.data_packet)
        self.len_param = struct.calcsize(self.mft_param)
        self.branch = {1: '<B', 2: '<H', 4: '<i', 8: '<d'}
        self.data_packet = b''
        self.len_data_packet = len(self.data_packet)

    def update_dt_packet(self, data1):
        self.data_packet = data1
        self.len_data_packet = len(self.data_packet)

    def ansver_packet(self):
        bb1 = []
        packet = struct.unpack(self.mft_atm, self.data_packet[:self.len_atm])
        if packet[2] == 1:
            bb1.append(struct.unpack(self.mft_qvit, self.data_packet))
            return bb1

        if packet[2] == 4:
            start_pack = self.len_atm
            end_pack = self.len_atm + self.len_param
            for ii in range(packet[3]):
                par1 = struct.unpack(self.mft_param, self.data_packet[start_pack:end_pack])
                delta = struct.calcsize(self.branch[par1[2]])
                start_pack = end_pack + delta
                bb1.append(par1 + struct.unpack(self.branch[par1[2]], self.data_packet[end_pack:start_pack]))
                end_pack += delta + self.len_param
        return bb1

def komm (list_komm):
    j, k, m, p = list_komm
    return struct.pack('<HHIH', j, k, m, p)

def mess (data):
    tt = int(time.time_ns() / 100)
    return struct.pack('<H', struct.calcsize('Q')+len(data)) + struct.pack('<Q', tt) + data

def set_ust(data, zn_ust, key, value):
    return data + struct.pack('<H' + value, key, zn_ust)


if __name__ == '__main__':
    km_vklbiab = Short_Comanda_KU(7, 1)
    #km_otklbiab = Short_Comanda_KU(7, 2)
    #km_podkl_izd = Short_Comanda_KU(7, 3)
    #km_otkl_izd = Short_Comanda_KU(7, 4)
    #km_complex = Short_Comanda_KU(8, 1)
    #km_avtonom = Short_Comanda_KU(8, 2)
    Vuab = Short_Comanda_KU(2, 1, 1)
    # print(struct.unpack('<HQHHIH', km_vklbiab.message()))
    
    # print(Vuab.set_ustavka_error(400, 5))
    # print(struct.unpack('<HQHHIHHI', Vuab.set_ustavka(400, 5)))
    atm = Atm_Packet()
    atm.update_dt_packet(b'\x1b\x00\x8c\x06\xa3\xc492\xd9\x01\x04\x00\x02\x00&\x00\x03\x00\x01?2\x00\x00\x00\x04ff\xa9B') #\x04ff\xa9B
    decode_str= atm.ansver_packet()
    uab = decode_str[1][3]
    print(uab)
    print( struct.pack('<i', decode_str[1][3]))
    print (struct.unpack('<f', b'ff\xa9B'))
    #atm.update_dt_packet(
     #   b'!\x00\xe4d*\xc9W-\xd8\x01\x04\x00\x03\x00\x08\x00\x00\x00\x02\x86\x01\t\x00\x01\x00\x02\x86\x01\x08\x00\x02'
      #  b'\x00\x02\x85\x01')
    #print(atm.ansver_packet())
    #tt = ('av1', 'av2', 'av3', 'av4', 'av5', 'av6', 'av7', 'av8')
    # = 245
    #print(tt)
    #tt1 = (str(bin(t))[2:])
    #print(tt1)
    #for i in range(len(tt1)):
    #    if tt1[i] == '0':
    #        print(tt[i])
    list_kommand = {'vkl_biab': (2, 7, 1, 0), 'vuab': (2, 2, 1, 1), 'atm': (1, 7, 1, 2), 'atm1': (4, 6, 1, 8)}
    km = komm(list_kommand['vkl_biab'])
    print(km)  
    #key_param = {1: 'B', 2: 'b', 3: 'H', 4: 'h', 5: 'I'}
        
    mess1 = mess(komm(list_kommand['vkl_biab']))
    mess2 = mess(komm(list_kommand['vuab']))
    print (km_vklbiab.message())
    print(mess1)
    
    print (Vuab.message())
    print(mess2)
    
    mess3 = mess(set_ust(komm(list_kommand['vuab']), 400, 5, 'I'))
    print(Vuab.set_ustavka(400, 5))
    print(mess3)
    print(Vuab.size_ku)
    print(len(mess3))
        
    mess_atm = mess(komm(list_kommand['atm']))
    mess_atm1 = mess(komm(list_kommand['atm1']))
    mess_head = mess_atm[:2]
    mft = '<HQH'
    mft_receipt = '<HHH'
    mft_data = '<HHB'
    len_pk = struct.calcsize(mft)
    for m in [mess1, mess2, mess3, mess_atm, mess_atm1]:
        mess_pk = struct.unpack(mft, m[:len_pk])
        if mess_pk[2] == 1:
            print('receipt')
            print(mess_pk)
            mess_pk_n = struct.unpack(mft_receipt, m[len_pk:len_pk+struct.calcsize(mft_receipt)])
            print(mess_pk, mess_pk_n)
        elif mess_pk[2] == 4:
            print('data')
            mess_pk_n = struct.unpack(mft_data, m[len_pk:len_pk+struct.calcsize(mft_data)])
            for d in range(mess_pk_n[0]):
                print(d)
            print(mess_pk, mess_pk_n)
        else:
            print('unknow')
        

    #branch = {1: '<B', 2: '<H', 4: '<i', 8: '<d'}
    #mft_atm = '<HQHH'
    #len_atm = struct.calcsize(mft_atm)
    #packet = struct.unpack(mft_atm, data1[:len_atm])
    #print(packet)'''
    
