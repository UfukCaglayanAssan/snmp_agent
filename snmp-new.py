#!/usr/bin/env python3
import asyncio
import psutil  # CPU ve RAM değerleri için
from pysnmp.hlapi.asyncio import *
from pysnmp.smi import builder, view, compiler, rfc1902
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import cmdrsp, context

# RAM verisi
ram_data = {
    "cpu_usage": 0,
    "free_memory": 0
}

# SNMP agent ayarları
snmpEngine = engine.SnmpEngine()

# SNMPv2c public community
config.addV1System(snmpEngine, "my-area", "public")

# UDP endpoint, port 161
config.addTransport(
    snmpEngine,
    udp.domainName,
    udp.UdpTransport().openServerMode(('0.0.0.0', 161))
)

# MIB context
snmpContext = context.SnmpContext(snmpEngine)

# MIB builder
mibBuilder = snmpContext.getMibInstrum().getMibBuilder()
mibViewController = view.MibViewController(mibBuilder)

# Custom OID: 1.3.6.1.4.1.50000
cpu_oid = (1,3,6,1,4,1,50000,1,0)
mem_oid = (1,3,6,1,4,1,50000,2,0)

# GET request callback
async def update_ram_data():
    while True:
        ram_data['cpu_usage'] = int(psutil.cpu_percent(interval=1))
        ram_data['free_memory'] = int(psutil.virtual_memory().available / (1024*1024))  # MB
        await asyncio.sleep(1)

# SNMP responder
class CustomScalarObject(rfc1902.MibScalarInstance):
    def __init__(self, name, value):
        self._value = value
        super().__init__(name, (0,), rfc1902.Integer32(value))

    def readGet(self, name, *args):
        return name, 2, rfc1902.Integer32(self._value())

# Scalar objeler
cpu_scalar = CustomScalarObject(cpu_oid, lambda: ram_data['cpu_usage'])
mem_scalar = CustomScalarObject(mem_oid, lambda: ram_data['free_memory'])

# Register objeler
snmpContext.registerContextName(
    None,  # default context
    cpu_scalar
)
snmpContext.registerContextName(
    None,
    mem_scalar
)

# Cmd responders
cmdrsp.GetCommandResponder(snmpEngine, snmpContext)
cmdrsp.NextCommandResponder(snmpEngine, snmpContext)
cmdrsp.SetCommandResponder(snmpEngine, snmpContext)

async def run_agent():
    asyncio.create_task(update_ram_data())
    snmpEngine.transportDispatcher.jobStarted(1)
    try:
        await snmpEngine.transportDispatcher.runDispatcher()
    finally:
        snmpEngine.transportDispatcher.closeDispatcher()

if __name__ == "__main__":
    asyncio.run(run_agent())
