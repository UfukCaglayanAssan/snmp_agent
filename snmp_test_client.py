#!/usr/bin/env python3
"""
SNMP Test Client - pysnmp ile test
"""

import asyncio
from pysnmp.hlapi.v3arch import *

# SNMP ayarları
community_string = 'public'
host = 'localhost'
port = 161

async def snmp_get(oid):
    """SNMP GET isteği gönder"""
    try:
        result = await get_cmd(
            SnmpEngine(),
            CommunityData(community_string),
            UdpTransportTarget.create((host, port)),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lookupMib=False,
            lexicographicMode=False,
        )
        return result
    except Exception as e:
        print(f"SNMP GET hatası: {e}")
        return None

async def snmp_walk(oid):
    """SNMP WALK isteği gönder"""
    try:
        result = await next_cmd(
            SnmpEngine(),
            CommunityData(community_string),
            UdpTransportTarget.create((host, port)),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lookupMib=False,
            lexicographicMode=False,
        )
        return result
    except Exception as e:
        print(f"SNMP WALK hatası: {e}")
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

async def test_battery_data_oids():
    """Batarya veri OID'lerini test et"""
    print("\n📊 Batarya Veri OID'leri Test Ediliyor...")
    print("=" * 50)
    
    # Test OID'leri
    test_oids = [
        "1.3.6.1.4.1.99999.4.1.3.10.0",   # Arm 1, k=3, dtype=10 (Gerilim)
        "1.3.6.1.4.1.99999.4.2.4.11.0",   # Arm 2, k=4, dtype=11 (SOH)
        "1.3.6.1.4.1.99999.4.3.3.12.0",   # Arm 3, k=3, dtype=12 (NTC1)
        "1.3.6.1.4.1.99999.4.3.3.126.0",  # Arm 3, k=3, dtype=126 (SOC)
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
    
    # Batarya veri OID'lerini test et
    await test_battery_data_oids()
    
    print("\n" + "=" * 50)
    print("🏁 Test tamamlandı!")

if __name__ == "__main__":
    asyncio.run(main())
