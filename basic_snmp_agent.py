#!/usr/bin/env python3
"""
Basit SNMP Agent - Sadece Okuma
Değişkenlerde tutulan değerleri SNMP ile sun
"""

import sys
import time
import datetime
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

# Basit değişkenler - Bu değerleri SNMP ile okuyacağız
battery_voltage = 12.5
battery_current = 2.3
battery_temperature = 25.0
system_status = "OK"
battery_count = 3
arm_count = 2

def start_basic_snmp_agent():
    """Basit SNMP Agent başlat - Sadece okuma"""
    print("🚀 Basit SNMP Agent Başlatılıyor...")
    print("📊 Sadece Okuma - Değişken Değerleri")
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

        class BasicMibScalarInstance(MibScalarInstance):
            """Basit MIB Instance - Sadece okuma"""
            def getValue(self, name, **context):
                oid = '.'.join([str(x) for x in name])
                print(f"🔍 MIB OID sorgusu: {oid}")
                
                # Sistem bilgileri
                if oid == "1.3.6.5.1.0":
                    return self.getSyntax().clone(
                        f"Python {sys.version} running on a {sys.platform} platform"
                    )
                elif oid == "1.3.6.5.2.0":  # battery_voltage
                    return self.getSyntax().clone(str(battery_voltage))
                elif oid == "1.3.6.5.3.0":  # battery_current
                    return self.getSyntax().clone(str(battery_current))
                elif oid == "1.3.6.5.4.0":  # battery_temperature
                    return self.getSyntax().clone(str(battery_temperature))
                elif oid == "1.3.6.5.5.0":  # system_status
                    return self.getSyntax().clone(str(system_status))
                elif oid == "1.3.6.5.6.0":  # battery_count
                    return self.getSyntax().clone(str(battery_count))
                elif oid == "1.3.6.5.7.0":  # arm_count
                    return self.getSyntax().clone(str(arm_count))
                elif oid == "1.3.6.5.8.0":  # timestamp
                    return self.getSyntax().clone(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    return self.getSyntax().clone("No Such Object")

        # MIB Objects oluştur
        mibBuilder.export_symbols(
            "__BASIC_MIB",
            # Sistem bilgileri
            MibScalar((1, 3, 6, 5, 1), v2c.OctetString()),
            BasicMibScalarInstance((1, 3, 6, 5, 1), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 2), v2c.OctetString()),
            BasicMibScalarInstance((1, 3, 6, 5, 2), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 3), v2c.OctetString()),
            BasicMibScalarInstance((1, 3, 6, 5, 3), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 4), v2c.OctetString()),
            BasicMibScalarInstance((1, 3, 6, 5, 4), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 5), v2c.OctetString()),
            BasicMibScalarInstance((1, 3, 6, 5, 5), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 6), v2c.OctetString()),
            BasicMibScalarInstance((1, 3, 6, 5, 6), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 7), v2c.OctetString()),
            BasicMibScalarInstance((1, 3, 6, 5, 7), (0,), v2c.OctetString()),
            
            MibScalar((1, 3, 6, 5, 8), v2c.OctetString()),
            BasicMibScalarInstance((1, 3, 6, 5, 8), (0,), v2c.OctetString()),
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

        print("🚀 Basit SNMP Agent başlatılıyor...")
        print("📡 Port 1161'de dinleniyor...")
        print("Ctrl+C ile durdurun")
        print("=" * 50)
        print("Test OID'leri:")
        print("1.3.6.5.1.0  - Python bilgisi")
        print("1.3.6.5.2.0  - Batarya voltajı")
        print("1.3.6.5.3.0  - Batarya akımı")
        print("1.3.6.5.4.0  - Batarya sıcaklığı")
        print("1.3.6.5.5.0  - Sistem durumu")
        print("1.3.6.5.6.0  - Batarya sayısı")
        print("1.3.6.5.7.0  - Kol sayısı")
        print("1.3.6.5.8.0  - Zaman damgası")
        print("=" * 50)
        print("Test komutları:")
        print("snmpget -v2c -c public localhost:1161 1.3.6.5.2.0")
        print("snmpget -v2c -c public localhost:1161 1.3.6.5.3.0")
        print("snmpget -v2c -c public localhost:1161 1.3.6.5.4.0")
        print("snmpwalk -v2c -c public localhost:1161 1.3.6.5")
        print("=" * 50)

        # Run I/O dispatcher which would receive queries and send responses
        try:
            snmpEngine.open_dispatcher()
        except:
            snmpEngine.close_dispatcher()
            raise
        
    except KeyboardInterrupt:
        print("\n🛑 Basit SNMP Agent durduruluyor...")
        snmpEngine.close_dispatcher()
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_basic_snmp_agent()
