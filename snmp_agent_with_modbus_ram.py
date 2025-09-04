#!/usr/bin/env python3
"""
SNMP Agent - Modbus TCP Server RAM Sistemi ile Entegre
Modbus TCP Server'daki RAM veri yapısını SNMP ile sunar
"""

import sys
import time
import datetime
import threading
from collections import defaultdict
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

# Modbus TCP Server'dan RAM veri yapısını import et
# Bu değişkenler Modbus TCP Server ile aynı olmalı
battery_data_ram = defaultdict(dict)  # {arm: {k: {dtype: value}}}
data_lock = threading.Lock()  # Thread-safe erişim için

def update_battery_data_ram(arm, k, dtype, value):
    """RAM'deki batarya verilerini güncelle - Modbus TCP Server ile aynı"""
    with data_lock:
        if arm not in battery_data_ram:
            battery_data_ram[arm] = {}
        if k not in battery_data_ram[arm]:
            battery_data_ram[arm][k] = {}
        
        battery_data_ram[arm][k][dtype] = {
            'value': value,
            'timestamp': int(time.time() * 1000)
        }
        
        print(f"SNMP RAM'e kaydedildi: Arm={arm}, k={k}, dtype={dtype}, value={value}")

def get_battery_data_ram(arm=None, k=None, dtype=None):
    """RAM'den batarya verilerini oku - Modbus TCP Server ile aynı"""
    with data_lock:
        if arm is None:
            result = dict(battery_data_ram)
            return result
        elif k is None:
            result = dict(battery_data_ram.get(arm, {}))
            return result
        elif dtype is None:
            result = dict(battery_data_ram.get(arm, {}).get(k, {}))
            return result
        else:
            result = battery_data_ram.get(arm, {}).get(k, {}).get(dtype, None)
            return result

def start_snmp_agent_with_modbus_ram():
    """SNMP Agent başlat - Modbus TCP Server RAM sistemi ile"""
    print("🚀 SNMP Agent Başlatılıyor...")
    print("📊 Modbus TCP Server RAM Sistemi ile Entegre")
    print("=" * 50)
    
    try:
        # Create SNMP engine
        snmpEngine = engine.SnmpEngine()
        print("✅ SNMP Engine oluşturuldu")

        # Transport setup - UDP over IPv4
        config.add_transport(
            snmpEngine, udp.DOMAIN_NAME, udp.UdpTransport().open_server_mode(("127.0.0.1", 1161))
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
                print(f"🔍 MIB OID sorgusu: {oid}")
                
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
                            
                            print(f"🔍 Debug: arm={arm}, k={k}, dtype={dtype}")
                            data = get_battery_data_ram(arm, k, dtype)
                            print(f"🔍 Debug: data={data}")
                            if data:
                                print(f"🔍 Debug: value={data['value']}")
                                return self.getSyntax().clone(str(data['value']))
                            print(f"🔍 Debug: No data found, returning 0")
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
        for arm in range(1, 5):  # 1, 2, 3, 4 (Modbus TCP Server ile aynı)
            for k in range(2, 6):  # 2, 3, 4, 5 (k=2 arm verisi, k>2 batarya verisi)
                for dtype in range(10, 15):  # 10, 11, 12, 13, 14 (Modbus TCP Server ile aynı)
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

        # Test verileri ekle - Modbus TCP Server formatında
        print("📊 Test verileri ekleniyor...")
        update_battery_data_ram(1, 2, 10, 2.5)    # Arm1, k=2 (arm), dtype=10 (akım)
        update_battery_data_ram(1, 2, 11, 65.0)   # Arm1, k=2 (arm), dtype=11 (nem)
        update_battery_data_ram(1, 2, 12, 25.0)   # Arm1, k=2 (arm), dtype=12 (ntc1)
        update_battery_data_ram(1, 2, 13, 26.0)   # Arm1, k=2 (arm), dtype=13 (ntc2)
        
        update_battery_data_ram(1, 3, 10, 12.5)   # Arm1, k=3 (batarya), dtype=10 (gerilim)
        update_battery_data_ram(1, 3, 11, 85.0)   # Arm1, k=3 (batarya), dtype=11 (soh)
        update_battery_data_ram(1, 3, 12, 25.0)   # Arm1, k=3 (batarya), dtype=12 (ntc1)
        update_battery_data_ram(1, 3, 13, 26.0)   # Arm1, k=3 (batarya), dtype=13 (ntc2)
        update_battery_data_ram(1, 3, 126, 75.5)  # Arm1, k=3 (batarya), dtype=126 (soc)
        
        update_battery_data_ram(2, 4, 10, 13.2)   # Arm2, k=4 (batarya), dtype=10 (gerilim)
        update_battery_data_ram(2, 4, 11, 90.0)   # Arm2, k=4 (batarya), dtype=11 (soh)
        update_battery_data_ram(2, 4, 12, 28.0)   # Arm2, k=4 (batarya), dtype=12 (ntc1)
        update_battery_data_ram(2, 4, 13, 29.0)   # Arm2, k=4 (batarya), dtype=13 (ntc2)
        update_battery_data_ram(2, 4, 126, 80.0)  # Arm2, k=4 (batarya), dtype=126 (soc)
        print("✅ Test verileri eklendi")

        print("🚀 SNMP Agent başlatılıyor...")
        print("📡 Port 1161'de dinleniyor...")
        print("Ctrl+C ile durdurun")
        print("=" * 50)
        print("Test OID'leri:")
        print("1.3.6.5.1.0  - Python bilgisi")
        print("1.3.6.5.2.0  - Batarya sayısı")
        print("1.3.6.5.3.0  - Kol sayısı")
        print("1.3.6.5.4.0  - Sistem durumu")
        print("1.3.6.5.5.0  - Son güncelleme")
        print("1.3.6.5.6.0  - Veri sayısı")
        print("=" * 50)
        print("Modbus TCP Server RAM Verileri:")
        print("1.3.6.5.10.1.2.10.0  - Arm1, k=2 (arm), dtype=10 (akım)")
        print("1.3.6.5.10.1.2.11.0  - Arm1, k=2 (arm), dtype=11 (nem)")
        print("1.3.6.5.10.1.3.10.0  - Arm1, k=3 (batarya), dtype=10 (gerilim)")
        print("1.3.6.5.10.1.3.11.0  - Arm1, k=3 (batarya), dtype=11 (soh)")
        print("1.3.6.5.10.1.3.126.0 - Arm1, k=3 (batarya), dtype=126 (soc)")
        print("1.3.6.5.10.2.4.10.0  - Arm2, k=4 (batarya), dtype=10 (gerilim)")
        print("1.3.6.5.10.2.4.11.0  - Arm2, k=4 (batarya), dtype=11 (soh)")
        print("1.3.6.5.10.2.4.126.0 - Arm2, k=4 (batarya), dtype=126 (soc)")
        print("=" * 50)
        print("Test komutları:")
        print("snmpget -v2c -c public localhost:1161 1.3.6.5.2.0")
        print("snmpget -v2c -c public localhost:1161 1.3.6.5.10.1.2.10.0")
        print("snmpget -v2c -c public localhost:1161 1.3.6.5.10.1.3.10.0")
        print("snmpwalk -v2c -c public localhost:1161 1.3.6.5")
        print("=" * 50)

        # Run I/O dispatcher which would receive queries and send responses
        try:
            snmpEngine.open_dispatcher()
        except:
            snmpEngine.close_dispatcher()
            raise
        
    except KeyboardInterrupt:
        print("\n🛑 SNMP Agent durduruluyor...")
        snmpEngine.close_dispatcher()
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_snmp_agent_with_modbus_ram()
