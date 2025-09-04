# -*- coding: utf-8 -*-

import time
import datetime
import threading
import queue
import math
import pigpio
import json
import os
import socket
import struct
import sys
from collections import defaultdict

# SNMP imports
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

# Global variables
buffer = bytearray()
data_queue = queue.Queue()
RX_PIN = 16
TX_PIN = 26
BAUD_RATE = 9600

# Periyot sistemi için global değişkenler
current_period_timestamp = None
period_active = False
last_data_received = time.time()
last_k_value = None  # Son gelen verinin k değerini tutar
last_k_value_lock = threading.Lock()  # Thread-safe erişim için

# RAM'de veri tutma sistemi
battery_data_ram = defaultdict(dict)  # {arm: {k: {dtype: value}}}
data_lock = threading.Lock()  # Thread-safe erişim için

# Modbus TCP server ayarları
MODBUS_TCP_PORT = 1502  # Port 502 yerine 1502 kullan
MODBUS_TCP_HOST = '0.0.0.0'

# SNMP Agent ayarları
SNMP_PORT = 1161
SNMP_HOST = '0.0.0.0'  # Dışarıdan erişim için 0.0.0.0

def Calc_SOC(x):
    if x is None:
        return None
        
    a1, a2, a3, a4 = 112.1627, 14.3937, 0, 10.5555
    b1, b2, b3, b4 = 14.2601, 11.6890, 12.7872, 10.9406
    c1, c2, c3, c4 = 1.8161, 0.8211, 0.0025, 0.3866
    
    try:
        Soctahmin = (
            a1 * math.exp(-((x - b1) / c1) ** 2) +
            a2 * math.exp(-((x - b2) / c2) ** 2) +
            a3 * math.exp(-((x - b3) / c3) ** 2) +
            a4 * math.exp(-((x - b4) / c4) ** 2)
        )
        
        if Soctahmin > 100.0:
            Soctahmin = 100.0
        elif Soctahmin < 0.0:
            Soctahmin = 0.0
            
        return round(Soctahmin, 4)
    except Exception as e:
        print(f"SOC hesaplama hatası: {str(e)}")
        return None

pi = pigpio.pi()
pi.set_mode(TX_PIN, pigpio.OUTPUT)

# Program başlangıç zamanı
program_start_time = int(time.time() * 1000)

def get_period_timestamp():
    """Aktif periyot için timestamp döndür"""
    global current_period_timestamp, period_active, last_data_received
    
    current_time = time.time()
    
    if not period_active:
        current_period_timestamp = int(current_time * 1000)
        period_active = True
        last_data_received = current_time
    
    return current_period_timestamp

def reset_period():
    """Periyotu sıfırla"""
    global period_active, current_period_timestamp
    period_active = False
    current_period_timestamp = None

def update_last_k_value(new_value):
    """Thread-safe olarak last_k_value güncelle"""
    global last_k_value
    with last_k_value_lock:
        last_k_value = new_value

def get_last_k_value():
    """Thread-safe olarak last_k_value oku"""
    global last_k_value
    with last_k_value_lock:
        return last_k_value

def update_battery_data_ram(arm, k, dtype, value):
    """RAM'deki batarya verilerini güncelle"""
    with data_lock:
        if arm not in battery_data_ram:
            battery_data_ram[arm] = {}
        if k not in battery_data_ram[arm]:
            battery_data_ram[arm][k] = {}
        
        battery_data_ram[arm][k][dtype] = {
            'value': value,
            'timestamp': int(time.time() * 1000)
        }
        
        print(f"RAM'e kaydedildi: Arm={arm}, k={k}, dtype={dtype}, value={value}")

def clear_battery_data_ram():
    """RAM'deki tüm batarya verilerini temizle"""
    with data_lock:
        battery_data_ram.clear()
        print("RAM tamamen temizlendi.")

def get_battery_data_ram(arm=None, k=None, dtype=None):
    """RAM'den batarya verilerini oku"""
    with data_lock:
        if arm is None:
            result = dict(battery_data_ram)
            print(f"RAM'den okundu: Tüm veriler, {len(result)} arm")
            return result
        elif k is None:
            result = dict(battery_data_ram.get(arm, {}))
            print(f"RAM'den okundu: Arm={arm}, {len(result)} k değeri")
            return result
        elif dtype is None:
            result = dict(battery_data_ram.get(arm, {}).get(k, {}))
            print(f"RAM'den okundu: Arm={arm}, k={k}, {len(result)} dtype")
            return result
        else:
            result = battery_data_ram.get(arm, {}).get(k, {}).get(dtype, None)
            print(f"RAM'den okundu: Arm={arm}, k={k}, dtype={dtype}, value={result}")
            return result

