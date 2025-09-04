#!/usr/bin/env python3
"""
SNMP Agent - PySNMP v7.1 Dokümantasyonuna Uygun
Agent-Side MIB Implementations
"""

import sys
import time
import datetime
from collections import defaultdict
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

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

def start_snmp_agent():
    """SNMP Agent başlat - PySNMP v7.1 dokümantasyonuna uygun"""
    print("🚀 SNMP Agent Başlatılıyor...")
    print("📡 Agent-Side MIB Implementations")
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

        class BatteryMibScalarInstance(MibScalarInstance):
            """Batarya verileri için MIB Instance"""
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
                    return self.getSyntax().clone(str(battery_count if battery_count > 0 else 1))
                elif oid == "1.3.6.5.3.0":  # totalArmCount
                    data = get_battery_data_ram()
                    return self.getSyntax().clone(str(len(data) if data else 2))
                elif oid == "1.3.6.5.4.0":  # systemStatus
                    return self.getSyntax().clone("1")
                elif oid == "1.3.6.5.5.0":  # lastUpdateTime
                    return self.getSyntax().clone(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                elif oid == "1.3.6.5.6.0":  # dataCount
                    data = get_battery_data_ram()
                    return self.getSyntax().clone(str(sum(len(data[arm]) for arm in data) if data else 13))
                else:
                    # Gerçek batarya verileri
                    if oid.startswith("1.3.6.5.10."):
                        parts = oid.split('.')
                        if len(parts) >= 6:
                            arm = int(parts[4])
                            k = int(parts[5])
                            dtype = int(parts[6]) if len(parts) > 6 else 0
                            
                            data = get_battery_data_ram(arm, k, dtype)
                            if data:
                                return self.getSyntax().clone(str(data['value']))
                            return self.getSyntax().clone("0")
                    
                    return self.getSyntax().clone("No Such Object")

        # MIB Objects oluştur
        mibBuilder.export_symbols(
            "__BATTERY_MIB",
            # Sistem bilgileri
            MibScalar((1, 3, 6, 5, 1), v2c.OctetString()),
            BatteryMibScalarInstance((1, 3, 6, 5, 1), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 2), v2c.OctetString()),
            BatteryMibScalarInstance((1, 3, 6, 5, 2), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 3), v2c.OctetString()),
            BatteryMibScalarInstance((1, 3, 6, 5, 3), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 4), v2c.OctetString()),
            BatteryMibScalarInstance((1, 3, 6, 5, 4), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 5), v2c.OctetString()),
            BatteryMibScalarInstance((1, 3, 6, 5, 5), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 6), v2c.OctetString()),
            BatteryMibScalarInstance((1, 3, 6, 5, 6), (0,), v2c.OctetString()),
        )
        print("✅ MIB Objects oluşturuldu")

        # --- end of Managed Object Instance initialization ----

        # Register SNMP Applications at the SNMP engine for particular SNMP context
        cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
        cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
        cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)
        cmdrsp.SetCommandResponder(snmpEngine, snmpContext)
        print("✅ Command Responder'lar kaydedildi (GET/SET/GETNEXT/GETBULK)")

        # Register an imaginary never-ending job to keep I/O dispatcher running forever
        snmpEngine.transport_dispatcher.job_started(1)
        print("✅ Job başlatıldı")

        # Test verileri ekle
        update_battery_data_ram(1, 3, 10, 12.5)
        update_battery_data_ram(2, 4, 11, 85.0)
        update_battery_data_ram(3, 3, 12, 25.0)
        update_battery_data_ram(3, 3, 126, 75.5)
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
    start_snmp_agent()
