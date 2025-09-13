#!/usr/bin/env python3
"""
SNMP Server - PySNMP v7.1 ile SNMP Agent
"""

import asyncio
import threading
import time
from pysnmp.hlapi.v3arch.asyncio import *
from collections import defaultdict

# SNMP Server ayarları
community_string = 'public'
host = '0.0.0.0'  # Tüm arayüzlerde dinle
port = 161

# RAM'de veri tutma sistemi (modbus-tcp-server'dan import edilecek)
battery_data_ram = defaultdict(dict)  # {arm: {k: {dtype: value}}}
data_lock = threading.Lock()  # Thread-safe erişim için

# Armslavecount verilerini tutmak için
arm_slave_counts = {1: 0, 2: 0, 3: 7, 4: 0}  # Her kol için batarya sayısı (default değerler)
arm_slave_counts_lock = threading.Lock()  # Thread-safe erişim için

# Alarm verilerini tutmak için
# {arm: {battery: {alarm_type: 0/1}}}
# alarm_type: 1=PozitifKutupBasi, 2=NegatifKutupBasi, 3=DusukGerilimUyari, 4=DusukGerilimAlarm, 5=YuksekGerilimUyari, 6=YuksekGerilimAlarm, 7=ModulSicaklik
alarm_data_ram = defaultdict(dict)  # {arm: {battery: {alarm_type: 0/1}}}
alarm_lock = threading.Lock()  # Thread-safe erişim için

# Status verilerini tutmak için
status_data_ram = defaultdict(dict)  # {arm: {battery: status}}
status_lock = threading.Lock()  # Thread-safe erişim için

# Kol alarmlarını tutmak için
# {arm: {alarm_type: 0/1}}
# alarm_type: 1=Sicaklik, 2=Nem, 3=Baglanti, 4=Guc
arm_alarm_data_ram = defaultdict(dict)  # {arm: {alarm_type: 0/1}}
arm_alarm_lock = threading.Lock()  # Thread-safe erişim için

def get_battery_data_ram(arm=None, k=None, dtype=None):
    """RAM'den batarya verilerini oku"""
    with data_lock:
        if arm is None:
            return dict(battery_data_ram)
        elif k is None:
            return dict(battery_data_ram.get(arm, {}))
        elif dtype is None:
            return dict(battery_data_ram.get(arm, {}).get(k, {}))
        else:
            return battery_data_ram.get(arm, {}).get(k, {}).get(dtype, None)

def get_arm_slave_count(arm_num):
    """Kol batarya sayısını getir"""
    with arm_slave_counts_lock:
        return arm_slave_counts.get(arm_num, 0)

def get_battery_status(arm_num, battery_num):
    """Batarya status'unu getir"""
    with status_lock:
        return status_data_ram.get(arm_num, {}).get(battery_num, 0)

def get_alarm_data(arm_num, battery_num, alarm_type):
    """Alarm verisini getir"""
    with alarm_lock:
        return alarm_data_ram.get(arm_num, {}).get(battery_num, {}).get(alarm_type, 0)

def set_alarm_data(arm_num, battery_num, alarm_type, value):
    """Alarm verisini set et (0=alarm yok, 1=alarm var)"""
    with alarm_lock:
        if arm_num not in alarm_data_ram:
            alarm_data_ram[arm_num] = {}
        if battery_num not in alarm_data_ram[arm_num]:
            alarm_data_ram[arm_num][battery_num] = {}
        alarm_data_ram[arm_num][battery_num][alarm_type] = value

def update_alarm_from_error_codes(arm_num, battery_num, error_msb, error_lsb):
    """Error kodlarından alarm verilerini güncelle"""
    with alarm_lock:
        if arm_num not in alarm_data_ram:
            alarm_data_ram[arm_num] = {}
        if battery_num not in alarm_data_ram[arm_num]:
            alarm_data_ram[arm_num][battery_num] = {}
        
        # MSB kontrolü
        if error_msb == 1:
            alarm_data_ram[arm_num][battery_num][1] = 1  # Pozitif kutup başı alarmı
        elif error_msb == 2:
            alarm_data_ram[arm_num][battery_num][2] = 1  # Negatif kutup başı alarmı
        
        # LSB kontrolü
        if error_lsb == 4:
            alarm_data_ram[arm_num][battery_num][3] = 1  # Düşük gerilim uyarısı
        elif error_lsb == 8:
            alarm_data_ram[arm_num][battery_num][4] = 1  # Düşük gerilim alarmı
        elif error_lsb == 16:
            alarm_data_ram[arm_num][battery_num][5] = 1  # Yüksek gerilim uyarısı
        elif error_lsb == 32:
            alarm_data_ram[arm_num][battery_num][6] = 1  # Yüksek gerilim alarmı
        elif error_lsb == 64:
            alarm_data_ram[arm_num][battery_num][7] = 1  # Modül sıcaklık alarmı