def Calc_SOH(x):
    if x is None:
        return None
    
    try:
        a1, b1, c1 = 85.918, 0.0181, 0.0083
        a2, b2, c2 = 85.11, 0.0324, 0.0104
        a3, b3, c3 = 0.3085, 0.0342, 0.0021
        a4, b4, c4 = 16.521, 0.0382, 0.0013
        a5, b5, c5 = -13.874, 0.0381, 0.0011
        a6, b6, c6 = 40.077, 0.0474, 0.0079
        a7, b7, c7 = 18.207, 0.0556, 0.0048

        SohSonuc = (
            a1 * math.exp(-((x - b1) / c1) ** 2) +
            a2 * math.exp(-((x - b2) / c2) ** 2) +
            a3 * math.exp(-((x - b3) / c3) ** 2) +
            a4 * math.exp(-((x - b4) / c4) ** 2) +
            a5 * math.exp(-((x - b5) / c5) ** 2) +
            a6 * math.exp(-((x - b6) / c6) ** 2) +
            a7 * math.exp(-((x - b7) / c7) ** 2)
        )
        
        if SohSonuc > 100.0:
            SohSonuc = 100.0
        
        return round(SohSonuc, 4)
    except Exception as e:
        print(f"SOH hesaplama hatası: {str(e)}")
        return None

def Calc_SOC(x):
    if x is None:
        return None
        
    a1, a2, a3, a4 = 112.1627, 14.3937, 0, 10.5555
    b1, b2, b3, b4 = 14.2601, 11.6890, 12.7872, 10.9406
    c1, c2, c3, c4 = 1.8161, 0.8211, 0.0025, 0.3866
    
    try:
        Soctahmin = (
            a1 * math.exp(-((x - b1) / c1) ** 2) +
            a2 * math.exp(-((x - b2) / c2) ** 2) +
            a3 * math.exp(-((x - b3) / c3) ** 2) +
            a4 * math.exp(-((x - b4) / c4) ** 2)
        )
        
        if Soctahmin > 100.0:
            Soctahmin = 100.0
        elif Soctahmin < 0.0:
            Soctahmin = 0.0
            
        return round(Soctahmin, 4)
    except Exception as e:
        print(f"SOC hesaplama hatası: {str(e)}")
        return None

def read_serial(pi):
    """Bit-banging ile GPIO üzerinden seri veri oku"""
    global buffer
    print("\nBit-banging UART veri alımı başladı...")
    
    buffer.clear()

    while True:
        try:
            (count, data) = pi.bb_serial_read(RX_PIN)
            if count > 0:
                buffer.extend(data)
                
                while len(buffer) >= 3:
                    try:
                        # Header (0x80 veya 0x81) bul
                        header_index = -1
                        for i, byte in enumerate(buffer):
                            if byte == 0x80 or byte == 0x81:
                                header_index = i
                                break
                        
                        if header_index == -1:
                            buffer.clear()
                            break

                        if header_index > 0:
                            buffer = buffer[header_index:]

                        # Paket uzunluğunu belirle
                        if len(buffer) >= 3:
                            dtype = buffer[2]
                            
                            # 5 byte'lık missing data paketi kontrolü
                            if dtype == 0x7F and len(buffer) >= 5:
                                packet_length = 5
                            # 6 byte'lık paket kontrolü
                            elif len(buffer) >= 6 and (buffer[2] == 0x0F or buffer[1] == 0x7E or (buffer[2] == 0x7D and buffer[1] == 2)):
                                packet_length = 6
                            elif dtype == 0x7D and len(buffer) >= 7 and buffer[1] > 2:
                                packet_length = 7
                            else:
                                packet_length = 11

                            if len(buffer) >= packet_length:
                                packet = buffer[:packet_length]
                                buffer = buffer[packet_length:]
                                hex_packet = [f"{b:02x}" for b in packet]
                                data_queue.put(hex_packet)
                            else:
                                # Paket tamamlanmamış, daha fazla veri bekle
                                break
                        else:
                            break

                    except Exception as e:
                        print(f"Paket işleme hatası: {e}")
                        buffer.clear()
                        continue

            time.sleep(0.01)

        except Exception as e:
            print(f"Veri okuma hatası: {e}")
            time.sleep(1)

