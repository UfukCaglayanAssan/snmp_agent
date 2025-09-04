#!/usr/bin/env python3
"""
SNMP Server - PySNMP v7.1 ile SNMP Agent
"""

import asyncio
from pysnmp.hlapi.v3arch.asyncio import *

# SNMP Server ayarları
community_string = 'public'
host = '0.0.0.0'  # Tüm arayüzlerde dinle
port = 161

# RAM'de veri tutma sistemi
battery_data = {
    '1.3.6.1.4.1.99999.1.1.1.0': 5,  # totalBatteryCount
    '1.3.6.1.4.1.99999.1.1.2.0': 3,  # totalArmCount
    '1.3.6.1.4.1.99999.1.1.3.0': 1,  # systemStatus
    '1.3.6.1.4.1.99999.1.1.4.0': '2025-01-01 12:00:00',  # lastUpdateTime
    '1.3.6.1.4.1.99999.2.2.0': 13,  # dataCount
    '1.3.6.1.4.1.99999.4.1.3.10.0': 12.5,  # Arm 1, k=3, dtype=10 (Gerilim)
    '1.3.6.1.4.1.99999.4.2.4.11.0': 85.0,  # Arm 2, k=4, dtype=11 (SOH)
    '1.3.6.1.4.1.99999.4.3.3.12.0': 25.0,  # Arm 3, k=3, dtype=12 (NTC1)
    '1.3.6.1.4.1.99999.4.3.3.126.0': 75.5,  # Arm 3, k=3, dtype=126 (SOC)
}

async def snmp_request_handler(snmpEngine, stateReference, varBinds, cbCtx):
    """SNMP isteklerini işle"""
    print(f"📡 SNMP İsteği alındı: {varBinds}")
    
    for varBind in varBinds:
        oid = str(varBind[0])
        print(f"🔍 OID: {oid}")
        
        if oid in battery_data:
            value = battery_data[oid]
            print(f"✅ Değer bulundu: {value}")
            # Cevap döndür
            varBind[1] = value
        else:
            print(f"❌ OID bulunamadı: {oid}")
            # Hata döndür
            varBind[1] = 'No Such Object'
    
    print(f"📤 SNMP Cevabı gönderiliyor: {varBinds}")

async def start_snmp_server():
    """SNMP Server'ı başlat"""
    print("🚀 SNMP Server Başlatılıyor...")
    print(f"📡 Dinlenen adres: {host}:{port}")
    print("=" * 50)
    
    try:
        # SNMP Engine oluştur
        snmpEngine = SnmpEngine()
        
        # Transport oluştur
        transport = await UdpTransportTarget.create((host, port))
        
        # SNMP Server'ı başlat
        await snmpEngine.msgAndPduDsp.router.msgRoutingTable.addRouting(
            snmpEngine.msgAndPduDsp.router.msgRoutingTable.getRoutingInfo(
                'snmpv2c'
            )[0],
            transport
        )
        
        print("✅ SNMP Server başlatıldı!")
        print("📡 İstekler bekleniyor...")
        print("Ctrl+C ile durdurun")
        
        # Sonsuz döngü
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 SNMP Server durduruluyor...")
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    asyncio.run(start_snmp_server())