#!/usr/bin/env python3
"""
SNMP Test Client - Düzeltilmiş pysnmp ile
"""

import asyncio
from pysnmp.hlapi.v3arch.asyncio import *

# SNMP ayarları
community_string = 'public'
host = 'localhost'
port = 161

async def snmp_get(oid):
    """SNMP GET isteği gönder"""
    try:
        # UdpTransportTarget.create() await edilmeli
        transport = await UdpTransportTarget.create((host, port))
        
        result = await get_cmd(
            SnmpEngine(),
            CommunityData(community_string),
            transport,
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lookupMib=False,
            lexicographicMode=False,
        )
        return result
    except Exception as e:
        print(f"SNMP GET hatası: {e}")
        return None

async def test_system_oids():
    """Sistem OID'lerini test et"""
    print("🧪 Sistem OID'leri Test Ediliyor...")
    print("=" * 50)
    
    # Test OID'leri
    test_oids = [
        "1.3.6.1.2.1.1.1.0",  # SysDescr
        "1.3.6.1.2.1.1.2.0",  # SysObjectID
        "1.3.6.1.2.1.1.3.0",  # SysUpTime
        "1.3.6.1.2.1.1.4.0",  # SysContact
        "1.3.6.1.2.1.1.5.0",  # SysName
        "1.3.6.1.2.1.1.6.0",  # SysLocation
    ]
    
    for oid in test_oids:
        print(f"\n📡 Testing: {oid}")
        result = await snmp_get(oid)
        if result:
            for (errorIndication, errorStatus, errorIndex, varBinds) in result:
                if errorIndication:
                    print(f"❌ ERROR: {errorIndication}")
                elif errorStatus:
                    print(f"❌ ERROR: {errorStatus.prettyPrint()}")
                else:
                    for varBind in varBinds:
                        print(f"✅ SUCCESS: {varBind.prettyPrint()}")
        else:
            print("❌ FAILED: Sonuç alınamadı")

async def test_battery_oids():
    """Batarya OID'lerini test et"""
    print("\n🔋 Batarya OID'leri Test Ediliyor...")
    print("=" * 50)
    
    # Test OID'leri
    test_oids = [
        "1.3.6.1.4.1.99999.1.1.1.0",  # totalBatteryCount
        "1.3.6.1.4.1.99999.1.1.2.0",  # totalArmCount
        "1.3.6.1.4.1.99999.1.1.3.0",  # systemStatus
        "1.3.6.1.4.1.99999.1.1.4.0",  # lastUpdateTime
        "1.3.6.1.4.1.99999.2.2.0",    # dataCount
    ]
    
    for oid in test_oids:
        print(f"\n📡 Testing: {oid}")
        result = await snmp_get(oid)
        if result:
            for (errorIndication, errorStatus, errorIndex, varBinds) in result:
                if errorIndication:
                    print(f"❌ ERROR: {errorIndication}")
                elif errorStatus:
                    print(f"❌ ERROR: {errorStatus.prettyPrint()}")
                else:
                    for varBind in varBinds:
                        print(f"✅ SUCCESS: {varBind.prettyPrint()}")
        else:
            print("❌ FAILED: Sonuç alınamadı")

async def main():
    """Ana fonksiyon"""
    print("🚀 SNMP Test Client Başlatılıyor...")
    print("=" * 50)
    
    # Sistem OID'lerini test et
    await test_system_oids()
    
    # Batarya OID'lerini test et
    await test_battery_oids()
    
    print("\n" + "=" * 50)
    print("🏁 Test tamamlandı!")

if __name__ == "__main__":
    asyncio.run(main())
