#!/usr/bin/env python3
"""
SNMP Agent - SNMPD Pass Direktifi ile
PySNMP v7.1'de SNMP server API'si yok, bu yüzden SNMPD pass kullanıyoruz
"""

import sys
import time
import datetime
from collections import defaultdict

# RAM'de veri tutma sistemi
battery_data_ram = defaultdict(dict)

def update_battery_data_ram(arm, k, dtype, value):
    """RAM'deki batarya verilerini güncelle"""
    if arm not in battery_data_ram:
        battery_data_ram[arm] = {}
    if k not in battery_data_ram[arm]:
        battery_data_ram[arm][k] = {}
    
    battery_data_ram[arm][k][dtype] = {
        'value': value,
        'timestamp': int(time.time() * 1000)
    }

def get_battery_data_ram(arm=None, k=None, dtype=None):
    """RAM'den batarya verilerini oku"""
    if arm is None:
        return dict(battery_data_ram)
    elif k is None:
        return dict(battery_data_ram.get(arm, {}))
    elif dtype is None:
        return dict(battery_data_ram.get(arm, {}).get(k, {}))
    else:
        return battery_data_ram.get(arm, {}).get(k, {}).get(dtype, None)

def get_snmp_value(oid):
    """SNMP OID için değer döndür - SNMPD pass direktifi için"""
    try:
        print(f"DEBUG: get_snmp_value called with OID: {oid}", file=sys.stderr)
        
        # OID'den .0 son ekini ve başındaki noktayı kaldır
        oid = oid.rstrip('.0').lstrip('.')
        print(f"DEBUG: OID after cleaning: {oid}", file=sys.stderr)

        # Sistem bilgileri
        if oid == "1.3.6.1.4.1.99999.1.1.1":  # totalBatteryCount
            print("DEBUG: Matched totalBatteryCount", file=sys.stderr)
            data = get_battery_data_ram()
            battery_count = 0
            for arm in data.keys():
                for k in data[arm].keys():
                    if k > 2:  # k>2 olanlar batarya verisi
                        battery_count += 1
            result = battery_count if battery_count > 0 else 1
            print(f"DEBUG: Returning battery count: {result}", file=sys.stderr)
            return result

        elif oid == "1.3.6.1.4.1.99999.1.1.2":  # totalArmCount
            print("DEBUG: Matched totalArmCount", file=sys.stderr)
            data = get_battery_data_ram()
            result = len(data) if data else 2
            print(f"DEBUG: Returning arm count: {result}", file=sys.stderr)
            return result

        elif oid == "1.3.6.1.4.1.99999.1.1.3":  # systemStatus
            print("DEBUG: Matched systemStatus", file=sys.stderr)
            result = 1  # Normal
            print(f"DEBUG: Returning system status: {result}", file=sys.stderr)
            return result

        elif oid == "1.3.6.1.4.1.99999.1.1.4":  # lastUpdateTime
            print("DEBUG: Matched lastUpdateTime", file=sys.stderr)
            result = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"DEBUG: Returning last update time: {result}", file=sys.stderr)
            return result

        # Veri sayısı
        elif oid == "1.3.6.1.4.1.99999.2.2":  # dataCount
            print("DEBUG: Matched dataCount", file=sys.stderr)
            data = get_battery_data_ram()
            result = sum(len(data[arm]) for arm in data) if data else 13
            print(f"DEBUG: Returning data count: {result}", file=sys.stderr)
            return result

        # Gerçek batarya verileri - OID'den arm, k, dtype çıkar
        elif oid.startswith("1.3.6.1.4.1.99999.4."):
            print("DEBUG: Matched real battery data OID", file=sys.stderr)
            # Format: 1.3.6.1.4.1.99999.4.{arm}.{k}.{dtype}
            parts = oid.split('.')
            if len(parts) >= 8:
                arm = int(parts[6])
                k = int(parts[7])
                dtype = int(parts[8]) if len(parts) > 8 else 0

                data = get_battery_data_ram(arm, k, dtype)
                if data:
                    result = data['value']
                    print(f"DEBUG: Returning real battery data value for OID {oid}: {result}", file=sys.stderr)
                    return result
                result = 0
                print(f"DEBUG: Returning 0 for real battery data OID {oid}", file=sys.stderr)
                return result

        else:
            print(f"DEBUG: No match for OID: {oid}", file=sys.stderr)
            return None

    except Exception as e:
        print(f"Error in get_snmp_value: {e}", file=sys.stderr)
        return None

def main():
    """Ana fonksiyon - SNMPD pass direktifi için"""
    if len(sys.argv) > 1 and sys.argv[1] == "-g":
        # SNMPD'den gelen OID isteği
        if len(sys.argv) > 2:
            oid = sys.argv[2]
            value = get_snmp_value(oid)
            
            if value is None:
                print("NONE")
            else:
                # SNMP pass formatı: OID, tip, değer
                print(oid)
                if isinstance(value, str):
                    print("STRING")
                    print(value)
                else:
                    print("INTEGER")
                    print(value)
        else:
            print("NONE")
    else:
        # Normal çalıştırma
        print("SNMP Agent başlatıldı...")
        print("=" * 40)
        
        # Test verileri ekle
        update_battery_data_ram(1, 3, 10, 12.5)
        update_battery_data_ram(2, 4, 11, 85.0)
        update_battery_data_ram(3, 3, 12, 25.0)
        update_battery_data_ram(3, 3, 126, 75.5)
        
        # Veri sayılarını göster
        print(f"Toplam kayıt: {get_snmp_value('1.3.6.1.4.1.99999.2.2')}")
        print(f"Kol sayısı: {get_snmp_value('1.3.6.1.4.1.99999.1.1.2')}")
        print(f"Batarya sayısı: {get_snmp_value('1.3.6.1.4.1.99999.1.1.1')}")
        
        print("\nSNMP Agent hazır. Veri bekleniyor...")
        print("Ctrl+C ile durdurun.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nSNMP Agent durduruldu.")

if __name__ == "__main__":
    main()
