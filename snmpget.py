import sys
import asyncio
from pysnmp.hlapi.asyncio import (
    SnmpEngine, CommunityData, ContextData,
    ObjectType, ObjectIdentity, MibScalar, MibScalarInstance,
    UdpTransportTarget, NotificationType
)
from pysnmp.entity import config
from pysnmp.entity.rfc3413 import cmdrsp

# 1️⃣ SNMP Engine oluştur
snmpEngine = SnmpEngine()

# 2️⃣ UDP transport, root gerekmiyor (yüksek port)
config.addTransport(
    snmpEngine,
    config.udp.domainName,
    config.udp.UdpTransport().openServerMode(("127.0.0.1", 1161))
)

# 3️⃣ Community setup
config.addV1System(snmpEngine, "my-area", "public")
config.addVacmUser(snmpEngine, 2, "my-area", "noAuthNoPriv", (1,3,6,5))

# 4️⃣ SNMP context oluştur
from pysnmp.entity.rfc3413 import context as snmp_context
snmpContext = snmp_context.SnmpContext(snmpEngine)

# 5️⃣ Özel MIB scalar tanımla
mibBuilder = snmpContext.getMibInstrum().getMibBuilder()
MibScalar, MibScalarInstance = mibBuilder.importSymbols(
    "SNMPv2-SMI", "MibScalar", "MibScalarInstance"
)

class PythonInfoInstance(MibScalarInstance):
    def getValue(self, name, **context):
        return self.getSyntax().clone(f"Python {sys.version} on {sys.platform}")

# OID 1.3.6.5.1 olarak tanımladık
mibBuilder.exportSymbols(
    "__MY_MIB",
    MibScalar((1,3,6,5,1), 'OctetString'),
    PythonInfoInstance((1,3,6,5,1), (0,), 'OctetString')
)

# 6️⃣ SNMP command responder
cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
cmdrsp.BulkCommandResponder(snmpEngine, snmpContext)

# 7️⃣ Dispatcher başlat (asyncio ile modern yöntem)
async def run_snmp_agent():
    snmpEngine.transportDispatcher.jobStarted(1)
    try:
        await snmpEngine.transportDispatcher.runDispatcher()
    except Exception:
        snmpEngine.transportDispatcher.closeDispatcher()
        raise

# 8️⃣ Asyncio loop ile başlat
if __name__ == "__main__":
    asyncio.run(run_snmp_agent())