def data_processor():
    """Gelen verileri işle ve RAM'e kaydet"""
    global last_data_received
    
    while True:
        try:
            data = data_queue.get(timeout=1)
            if data is None:
                break
            
            # Veri alındığında zaman damgasını güncelle
            last_data_received = time.time()
        
            # 7 byte Batkon alarm verisi kontrolü
            if len(data) == 7:
                raw_bytes = [int(b, 16) for b in data]
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                print(f"\n*** BATKON ALARM VERİSİ ALGILANDI - {timestamp} ***")
                print(f"Ham Veri: {data}")
                continue

            # 5 byte'lık missing data verisi kontrolü
            if len(data) == 5:
                raw_bytes = [int(b, 16) for b in data]
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                print(f"\n*** MISSING DATA VERİSİ ALGILANDI - {timestamp} ***")
                continue

            # 11 byte'lık veri kontrolü
            if len(data) == 11:
                arm_value = int(data[3], 16)
                dtype = int(data[2], 16)
                k_value = int(data[1], 16)
                
                # k_value 2 geldiğinde yeni periyot başlat (ard arda gelmemesi şartıyla)
                if k_value == 2:
                    if get_last_k_value() != 2:  # Non-consecutive arm data
                        reset_period()
                        get_period_timestamp()
                    update_last_k_value(2)
                else:  # Battery data
                    update_last_k_value(k_value)
                
                # Arm değeri kontrolü
                if arm_value not in [1, 2, 3, 4]:
                    print(f"\nHATALI ARM DEĞERİ: {arm_value}")
                    continue
                
                # Salt data hesapla
                if dtype == 11 and k_value == 2:  # Nem hesapla
                    onlar = int(data[5], 16)
                    birler = int(data[6], 16)
                    kusurat1 = int(data[7], 16)
                    kusurat2 = int(data[8], 16)
                    
                    tam_kisim = (onlar * 10 + birler)
                    kusurat_kisim = (kusurat1 * 0.1 + kusurat2 * 0.01)
                    salt_data = tam_kisim + kusurat_kisim
                    salt_data = round(salt_data, 4)
                else:
                    # Normal hesaplama
                    saltData = int(data[4], 16) * 100 + int(data[5], 16) * 10 + int(data[6], 16) + int(data[7], 16) * 0.1 + int(data[8], 16) * 0.01 + int(data[9], 16) * 0.001
                    salt_data = round(saltData, 4)
                
                # Veri işleme ve RAM'e kayıt
                if dtype == 10:  # Gerilim
                    # Ham gerilim verisini kaydet
                    update_battery_data_ram(arm_value, k_value, 10, salt_data)
                    
                    # SOC hesapla ve dtype=126'ya kaydet
                    if k_value != 2:  # k_value 2 değilse SOC hesapla
                        soc_value = Calc_SOC(salt_data)
                        update_battery_data_ram(arm_value, k_value, 126, soc_value)
                
                elif dtype == 11:  # SOH veya Nem
                    if k_value == 2:  # Nem verisi
                        print(f"*** VERİ ALGILANDI - Arm: {arm_value}, Nem: {salt_data}% ***")
                        update_battery_data_ram(arm_value, k_value, 11, salt_data)
                    else:  # SOH verisi
                        if int(data[4], 16) == 1:  # Eğer data[4] 1 ise SOH 100'dür
                            soh_value = 100.0
                        else:
                            onlar = int(data[5], 16)
                            birler = int(data[6], 16)
                            kusurat1 = int(data[7], 16)
                            kusurat2 = int(data[8], 16)
                            
                            tam_kisim = (onlar * 10 + birler)
                            kusurat_kisim = (kusurat1 * 0.1 + kusurat2 * 0.01)
                            soh_value = tam_kisim + kusurat_kisim
                            soh_value = round(soh_value, 4)
                        
                        # SOH verisini dtype=11'e kaydet
                        update_battery_data_ram(arm_value, k_value, 11, soh_value)
                
                elif dtype == 12:  # NTC1
                    update_battery_data_ram(arm_value, k_value, 12, salt_data)
                
                elif dtype == 13:  # NTC2
                    update_battery_data_ram(arm_value, k_value, 13, salt_data)
                

                
                else:  # Diğer Dtype değerleri için
                    update_battery_data_ram(arm_value, k_value, dtype, salt_data)

            # 6 byte'lık balans komutu veya armslavecounts kontrolü
            elif len(data) == 6:
                raw_bytes = [int(b, 16) for b in data]
                
                # Slave sayısı verisi: 2. byte (index 1) 0x7E ise
                if raw_bytes[1] == 0x7E:
                    arm1, arm2, arm3, arm4 = raw_bytes[2], raw_bytes[3], raw_bytes[4], raw_bytes[5]
                    print(f"armslavecounts verisi tespit edildi: arm1={arm1}, arm2={arm2}, arm3={arm3}, arm4={arm4}")
                    continue
                
                # Balans verisi: 3. byte (index 2) 0x0F ise
                elif raw_bytes[2] == 0x0F:
                    print(f"Balans verisi tespit edildi")
                    continue
                
                # Hatkon alarmı: 3. byte (index 2) 0x7D ise
                elif raw_bytes[2] == 0x7D:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    print(f"\n*** HATKON ALARM VERİSİ ALGILANDI - {timestamp} ***")
                    continue

            data_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"\ndata_processor'da beklenmeyen hata: {e}")
            continue

