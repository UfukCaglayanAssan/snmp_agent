#!/usr/bin/env python3
"""
SNMP Table Agent - PySNMP v7.1 Dokümantasyonuna Uygun
Implementing conceptual table
"""

import sys
import time
from collections import defaultdict
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

# RAM'de tablo verisi tutma sistemi
table_data = defaultdict(dict)

def update_table_data(row_index, column, value):
    """Tabloya veri ekle/güncelle"""
    table_data[row_index][column] = value

def get_table_data(row_index=None, column=None):
    """Tablodan veri oku"""
    if row_index is None:
        return dict(table_data)
    elif column is None:
        return dict(table_data.get(row_index, {}))
    else:
        return table_data.get(row_index, {}).get(column, None)

def start_snmp_table_agent():
    """SNMP Table Agent başlat - PySNMP v7.1 dokümantasyonuna uygun"""
    print("🚀 SNMP Table Agent Başlatılıyor...")
    print("📊 Implementing conceptual table")
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
        config.add_vacm_user(snmpEngine, 2, "my-area", "noAuthNoPriv", (1, 3, 6, 6))
        print("✅ VACM ayarlandı")

        # Create an SNMP context
        snmpContext = context.SnmpContext(snmpEngine)
        print("✅ SNMP Context oluşturuldu")

        # --- create custom Managed Object Instance ---
        mibBuilder = snmpContext.get_mib_instrum().get_mib_builder()

        MibTable, MibTableRow, MibTableColumn, MibScalar, MibScalarInstance = mibBuilder.import_symbols(
            "SNMPv2-SMI", "MibTable", "MibTableRow", "MibTableColumn", "MibScalar", "MibScalarInstance"
        )
        print("✅ MIB Builder oluşturuldu")

        class ExampleTableRow(MibTableRow):
            """Örnek tablo satırı"""
            def getValue(self, name, **context):
                oid = '.'.join([str(x) for x in name])
                print(f"🔍 Table OID sorgusu: {oid}")
                
                # OID'yi parse et: 1.3.6.6.1.5.{column}.{row_index}
                parts = oid.split('.')
                if len(parts) >= 6:
                    column = int(parts[5])
                    row_index = int(parts[6]) if len(parts) > 6 else 0
                    
                    data = get_table_data(row_index, column)
                    if data is not None:
                        if column == 2:  # String column
                            return self.getSyntax().clone(str(data))
                        elif column == 4:  # Integer column
                            return self.getSyntax().clone(int(data))
                        else:
                            return self.getSyntax().clone(str(data))
                    else:
                        return self.getSyntax().clone("No Such Object")
                
                return self.getSyntax().clone("No Such Object")

        # MIB Objects oluştur
        mibBuilder.export_symbols(
            "__EXAMPLE_MIB",
            # Tablo tanımı
            MibTable((1, 3, 6, 6, 1, 5)),
            ExampleTableRow((1, 3, 6, 6, 1, 5), (2,), v2c.OctetString()),  # String column
            ExampleTableRow((1, 3, 6, 6, 1, 5), (4,), v2c.Integer()),      # Integer column
        )
        print("✅ MIB Table Objects oluşturuldu")

        # --- end of Managed Object Instance initialization ----

        # Register SNMP Applications at the SNMP engine for particular SNMP context
        cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
        cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
        cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)
        print("✅ Command Responder'lar kaydedildi")

        # Register an imaginary never-ending job to keep I/O dispatcher running forever
        snmpEngine.transport_dispatcher.job_started(1)
        print("✅ Job başlatıldı")

        # Test verileri ekle
        update_table_data(97, 2, "my value")
        update_table_data(97, 4, 4)
        print("✅ Test verileri eklendi")

        print("🚀 SNMP Table Agent başlatılıyor...")
        print("📡 Port 1161'de dinleniyor...")
        print("Ctrl+C ile durdurun")
        print("=" * 50)
        print("Test OID'leri:")
        print("1.3.6.6.1.5.2.97  - String değer")
        print("1.3.6.6.1.5.4.97  - Integer değer")
        print("=" * 50)
        print("Test komutları:")
        print("snmpget -v2c -c public localhost:1161 1.3.6.6.1.5.2.97")
        print("snmpget -v2c -c public localhost:1161 1.3.6.6.1.5.4.97")
        print("snmpwalk -v2c -c public localhost:1161 1.3.6.6")
        print("=" * 50)

        # Run I/O dispatcher which would receive queries and send responses
        try:
            snmpEngine.open_dispatcher()
        except:
            snmpEngine.close_dispatcher()
            raise
        
    except KeyboardInterrupt:
        print("\n🛑 SNMP Table Agent durduruluyor...")
        snmpEngine.close_dispatcher()
    except Exception as e:
        print(f"❌ Hata: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_snmp_table_agent()
