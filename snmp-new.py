#!/usr/bin/env python3
import asyncio
from pysnmp.hlapi.asyncio import *
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import cmdrsp

# RAM'de tutulan veri
batarya_sayisi = 5

async def run_agent():
    snmpEngine = engine.SnmpEngine()

    # SNMP v2c community
    config.add_v1_system(snmpEngine, "my-area", "public")

    # UDP endpoint (161 portu root gerektirir, yoksa 1161 gibi başka port kullan)
    config.add_transport(
        snmpEngine,
        udp.DOMAIN_NAME,
        udp.UdpTransport().open_server_mode(('0.0.0.0', 161))
    )

    # CommandResponder kullanarak GET isteklerini yakalayacağız
    class BatteryResponder(cmdrsp.GetCommandResponder):
        async def handleVarBinds(self, snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
            # Gelen varbindleri düzenleyip yanıt veriyoruz
            responseVarBinds = []
            for oid, val in varBinds:
                # OID eşleşirse batarya_sayisi değerini dön
                if oid == ObjectIdentity('1.3.6.1.4.1.50000.1.0').resolveWithMib(None):
                    responseVarBinds.append((oid, Integer(batarya_sayisi)))
                else:
                    responseVarBinds.append((oid, val))
            return responseVarBinds

    # CmdResponder kayıt et
    BatteryResponder(snmpEngine, None)

    # Başlat
    snmpEngine.transportDispatcher.jobStarted(1)
    try:
        await snmpEngine.transportDispatcher.runDispatcher()
    finally:
        snmpEngine.transportDispatcher.closeDispatcher()

if __name__ == "__main__":
    asyncio.run(run_agent())