def modbus_tcp_server():
    """Modbus TCP server - cihazlardan gelen istekleri dinle"""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((MODBUS_TCP_HOST, MODBUS_TCP_PORT))
        server_socket.listen(5)
        
        print(f"Modbus TCP Server başlatıldı: {MODBUS_TCP_HOST}:{MODBUS_TCP_PORT}")
        
        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"Yeni bağlantı: {client_address}")
                
                # Her bağlantı için ayrı thread
                client_thread = threading.Thread(
                    target=handle_modbus_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                print(f"Modbus TCP server hatası: {e}")
                continue
                
    except Exception as e:
        print(f"Modbus TCP server başlatma hatası: {e}")

def handle_modbus_client(client_socket, client_address):
    """Modbus TCP client isteklerini işle"""
    try:
        while True:
            # Modbus TCP frame oku
            data = client_socket.recv(1024)
            if not data:
                break
            
            if len(data) < 8:  # Minimum Modbus TCP frame boyutu
                continue
            
            # Modbus TCP frame parse et
            transaction_id = struct.unpack('>H', data[0:2])[0]
            protocol_id = struct.unpack('>H', data[2:4])[0]
            length = struct.unpack('>H', data[4:6])[0]
            unit_id = data[6]
            function_code = data[7]
            
            print(f"Modbus TCP isteği: Transaction={transaction_id}, Function={function_code}, Unit={unit_id}")
            
            # Function code 3 (Read Holding Registers) işle
            if function_code == 3:
                if len(data) >= 12:
                    start_address = struct.unpack('>H', data[8:10])[0]
                    quantity = struct.unpack('>H', data[10:12])[0]
                    
                    response = handle_read_holding_registers(transaction_id, unit_id, start_address, quantity)
                    if response:
                        client_socket.send(response)
            
            # Function code 4 (Read Input Registers) işle
            elif function_code == 4:
                if len(data) >= 12:
                    start_address = struct.unpack('>H', data[8:10])[0]
                    quantity = struct.unpack('>H', data[10:12])[0]
                    
                    response = handle_read_input_registers(transaction_id, unit_id, start_address, quantity)
                    if response:
                        client_socket.send(response)
            
    except Exception as e:
        print(f"Client {client_address} işleme hatası: {e}")
    finally:
        client_socket.close()
        print(f"Client {client_address} bağlantısı kapatıldı")

def handle_read_holding_registers(transaction_id, unit_id, start_address, quantity):
    """Read Holding Registers (Function Code 3) işle"""
    try:
        print(f"DEBUG: start_address={start_address}, quantity={quantity}")
        
        # Batarya verilerini hazırla
        registers = []
        
        # Start address'e göre veri döndür
        if start_address == 0:  # Genel sistem bilgileri
            # Register 0'dan başlayarak doldur
            registers = []
            for i in range(quantity):
                if i == 0:
                    registers.append(1.0)  # Arm 1 aktif
                elif i == 1:
                    registers.append(2.0)  # Arm 2 aktif
                elif i == 2:
                    registers.append(3.0)  # Arm 3 aktif
                elif i == 3:
                    registers.append(4.0)  # Arm 4 aktif
                else:
                    registers.append(0.0)  # Boş register
            print(f"DEBUG: Genel sistem bilgileri: {registers}")
        elif start_address >= 100 and start_address < 200:  # Arm 1 verileri
            arm_num = 1
            if start_address == 100:  # k=2 (arm verileri)
                arm_data = get_battery_data_ram(arm_num)
                registers = format_arm_data_for_modbus(arm_data, 0, quantity)
                print(f"DEBUG: Arm {arm_num}, k=2 (arm) verileri: {registers}")
            else:  # k>2 (batarya verileri)
                k_value = start_address - 100
                arm_data = get_battery_data_ram(arm_num)
                registers = format_specific_battery_data(arm_data, k_value, quantity)
                print(f"DEBUG: Arm {arm_num}, k={k_value} (batarya) verileri: {registers}")
        elif start_address >= 200 and start_address < 300:  # Arm 2 verileri
            arm_num = 2
            if start_address == 200:  # k=2 (arm verileri)
                arm_data = get_battery_data_ram(arm_num)
                registers = format_arm_data_for_modbus(arm_data, 0, quantity)
                print(f"DEBUG: Arm {arm_num}, k=2 (arm) verileri: {registers}")
            else:  # k>2 (batarya verileri)
                k_value = start_address - 200
                arm_data = get_battery_data_ram(arm_num)
                registers = format_specific_battery_data(arm_data, k_value, quantity)
                print(f"DEBUG: Arm {arm_num}, k={k_value} (batarya) verileri: {registers}")
        elif start_address >= 300 and start_address < 400:  # Arm 3 verileri
            arm_num = 3
            if start_address == 300:  # k=2 (arm verileri)
                arm_data = get_battery_data_ram(arm_num)
                registers = format_arm_data_for_modbus(arm_data, 0, quantity)
                print(f"DEBUG: Arm {arm_num}, k=2 (arm) verileri: {registers}")
            else:  # k>2 (batarya verileri)
                k_value = start_address - 300
                arm_data = get_battery_data_ram(arm_num)
                registers = format_specific_battery_data(arm_data, k_value, quantity)
                print(f"DEBUG: Arm {arm_num}, k={k_value} (batarya) verileri: {registers}")
        elif start_address >= 0x1000 and start_address <= 0x4FFF:  # Hex adresler (1000-4FFF)
            # Hex adresini parse et: 303A -> Arm=3, Battery=3, Dtype=A
            hex_str = hex(start_address)[2:].upper()  # '303A'
            
            if len(hex_str) >= 4:
                # Hex adresini parse et: 3000, 3001, 3004, 303A, 303B, vs.
                arm_num = int(hex_str[0], 16)  # İlk hane: Arm numarası
                
                # Hex dtype'ı sayıya çevir
                hex_to_dtype = {
                    'A': 10,   # Gerilim
                    'B': 11,   # SOH
                    'C': 12,   # NTC1
                    'D': 13,   # NTC2
                    'E': 14,   # NTC3
                    'F': 126   # SOC
                }
                
                # 3000 formatı (tüm veriler) vs 303A formatı (tekil veri) kontrolü
                if len(hex_str) >= 4 and hex_str[3] in ['A', 'B', 'C', 'D', 'E', 'F']:
                    # 303A formatı: Tekil veri
                    battery_num = int(hex_str[2], 16)  # Üçüncü hane: Battery numarası (301A -> 1)
                    k_value = battery_num + 2  # Battery numarası + 2 = k değeri (301A -> k=3)
                    dtype_hex = hex_str[3]  # Dördüncü hane: Dtype (301A -> A)
                    dtype = hex_to_dtype.get(dtype_hex, 10)
                    arm_data = get_battery_data_ram(arm_num)
                    registers = format_specific_dtype_data(arm_data, k_value, dtype, quantity)
                    print(f"DEBUG: Arm {arm_num}, k={k_value}, dtype={dtype} (hex adres {hex(start_address)}) verileri: {registers}")
                else:
                    # 3000, 3001, 3004 formatı: Tüm veriler
                    battery_num = int(hex_str[3], 16)  # Dördüncü hane: Battery numarası (3004 -> 4)
                    if battery_num == 0:  # 3000 -> Arm 3, k=2 (arm verileri)
                        k_value = 2
                        arm_data = get_battery_data_ram(arm_num)
                        registers = format_arm_data_for_modbus(arm_data, k_value, quantity)
                        print(f"DEBUG: Arm {arm_num}, k={k_value} (arm verileri) verileri: {registers}")
                    else:  # 3001, 3004, vs. -> Arm 3, k=3,4,5 (batarya verileri)
                        k_value = battery_num  # 3001 -> k=1, 3004 -> k=4
                        arm_data = get_battery_data_ram(arm_num)
                        registers = format_specific_battery_data(arm_data, k_value, quantity)
                        print(f"DEBUG: Arm {arm_num}, k={k_value} (batarya verileri) verileri: {registers}")
            else:
                registers = [0.0] * quantity
                print(f"DEBUG: Geçersiz hex adres {hex(start_address)}, boş veri: {registers}")
        elif start_address >= 400 and start_address < 500:  # Arm 4 verileri
            arm_num = 4
            if start_address == 400:  # k=2 (arm verileri)
                arm_data = get_battery_data_ram(arm_num)
                registers = format_arm_data_for_modbus(arm_data, 0, quantity)
                print(f"DEBUG: Arm {arm_num}, k=2 (arm) verileri: {registers}")
            else:  # k>2 (batarya verileri)
                k_value = start_address - 400
                arm_data = get_battery_data_ram(arm_num)
                registers = format_specific_battery_data(arm_data, k_value, quantity)
                print(f"DEBUG: Arm {arm_num}, k={k_value} (batarya) verileri: {registers}")
        else:
            # Bilinmeyen adres için boş veri
            registers = [0.0] * quantity
            print(f"DEBUG: Bilinmeyen adres {start_address}, boş veri: {registers}")
        
        # Modbus TCP response hazırla
        byte_count = len(registers) * 2  # Her register 2 byte
        response = struct.pack('>HHHBB', 
                      transaction_id,
                      0,
                      byte_count + 3,
                      unit_id,
                      3
                     )
        response += struct.pack('B', byte_count)

        for reg in registers:
            # Virgüllü sayıları 100 ile çarpıp integer olarak gönder
            if reg == int(reg):  # Tam sayı ise
                response += struct.pack('>H', int(reg))
            else:  # Virgüllü sayı ise
                response += struct.pack('>H', int(reg * 100))  # 100 ile çarp

        
        # Register isimlerini hazırla
        register_names = []
        if start_address == 0:
            register_names = ["Arm1", "Arm2", "Arm3", "Arm4"]
        elif start_address >= 0x1000 and start_address <= 0x4FFF:  # Hex adresler
            hex_str = hex(start_address)[2:].upper()
            if len(hex_str) >= 4:
                arm_num = int(hex_str[0], 16)
                if len(hex_str) >= 4 and hex_str[3] in ['A', 'B', 'C', 'D', 'E', 'F']:
                    # Tekil veri formatı (301A) - tek değer
                    register_names = ["Tekil Veri"]
                else:
                    # Tüm veriler formatı (3000, 3001, 3004)
                    battery_num = int(hex_str[3], 16)
                    if battery_num == 0:  # 3000 -> k=2 (arm verileri)
                        register_names = ["Akım(A)", "Nem(%)", "NTC1(°C)", "NTC2(°C)"]
                    else:  # 3001, 3004 -> k>2 (batarya verileri)
                        register_names = ["Gerilim(V)", "SOH(%)", "NTC1(°C)", "NTC2(°C)", "NTC3(°C)", "SOC(%)"]
            else:
                register_names = ["Bilinmeyen"]
        else:
            register_names = ["Gerilim(V)", "SOH(%)", "NTC1(°C)", "NTC2(°C)", "NTC3(°C)", "SOC(%)"]
        
        print(f"DEBUG: Response hazırlandı, byte_count={byte_count}")
        print(f"DEBUG: Register Names: {register_names[:len(registers)]}")
        print(f"DEBUG: Register Values: {registers}")
        print(f"DEBUG: Modbus Values (100x): {[int(reg * 100) if reg != int(reg) else int(reg) for reg in registers]}")
        return response
        
    except Exception as e:
        print(f"Read Holding Registers hatası: {e}")
        import traceback
        traceback.print_exc()
        return None

def handle_read_input_registers(transaction_id, unit_id, start_address, quantity):
    """Read Input Registers (Function Code 4) işle"""
    # Şimdilik Read Holding Registers ile aynı
    return handle_read_holding_registers(transaction_id, unit_id, start_address, quantity)

def format_arm_data_for_modbus(arm_data, k_value, quantity):
    """Arm verilerini Modbus register formatına çevir - sadece k=2 (arm) verileri"""
    registers = []
    
    # Veri tiplerini sırala: 10 (akım), 11 (nem), 12 (ntc1), 13 (ntc2)
    data_types = [10, 11, 12, 13]
    
    # Sadece mevcut veri tiplerini döndür, quantity'yi sınırla
    max_registers = min(quantity, len(data_types))
    
    for i in range(max_registers):
        dtype = data_types[i]
        value = 0.0
        
        # Sadece k=2 (arm) verilerini kontrol et
        if k_value in arm_data and dtype in arm_data[k_value]:
            value = arm_data[k_value][dtype]['value']
            print(f"DEBUG: k={k_value} (arm) verisi kullanıldı: dtype={dtype}, value={value}")
        
        registers.append(value)
    
    return registers

def format_specific_battery_data(arm_data, battery_num, quantity):
    """Belirli bir bataryanın verilerini Modbus register formatına çevir"""
    registers = []
    
    # Veri tiplerini sırala: 10 (gerilim/akım), 11 (soh/nem), 12 (ntc1), 13 (ntc2), 14 (ntc3), 126 (soc)
    data_types = [10, 11, 12, 13, 14, 126]
    
    # Sadece mevcut veri tiplerini döndür, quantity'yi sınırla
    max_registers = min(quantity, len(data_types))
    
    for i in range(max_registers):
        dtype = data_types[i]
        value = 0.0
        
        # Belirli batarya numarası için veri ara
        if battery_num in arm_data and dtype in arm_data[battery_num]:
            value = arm_data[battery_num][dtype]['value']
            print(f"DEBUG: Batarya {battery_num} verisi kullanıldı: dtype={dtype}, value={value}")
        
        registers.append(value)
    
    return registers

def format_specific_dtype_data(arm_data, battery_num, dtype, quantity):
    """Belirli bir dtype'ın verilerini Modbus register formatına çevir - tek değer döner"""
    registers = []
    
    # Tek değer döndür
    value = 0.0
    
    # Belirli batarya numarası ve dtype için veri ara
    if battery_num in arm_data and dtype in arm_data[battery_num]:
        value = arm_data[battery_num][dtype]['value']
        print(f"DEBUG: Batarya {battery_num}, dtype={dtype} verisi kullanıldı: value={value}")
    
    # Quantity kadar aynı değeri döndür
    for i in range(quantity):
        registers.append(value)
    
    return registers

def start_snmp_agent():
    """SNMP Agent başlat - Modbus TCP Server RAM sistemi ile"""
    print("🚀 SNMP Agent Başlatılıyor...")
    print("📊 Modbus TCP Server RAM Sistemi ile Entegre")
    
    try:
        # Create SNMP engine
        snmpEngine = engine.SnmpEngine()
        print("✅ SNMP Engine oluşturuldu")

        # Transport setup - UDP over IPv4
        config.add_transport(
            snmpEngine, udp.DOMAIN_NAME, udp.UdpTransport().open_server_mode((SNMP_HOST, SNMP_PORT))
        )
        print("✅ Transport ayarlandı")

        # SNMPv2c setup
        config.add_v1_system(snmpEngine, "my-area", "public")
        print("✅ SNMPv2c ayarlandı")

        # Allow read MIB access for this user / securityModels at VACM
        config.add_vacm_user(snmpEngine, 2, "my-area", "noAuthNoPriv", (1, 3, 6, 5))
        print("✅ VACM ayarlandı")

        # Create an SNMP context
        snmpContext = context.SnmpContext(snmpEngine)
        print("✅ SNMP Context oluşturuldu")

        # --- create custom Managed Object Instance ---
        mibBuilder = snmpContext.get_mib_instrum().get_mib_builder()

        MibScalar, MibScalarInstance = mibBuilder.import_symbols(
            "SNMPv2-SMI", "MibScalar", "MibScalarInstance"
        )
        print("✅ MIB Builder oluşturuldu")

        class ModbusRAMMibScalarInstance(MibScalarInstance):
            """Modbus TCP Server RAM sistemi ile MIB Instance"""
            def getValue(self, name, **context):
                oid = '.'.join([str(x) for x in name])
                print(f"🔍 SNMP OID sorgusu: {oid}")
                
                # Sistem bilgileri
                if oid == "1.3.6.5.1.0":
                    return self.getSyntax().clone(
                        f"Python {sys.version} running on a {sys.platform} platform"
                    )
                elif oid == "1.3.6.5.2.0":  # totalBatteryCount
                    data = get_battery_data_ram()
                    battery_count = 0
                    for arm in data.keys():
                        for k in data[arm].keys():
                            if k > 2:  # k>2 olanlar batarya verisi
                                battery_count += 1
                    return self.getSyntax().clone(str(battery_count if battery_count > 0 else 0))
                elif oid == "1.3.6.5.3.0":  # totalArmCount
                    data = get_battery_data_ram()
                    return self.getSyntax().clone(str(len(data) if data else 0))
                elif oid == "1.3.6.5.4.0":  # systemStatus
                    return self.getSyntax().clone("1")
                elif oid == "1.3.6.5.5.0":  # lastUpdateTime
                    return self.getSyntax().clone(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                elif oid == "1.3.6.5.6.0":  # dataCount
                    data = get_battery_data_ram()
                    total_data = 0
                    for arm in data.values():
                        for k in arm.values():
                            total_data += len(k)
                    return self.getSyntax().clone(str(total_data if total_data > 0 else 0))
                else:
                    # Gerçek batarya verileri - Modbus TCP Server RAM'den oku
                    if oid.startswith("1.3.6.5.10."):
                        parts = oid.split('.')
                        if len(parts) >= 8:  # 1.3.6.5.10.arm.k.dtype.0
                            arm = int(parts[5])    # 1.3.6.5.10.{arm}
                            k = int(parts[6])      # 1.3.6.5.10.arm.{k}
                            dtype = int(parts[7])  # 1.3.6.5.10.arm.k.{dtype}
                            
                            data = get_battery_data_ram(arm, k, dtype)
                            if data:
                                return self.getSyntax().clone(str(data['value']))
                            return self.getSyntax().clone("0")
                    
                    return self.getSyntax().clone("No Such Object")

        # MIB Objects oluştur
        mibBuilder.export_symbols(
            "__MODBUS_RAM_MIB",
            # Sistem bilgileri
            MibScalar((1, 3, 6, 5, 1), v2c.OctetString()),
            ModbusRAMMibScalarInstance((1, 3, 6, 5, 1), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 2), v2c.OctetString()),
            ModbusRAMMibScalarInstance((1, 3, 6, 5, 2), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 3), v2c.OctetString()),
            ModbusRAMMibScalarInstance((1, 3, 6, 5, 3), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 4), v2c.OctetString()),
            ModbusRAMMibScalarInstance((1, 3, 6, 5, 4), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 5), v2c.OctetString()),
            ModbusRAMMibScalarInstance((1, 3, 6, 5, 5), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 6), v2c.OctetString()),
            ModbusRAMMibScalarInstance((1, 3, 6, 5, 6), (0,), v2c.OctetString()),
        )
        
        # Batarya verileri için MIB Objects - Dinamik olarak oluştur
        for arm in range(1, 5):  # 1, 2, 3, 4
            for k in range(2, 6):  # 2, 3, 4, 5
                for dtype in range(10, 15):  # 10, 11, 12, 13, 14
                    oid = (1, 3, 6, 5, 10, arm, k, dtype)
                    mibBuilder.export_symbols(
                        f"__BATTERY_MIB_{arm}_{k}_{dtype}",
                        MibScalar(oid, v2c.OctetString()),
                        ModbusRAMMibScalarInstance(oid, (0,), v2c.OctetString()),
                    )
                
                # SOC verisi için dtype=126
                oid = (1, 3, 6, 5, 10, arm, k, 126)
                mibBuilder.export_symbols(
                    f"__BATTERY_MIB_{arm}_{k}_126",
                    MibScalar(oid, v2c.OctetString()),
                    ModbusRAMMibScalarInstance(oid, (0,), v2c.OctetString()),
                )
        print("✅ MIB Objects oluşturuldu")

        # --- end of Managed Object Instance initialization ----

        # Register SNMP Applications at the SNMP engine for particular SNMP context
        cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
        cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
        cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)
        print("✅ Command Responder'lar kaydedildi (GET/GETNEXT/GETBULK)")

        # Register an imaginary never-ending job to keep I/O dispatcher running forever
        snmpEngine.transport_dispatcher.job_started(1)
        print("✅ Job başlatıldı")

        print(f"🚀 SNMP Agent başlatılıyor...")
        print(f"📡 Port {SNMP_PORT}'de dinleniyor...")
        print("=" * 50)
        print("SNMP Test OID'leri:")
        print("1.3.6.5.1.0  - Python bilgisi")
        print("1.3.6.5.2.0  - Batarya sayısı")
        print("1.3.6.5.3.0  - Kol sayısı")
        print("1.3.6.5.4.0  - Sistem durumu")
        print("1.3.6.5.5.0  - Son güncelleme")
        print("1.3.6.5.6.0  - Veri sayısı")
        print("=" * 50)
        print("SNMP Test komutları:")
        print(f"snmpget -v2c -c public localhost:{SNMP_PORT} 1.3.6.5.2.0")
        print(f"snmpget -v2c -c public localhost:{SNMP_PORT} 1.3.6.5.10.1.2.10.0")
        print(f"snmpget -v2c -c public localhost:{SNMP_PORT} 1.3.6.5.10.1.3.10.0")
        print(f"snmpwalk -v2c -c public localhost:{SNMP_PORT} 1.3.6.5")
        print("=" * 50)

        # Run I/O dispatcher which would receive queries and send responses
        try:
            snmpEngine.open_dispatcher()
        except:
            snmpEngine.close_dispatcher()
            raise
        
    except Exception as e:
        print(f"❌ SNMP Agent hatası: {e}")
        import traceback
        traceback.print_exc()

