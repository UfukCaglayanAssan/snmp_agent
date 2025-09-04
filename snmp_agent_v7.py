#!/usr/bin/env python3
"""
SNMP Agent - PySNMP v7.1 Low-Level v3arch ile
Agent-Side MIB Implementations
"""

import asyncio
import sys
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

async def start_snmp_agent():
    """SNMP Agent başlat - Agent-Side MIB Implementations"""
    print("🚀 SNMP Agent Başlatılıyor...")
    print("📡 Agent-Side MIB Implementations")
    print("=" * 50)
    
    try:
        # Create SNMP engine
        snmpEngine = engine.SnmpEngine()
        print("✅ SNMP Engine oluşturuldu")

        # Transport setup - UDP over IPv4 (Port 1161 kullan)
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

        class MyStaticMibScalarInstance(MibScalarInstance):
            def getValue(self, name, **context):
                return self.getSyntax().clone(
                    f"Python {sys.version} running on a {sys.platform} platform"
                )

        mibBuilder.export_symbols(
            "__MY_MIB",
            MibScalar((1, 3, 6, 5, 1), v2c.OctetString()),
            MyStaticMibScalarInstance((1, 3, 6, 5, 1), (0,), v2c.OctetString()),
        )
        print("✅ MIB Object oluşturuldu")

        # --- end of Managed Object Instance initialization ----

        # Register SNMP Applications at the SNMP engine for particular SNMP context
        cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
        cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
        cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)
        print("✅ Command Responder'lar kaydedildi")

        # Register an imaginary never-ending job to keep I/O dispatcher running forever
        snmpEngine.transport_dispatcher.job_started(1)
        print("✅ Job başlatıldı")

        print("🚀 SNMP Agent başlatılıyor...")
        print("📡 Port 161'de dinleniyor...")
        print("Ctrl+C ile durdurun")

        # Run I/O dispatcher which would receive queries and send responses
        try:
            snmpEngine.open_dispatcher()
        except KeyboardInterrupt:
            print("\n🛑 SNMP Agent durduruluyor...")
            snmpEngine.close_dispatcher()
        except Exception as e:
            print(f"❌ Hata: {e}")
            snmpEngine.close_dispatcher()
        
    except KeyboardInterrupt:
        print("\n🛑 SNMP Agent durduruluyor...")
        snmpEngine.close_dispatcher()
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Ana fonksiyon"""
    asyncio.run(start_snmp_agent())

if __name__ == "__main__":
    main()
