#!/usr/bin/env python3
"""
SNMP Test Client - PySNMP v7.1 Dokümantasyonuna Göre Düzeltilmiş
"""

import asyncio
from pysnmp.hlapi.v3arch.asyncio import *

async def test_snmp():
    """SNMP test et - PySNMP v7.1 dokümantasyonuna göre"""
    print("🧪 SNMP Test Başlatılıyor...")
    print("=" * 50)
    
    # Test OID'leri
    test_oids = [
        "1.3.6.1.2.1.1.1.0",  # SysDescr
        "1.3.6.1.2.1.1.2.0",  # SysObjectID
        "1.3.6.1.2.1.1.3.0",  # SysUpTime
        "1.3.6.1.4.1.99999.1.1.1.0",  # totalBatteryCount
        "1.3.6.1.4.1.99999.1.1.2.0",  # totalArmCount
        "1.3.6.1.4.1.99999.1.1.3.0",  # systemStatus
    ]
    
    for oid in test_oids:
        print(f"\n📡 Testing: {oid}")
        try:
            # PySNMP v7.1 dokümantasyonuna göre doğru kullanım
            transport = await UdpTransportTarget.create(('localhost', 161))
            
            result = await get_cmd(
                SnmpEngine(),
                CommunityData('public'),
                transport,
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lookupMib=False,
                lexicographicMode=False,
            )
            
            # Async iterator kullan
            async for (errorIndication, errorStatus, errorIndex, varBinds) in result:
                if errorIndication:
                    print(f"❌ ERROR: {errorIndication}")
                elif errorStatus:
                    print(f"❌ ERROR: {errorStatus.prettyPrint()}")
                else:
                    for varBind in varBinds:
                        print(f"✅ SUCCESS: {varBind.prettyPrint()}")
                        
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test tamamlandı!")

async def test_snmp_walk():
    """SNMP WALK test et"""
    print("\n🔄 SNMP WALK Test Başlatılıyor...")
    print("=" * 50)
    
    try:
        transport = await UdpTransportTarget.create(('localhost', 161))
        
        result = await next_cmd(
            SnmpEngine(),
            CommunityData('public'),
            transport,
            ContextData(),
            ObjectType(ObjectIdentity('1.3.6.1.2.1.1')),
            lookupMib=False,
            lexicographicMode=False,
        )
        
        print("📊 SNMP WALK Sonuçları:")
        async for (errorIndication, errorStatus, errorIndex, varBinds) in result:
            if errorIndication:
                print(f"❌ ERROR: {errorIndication}")
                break
            elif errorStatus:
                print(f"❌ ERROR: {errorStatus.prettyPrint()}")
                break
            else:
                for varBind in varBinds:
                    print(f"✅ {varBind.prettyPrint()}")
                    
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

async def main():
    """Ana fonksiyon"""
    print("🚀 PySNMP v7.1 Test Client Başlatılıyor...")
    print("=" * 50)
    
    # SNMP GET test
    await test_snmp()
    
    # SNMP WALK test
    await test_snmp_walk()
    
    print("\n" + "=" * 50)
    print("🏁 Tüm testler tamamlandı!")

if __name__ == "__main__":
    asyncio.run(main())