def main():
    try:
        # RAM'i temizle
        with data_lock:
            battery_data_ram.clear()
        print("RAM temizlendi.")
        
        if not pi.connected:
            print("pigpio bağlantısı sağlanamadı!")
            return
            
        pi.write(TX_PIN, 1)

        # Okuma thread'i
        pi.bb_serial_read_open(RX_PIN, BAUD_RATE)
        print(f"GPIO{RX_PIN} bit-banging UART başlatıldı @ {BAUD_RATE} baud.")

        # Okuma thread'i
        read_thread = threading.Thread(target=read_serial, args=(pi,), daemon=True)
        read_thread.start()
        print("read_serial thread'i başlatıldı.")

        # Veri işleme thread'i
        data_thread = threading.Thread(target=data_processor, daemon=True)
        data_thread.start()
        print("data_processor thread'i başlatıldı.")

        # Modbus TCP server thread'i
        modbus_thread = threading.Thread(target=modbus_tcp_server, daemon=True)
        modbus_thread.start()
        print("modbus_tcp_server thread'i başlatıldı.")

        # SNMP Agent'ı ana thread'de çalıştır (thread içinde asyncio sorunu)
        print("SNMP Agent başlatılıyor...")
        start_snmp_agent()

        print(f"\nSistem başlatıldı.")
        print("Program çalışıyor... (Ctrl+C ile durdurun)")
        print("=" * 50)
        print("Modbus TCP Server: Port 1502")
        print(f"SNMP Agent: Port {SNMP_PORT}")
        print("=" * 50)

        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nProgram sonlandırılıyor...")

    finally:
        if 'pi' in locals():
            try:
                pi.bb_serial_read_close(RX_PIN)
                print("Bit-bang UART kapatıldı.")
            except pigpio.error:
                print("Bit-bang UART zaten kapalı.")
            pi.stop()

if __name__ == '__main__':
    print("Modbus TCP Server başlatıldı ==>")
    main()

 