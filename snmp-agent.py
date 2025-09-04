import time
import threading
import queue
import pigpio
import datetime
import math
from collections import defaultdict

from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp
from pysnmp.smi import rfc1902, instrum

# ---------------------- Ayarlar ----------------------
SNMP_AGENT_PORT = 161
SNMP_COMMUNITY = 'public'
SNMP_ENTERPRISE_OID = '1.3.6.1.4.1.99999'

RX_PIN = 16
TX_PIN = 26
BAUD_RATE = 9600

# ---------------------- Global Değişkenler ----------------------
buffer = bytearray()
data_queue = queue.Queue()
battery_data_ram = defaultdict(dict)
data_lock = threading.Lock()
last_k_value = None
last_k_value_lock = threading.Lock()

# RAM'de veri tutma sistemi
battery_data_ram = defaultdict(dict)  # {arm: {k: {dtype: value}}}
data_lock = threading.Lock()  # Thread-safe erişim için

# SNMP Agent ayarları
SNMP_AGENT_PORT = 161
SNMP_COMMUNITY = 'public'
SNMP_ENTERPRISE_OID = '1.3.6.1.4.1.99999'  # Özel enterprise OID

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

def get_snmp_value(oid_str):
    try:
        oid_parts = oid_str.split(".")
        if len(oid_parts) < 10:
            return rfc1902.NoSuchObject()
        if ".".join(oid_parts[:7]) != SNMP_ENTERPRISE_OID:
            return rfc1902.NoSuchObject()
        arm = int(oid_parts[7])
        k = int(oid_parts[8])
        dtype = int(oid_parts[9])
        data = get_battery_data_ram(arm, k, dtype)
        if not data:
            return rfc1902.NoSuchObject()
        val = data.get("value", 0)
        if isinstance(val, int):
            return rfc1902.Integer(val)
        elif isinstance(val, float):
            return rfc1902.Gauge32(int(val * 100))
        else:
            return rfc1902.OctetString(str(val))
    except:
        return rfc1902.NoSuchObject()

def get_all_battery_data(arm_num, k_value):
    """Belirli bir arm ve k değeri için tüm verileri döndür"""
    try:
        arm_data = get_battery_data_ram(arm_num, k_value)
        
        if not arm_data:
            return {}
            
        result = {}
        for dtype, data in arm_data.items():
            result[dtype] = data['value']
            
        return result
        
    except Exception as e:
        print(f"Tüm batarya verisi alma hatası: {e}")
        return {}

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

def snmp_get_handler(snmpEngine, stateReference, contextName, varBinds, cbCtx):
    """SNMP GET isteklerini işle"""
    try:
        for oid, val in varBinds:
            oid_str = '.'.join([str(x) for x in oid])
            print(f"SNMP GET isteği: OID={oid_str}")
            
            # OID'ye göre değer al
            value = get_snmp_value(oid_str)
            
            if value is not None:
                # Float değeri integer'a çevir (SNMP için)
                int_value = int(value * 100) if isinstance(value, float) else int(value)
                print(f"SNMP değer döndürüldü: OID={oid_str}, Value={value} -> {int_value}")
                
                # SNMP response hazırla
                varBinds = [(oid, rfc1902.Integer(int_value))]
                snmpEngine.msgAndPduDsp.returnResponsePdu(
                    snmpEngine, stateReference, 0, 0, varBinds
                )
            else:
                print(f"SNMP değer bulunamadı: OID={oid_str}")
                # NoSuchInstance hatası döndür
                snmpEngine.msgAndPduDsp.returnResponsePdu(
                    snmpEngine, stateReference, 0, 2, varBinds
                )
                
    except Exception as e:
        print(f"SNMP GET handler hatası: {e}")

def request_handler(snmpEngine, stateReference, contextEngineId,
                    contextName, varBinds, cbCtx):
    rspVarBinds = []
    for oid, val in varBinds:
        oid_str = ".".join(str(x) for x in oid)
        rspVarBinds.append((oid, get_snmp_value(oid_str)))
    return rspVarBinds

def start_snmp_agent():
    snmpEngine = engine.SnmpEngine()
    config.addSocketTransport(
        snmpEngine,
        config.SnmpUDPDomain,
        config.UdpTransport().openServerMode(('0.0.0.0', SNMP_AGENT_PORT))
    )
    config.addV1System(snmpEngine, 'my-area', SNMP_COMMUNITY)
    cmdrsp.GetCommandResponder(snmpEngine, cbFun=request_handler)
    cmdrsp.NextCommandResponder(snmpEngine, cbFun=request_handler)
    cmdrsp.SetCommandResponder(snmpEngine, cbFun=request_handler)
    snmpEngine.transportDispatcher.jobStarted(1)
    try:
        snmpEngine.transportDispatcher.runDispatcher()
    except KeyboardInterrupt:
        snmpEngine.transportDispatcher.closeDispatcher()
        print("SNMP agent kapatıldı.")

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

        # SNMP Agent thread'i
        snmp_thread = threading.Thread(target=start_snmp_agent, daemon=True)
        snmp_thread.start()
        print("snmp_agent thread'i başlatıldı.")

        print(f"\nSistem başlatıldı.")
        print("Program çalışıyor... (Ctrl+C ile durdurun)")

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
    print("SNMP Agent başlatıldı ==>")
    main()
