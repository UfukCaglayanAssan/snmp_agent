import sys
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.proto.api import v2c

# 1️⃣ SNMP engine oluştur
snmpEngine = engine.SnmpEngine()

# 2️⃣ UDP transport, root yetkisi olmadan yüksek port kullanıyoruz
config.add_transport(
    snmpEngine,
    udp.DOMAIN_NAME,
    udp.UdpTransport().open_server_mode(("127.0.0.1", 1161))
)

# 3️⃣ SNMPv2c setup
config.add_v1_system(snmpEngine, "my-area", "public")
config.add_vacm_user(snmpEngine, 2, "my-area", "noAuthNoPriv", (1, 3, 6, 5))

# 4️⃣ SNMP context oluştur
snmpContext = context.SnmpContext(snmpEngine)

# 5️⃣ Özel MIB tanımla
mibBuilder = snmpContext.get_mib_instrum().get_mib_builder()
MibScalar, MibScalarInstance = mibBuilder.import_symbols(
    "SNMPv2-SMI", "MibScalar", "MibScalarInstance"
)

class MyStaticMibScalarInstance(MibScalarInstance):
    def getValue(self, name, **context):
        return self.getSyntax().clone(
            f"Python {sys.version} on {sys.platform}"
        )

mibBuilder.export_symbols(
    "__MY_MIB",
    MibScalar((1, 3, 6, 5, 1), v2c.OctetString()),
    MyStaticMibScalarInstance((1, 3, 6, 5, 1), (0,), v2c.OctetString()),
)

# 6️⃣ SNMP command responder’ları
cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)

# 7️⃣ Dispatcher başlat
snmpEngine.transport_dispatcher.job_started(1)
try:
    snmpEngine.transport_dispatcher.runDispatcher()
except:
    snmpEngine.transport_dispatcher.closeDispatcher()
    raise
