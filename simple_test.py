#!/usr/bin/env python3
"""
Basit SNMP Test - pysnmp ile
"""

import asyncio
from pysnmp.hlapi.v3arch.asyncio import *

async def test_snmp():
    """SNMP test et"""
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
            # UdpTransportTarget.create() await edilmeli
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
            
            # Result'ı iterate et
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

if __name__ == "__main__":
    asyncio.run(test_snmp())