def get_arm_alarm_data(arm_num, alarm_type):
    """Kol alarm verisini getir"""
    with arm_alarm_lock:
        return arm_alarm_data_ram.get(arm_num, {}).get(alarm_type, 0)

def set_arm_alarm_data(arm_num, alarm_type, value):
    """Kol alarm verisini set et (0=alarm yok, 1=alarm var)"""
    with arm_alarm_lock:
        if arm_num not in arm_alarm_data_ram:
            arm_alarm_data_ram[arm_num] = {}
        arm_alarm_data_ram[arm_num][alarm_type] = value

def update_arm_alarm_from_error_codes(arm_num, error_msb):
    """Error kodlarından kol alarm verilerini güncelle"""
    with arm_alarm_lock:
        if arm_num not in arm_alarm_data_ram:
            arm_alarm_data_ram[arm_num] = {}
        
        # MSB kontrolü (kol alarmları)
        if error_msb == 1:
            arm_alarm_data_ram[arm_num][1] = 1  # Kol sıcaklık alarmı
        elif error_msb == 2:
            arm_alarm_data_ram[arm_num][2] = 1  # Kol nem alarmı
        elif error_msb == 3:
            arm_alarm_data_ram[arm_num][3] = 1  # Kol bağlantı hatası
        elif error_msb == 4:
            arm_alarm_data_ram[arm_num][4] = 1  # Kol güç hatası
        elif error_msb == 0:
            # Kol alarmı düzeldi - tüm alarmları sıfırla
            arm_alarm_data_ram[arm_num] = {1: 0, 2: 0, 3: 0, 4: 0}

def parse_oid(oid_str):
    """OID'yi parse et"""
    try:
        oid_parts = oid_str.split('.')
        
        # Kol verileri: .1.3.6.1.4.1.1001.{KOL}.{VERİ_TİPİ}
        if len(oid_parts) >= 8 and oid_parts[6] == '1001':
            arm_num = int(oid_parts[7])
            if len(oid_parts) == 9:  # Kol verisi
                data_type = int(oid_parts[8])
                return {'type': 'arm', 'arm': arm_num, 'data_type': data_type}
            elif len(oid_parts) == 11:  # Batarya verisi
                battery_num = int(oid_parts[9])
                data_type = int(oid_parts[10])
                return {'type': 'battery', 'arm': arm_num, 'battery': battery_num, 'data_type': data_type}
            elif len(oid_parts) == 10:  # Status verisi
                battery_num = int(oid_parts[9])
                return {'type': 'status', 'arm': arm_num, 'battery': battery_num}
            elif len(oid_parts) == 10 and oid_parts[8] == '7':  # Kol alarm verisi
                alarm_type = int(oid_parts[9])
                return {'type': 'arm_alarm', 'arm': arm_num, 'alarm_type': alarm_type}
            elif len(oid_parts) == 12:  # Batarya alarm verisi
                battery_num = int(oid_parts[9])
                alarm_type = int(oid_parts[11])
                return {'type': 'battery_alarm', 'arm': arm_num, 'battery': battery_num, 'alarm_type': alarm_type}
        
        return None
    except (ValueError, IndexError):
        return None

