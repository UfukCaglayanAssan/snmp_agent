#!/usr/bin/env python3
import asyncio
from pysnmp.hlapi.asyncio import *
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import cmdrsp
from pysnmp.smi import builder, view, rfc1902

# RAM verisi
batarya_sayisi = 5

async def run_agent():
    snmpEngine = engine.SnmpEngine()

    # SNMP v2c community
    config.add_v1_system(snmpEngine, "my-area", "public")

    # UDP endpoint
    config.add_transport(
        snmpEngine,
        udp.domainName,
        udp.UdpTransport().openServerMode(('0.0.0.0', 161))
    )

    # Custom MIB scalar için builder
    mibBuilder = snmpEngine.getMibBuilder()
    mibViewController = view.MibViewController(mibBuilder)

    # OID: 1.3.6.1.4.1.50000.1.0
    cpu_oid = (1,3,6,1,4,1,50000,1,0)

    # GET callback için responder
    class BatteryScalar(rfc1902.MibScalarInstance):
        def readGet(self, name, *args):
            return name, 2, rfc1902.Integer(batarya_sayisi)

    battery_scalar = BatteryScalar(cpu_oid, lambda: batarya_sayisi)

    # Cmd responders
    cmdrsp.GetCommandResponder(snmpEngine, None)
    cmdrsp.NextCommandResponder(snmpEngine, None)

    snmpEngine.transportDispatcher.jobStarted(1)
    try:
        await snmpEngine.transportDispatcher.runDispatcher()
    finally:
        snmpEngine.transportDispatcher.closeDispatcher()

if __name__ == "__main__":
    asyncio.run(run_agent())
