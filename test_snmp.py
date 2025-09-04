#!/usr/bin/env python3
"""
SNMP Agent Test Scripti
"""

import subprocess
import time
import sys

def test_snmp_agent():
    """SNMP Agent'ı test et"""
    print("🧪 SNMP Agent Test Başlatılıyor...")
    print("=" * 50)
    
    # Test OID'leri
    test_oids = [
        "1.3.6.1.4.1.99999.1.1.1.0",  # totalBatteryCount
        "1.3.6.1.4.1.99999.1.1.2.0",  # totalArmCount
        "1.3.6.1.4.1.99999.1.1.3.0",  # systemStatus
        "1.3.6.1.4.1.99999.1.1.4.0",  # lastUpdateTime
        "1.3.6.1.4.1.99999.2.2.0",    # dataCount
    ]
    
    print("📋 Test OID'leri:")
    for oid in test_oids:
        print(f"  {oid}")
    
    print("\n🔍 SNMP Test Komutları:")
    print("=" * 50)
    
    for oid in test_oids:
        print(f"\n📡 Testing: {oid}")
        try:
            # snmpget komutu
            cmd = ["snmpget", "-v2c", "-c", "public", "localhost", oid]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print(f"✅ SUCCESS: {result.stdout.strip()}")
            else:
                print(f"❌ ERROR: {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print("⏰ TIMEOUT: SNMP isteği zaman aşımına uğradı")
        except FileNotFoundError:
            print("❌ ERROR: snmpget komutu bulunamadı. 'sudo apt install snmp snmp-mibs-downloader' kurun")
            break
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test tamamlandı!")

def test_snmpwalk():
    """snmpwalk ile test et"""
    print("\n🔄 SNMP Walk Test:")
    print("=" * 50)
    
    try:
        # Sistem bilgileri
        print("📊 Sistem Bilgileri:")
        cmd = ["snmpwalk", "-v2c", "-c", "public", "localhost", "1.3.6.1.4.1.99999.1.1"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"❌ ERROR: {result.stderr}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    print("🚀 SNMP Agent Test Scripti")
    print("=" * 50)
    
    # SNMP araçlarının kurulu olup olmadığını kontrol et
    try:
        subprocess.run(["snmpget", "--version"], capture_output=True, check=True)
        print("✅ SNMP araçları kurulu")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ SNMP araçları kurulu değil!")
        print("Kurulum için: sudo apt install snmp snmp-mibs-downloader")
        sys.exit(1)
    
    # Testleri çalıştır
    test_snmp_agent()
    test_snmpwalk()