async def snmp_request_handler(snmpEngine, stateReference, varBinds, cbCtx):
    """SNMP isteklerini işle"""
    print(f"📡 SNMP İsteği alındı: {varBinds}")
    
    for varBind in varBinds:
        oid = str(varBind[0])
        print(f"🔍 OID: {oid}")
        
        parsed_oid = parse_oid(oid)
        
        if parsed_oid is None:
            print(f"❌ Geçersiz OID formatı: {oid}")
            varBind[1] = 'No Such Object'
            continue
        
        try:
            if parsed_oid['type'] == 'arm':
                # Kol verileri
                arm_num = parsed_oid['arm']
                data_type = parsed_oid['data_type']
                
                if arm_num < 1 or arm_num > 4:
                    varBind[1] = 'No Such Object'
                    continue
                
                # k=2 (kol verileri) için veri al
                value = get_battery_data_ram(arm_num, 2, data_type)
                if value is not None:
                    varBind[1] = value['value']
                else:
                    varBind[1] = 0.0
                    
            elif parsed_oid['type'] == 'battery':
                # Batarya verileri
                arm_num = parsed_oid['arm']
                battery_num = parsed_oid['battery']
                data_type = parsed_oid['data_type']
                
                if arm_num < 1 or arm_num > 4:
                    varBind[1] = 'No Such Object'
                    continue
                
                if battery_num > 120:
                    varBind[1] = 'No Such Object'
                    continue
                
                # armslavecounts kontrolü
                max_batteries = get_arm_slave_count(arm_num)
                if battery_num > max_batteries:
                    varBind[1] = 'No Such Object'
                    continue
                
                # k değeri hesapla (battery_num + 2)
                k_value = battery_num + 2
                value = get_battery_data_ram(arm_num, k_value, data_type)
                if value is not None:
                    varBind[1] = value['value']
                else:
                    varBind[1] = 0.0
                    
            elif parsed_oid['type'] == 'status':
                # Status verileri
                arm_num = parsed_oid['arm']
                battery_num = parsed_oid['battery']
                
                if arm_num < 1 or arm_num > 4:
                    varBind[1] = 'No Such Object'
                    continue
                
                if battery_num > 120:
                    varBind[1] = 'No Such Object'
                    continue
                
                # armslavecounts kontrolü
                max_batteries = get_arm_slave_count(arm_num)
                if battery_num > max_batteries:
                    varBind[1] = 'No Such Object'
                    continue
                
                status = get_battery_status(arm_num, battery_num)
                varBind[1] = status
                
            elif parsed_oid['type'] == 'arm_alarm':
                # Kol alarm verileri
                arm_num = parsed_oid['arm']
                alarm_type = parsed_oid['alarm_type']
                
                if arm_num < 1 or arm_num > 4:
                    varBind[1] = 'No Such Object'
                    continue
                
                if alarm_type < 1 or alarm_type > 4:
                    varBind[1] = 'No Such Object'
                    continue
                
                alarm_value = get_arm_alarm_data(arm_num, alarm_type)
                varBind[1] = alarm_value
                
            elif parsed_oid['type'] == 'battery_alarm':
                # Batarya alarm verileri
                arm_num = parsed_oid['arm']
                battery_num = parsed_oid['battery']
                alarm_type = parsed_oid['alarm_type']
                
                if arm_num < 1 or arm_num > 4:
                    varBind[1] = 'No Such Object'
                    continue
                
                if battery_num > 120:
                    varBind[1] = 'No Such Object'
                    continue
                
                if alarm_type < 1 or alarm_type > 7:
                    varBind[1] = 'No Such Object'
                    continue
                
                # armslavecounts kontrolü
                max_batteries = get_arm_slave_count(arm_num)
                if battery_num > max_batteries:
                    varBind[1] = 'No Such Object'
                    continue
                
                alarm_value = get_alarm_data(arm_num, battery_num, alarm_type)
                varBind[1] = alarm_value
            
            print(f"✅ Değer bulundu: {varBind[1]}")
            
        except Exception as e:
            print(f"❌ Hata: {e}")
            varBind[1] = 'No Such Object'
    
    print(f"📤 SNMP Cevabı gönderiliyor: {varBinds}")

async def start_snmp_server():
    """SNMP Server'ı başlat"""
    print("🚀 SNMP Server Başlatılıyor...")
    print(f"📡 Dinlenen adres: {host}:{port}")
    print("=" * 50)
    
    try:
        # SNMP Engine oluştur
        snmpEngine = SnmpEngine()
        
        # Transport oluştur
        transport = await UdpTransportTarget.create((host, port))
        
        # SNMP Server'ı başlat
        await snmpEngine.msgAndPduDsp.router.msgRoutingTable.addRouting(
            snmpEngine.msgAndPduDsp.router.msgRoutingTable.getRoutingInfo(
                'snmpv2c'
            )[0],
            transport
        )
        
        print("✅ SNMP Server başlatıldı!")
        print("📡 İstekler bekleniyor...")
        print("Ctrl+C ile durdurun")
        
        # Sonsuz döngü
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 SNMP Server durduruluyor...")
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    asyncio.run(start_snmp_server())