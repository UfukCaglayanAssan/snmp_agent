#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Script - Alarm Trap Sistemi Test
Kol ve batarya alarmlarını simüle eder
"""

import time
import sys
import os

# Modbus server'ı import et
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'modbus'))
from modbus_tcp_server import set_arm_alarm_data, set_battery_alarm_data, get_arm_alarm_data, get_battery_alarm_data

def test_arm_alarms():
    """Kol alarmlarını test et"""
    print("🧪 Kol Alarm Testi Başlatılıyor...")
    print("=" * 50)
    
    # Kol 1 alarmı ekle
    print("1️⃣ Kol 1 alarmı ekleniyor...")
    set_arm_alarm_data(1, "Kol 1 Yüksek Sıcaklık Alarmı")
    time.sleep(2)
    
    # Kol 2 alarmı ekle
    print("2️⃣ Kol 2 alarmı ekleniyor...")
    set_arm_alarm_data(2, "Kol 2 Düşük Gerilim Alarmı")
    time.sleep(2)
    
    # Kol 3 alarmı ekle
    print("3️⃣ Kol 3 alarmı ekleniyor...")
    set_arm_alarm_data(3, "Kol 3 Yüksek Akım Alarmı")
    time.sleep(2)
    
    # Kol 1 alarmını çöz
    print("✅ Kol 1 alarmı çözülüyor...")
    set_arm_alarm_data(1, "")
    time.sleep(2)
    
    # Kol 2 alarmını çöz
    print("✅ Kol 2 alarmı çözülüyor...")
    set_arm_alarm_data(2, "")
    time.sleep(2)
    
    print("✅ Kol Alarm Testi Tamamlandı!")

def test_battery_alarms():
    """Batarya alarmlarını test et"""
    print("\n🧪 Batarya Alarm Testi Başlatılıyor...")
    print("=" * 50)
    
    # Kol 1, Batarya 5 alarmı
    print("1️⃣ Kol 1, Batarya 5 alarmı ekleniyor...")
    set_battery_alarm_data(1, 5, "Batarya 1-5 Yüksek Sıcaklık")
    time.sleep(2)
    
    # Kol 2, Batarya 3 alarmı
    print("2️⃣ Kol 2, Batarya 3 alarmı ekleniyor...")
    set_battery_alarm_data(2, 3, "Batarya 2-3 Düşük Gerilim")
    time.sleep(2)
    
    # Kol 3, Batarya 8 alarmı
    print("3️⃣ Kol 3, Batarya 8 alarmı ekleniyor...")
    set_battery_alarm_data(3, 8, "Batarya 3-8 Yüksek Akım")
    time.sleep(2)
    
    # Kol 1, Batarya 5 alarmını çöz
    print("✅ Kol 1, Batarya 5 alarmı çözülüyor...")
    set_battery_alarm_data(1, 5, "")
    time.sleep(2)
    
    # Kol 2, Batarya 3 alarmını çöz
    print("✅ Kol 2, Batarya 3 alarmı çözülüyor...")
    set_battery_alarm_data(2, 3, "")
    time.sleep(2)
    
    print("✅ Batarya Alarm Testi Tamamlandı!")

def test_mixed_alarms():
    """Karışık alarm testi"""
    print("\n🧪 Karışık Alarm Testi Başlatılıyor...")
    print("=" * 50)
    
    # Aynı anda kol ve batarya alarmları
    print("🚨 Aynı anda kol ve batarya alarmları...")
    set_arm_alarm_data(1, "Kol 1 Kritik Alarm")
    set_battery_alarm_data(1, 2, "Batarya 1-2 Kritik Alarm")
    set_battery_alarm_data(2, 4, "Batarya 2-4 Kritik Alarm")
    time.sleep(3)
    
    # Tüm alarmları çöz
    print("✅ Tüm alarmlar çözülüyor...")
    set_arm_alarm_data(1, "")
    set_battery_alarm_data(1, 2, "")
    set_battery_alarm_data(2, 4, "")
    time.sleep(2)
    
    print("✅ Karışık Alarm Testi Tamamlandı!")

def show_current_alarms():
    """Mevcut alarmları göster"""
    print("\n📊 Mevcut Alarm Durumu:")
    print("=" * 30)
    
    # Kol alarmları
    for arm in range(1, 5):
        alarm = get_arm_alarm_data(arm)
        if alarm:
            print(f"🚨 Kol {arm}: {alarm}")
        else:
            print(f"✅ Kol {arm}: Alarm yok")
    
    # Batarya alarmları
    print("\nBatarya Alarmları:")
    for arm in range(1, 5):
        for battery in range(1, 8):  # Maksimum 7 batarya
            alarm = get_battery_alarm_data(arm, battery)
            if alarm:
                print(f"🚨 Kol {arm}, Batarya {battery}: {alarm}")

def main():
    """Ana test fonksiyonu"""
    print("🧪 SNMP Alarm Trap Test Sistemi")
    print("=" * 50)
    print("Bu script alarm durumlarını simüle eder ve trap gönderir.")
    print("Modbus server'ın çalıştığından emin olun!")
    print("=" * 50)
    
    try:
        # Mevcut durumu göster
        show_current_alarms()
        
        # Test seçimi
        print("\n📋 Test Seçenekleri:")
        print("1. Kol Alarm Testi")
        print("2. Batarya Alarm Testi")
        print("3. Karışık Alarm Testi")
        print("4. Tüm Testler")
        print("5. Mevcut Durumu Göster")
        print("0. Çıkış")
        
        while True:
            choice = input("\nSeçiminiz (0-5): ").strip()
            
            if choice == '0':
                print("👋 Test tamamlandı!")
                break
            elif choice == '1':
                test_arm_alarms()
            elif choice == '2':
                test_battery_alarms()
            elif choice == '3':
                test_mixed_alarms()
            elif choice == '4':
                test_arm_alarms()
                test_battery_alarms()
                test_mixed_alarms()
            elif choice == '5':
                show_current_alarms()
            else:
                print("❌ Geçersiz seçim!")
            
            print("\n" + "="*50)
    
    except KeyboardInterrupt:
        print("\n⏹️  Test durduruldu!")
    except Exception as e:
        print(f"❌ Test hatası: {e}")

if __name__ == "__main__":
    main()
