#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SNMP Trap Receiver - Alarm Bildirimleri Al
Raspberry Pi'den gelen alarm trap'lerini dinler ve gösterir
"""

import threading
import time
from datetime import datetime
from pysnmp.hlapi import *
from pysnmp.entity import engine, config
from pysnmp.carrier.udp.udp import UdpTransport
from pysnmp.entity.rfc3413 import ntforg, context
from pysnmp.smi import rfc1902

class SNMPTrapReceiver:
    def __init__(self, listen_port=162, community='public'):
        self.listen_port = listen_port
        self.community = community
        self.running = False
        self.receiver_thread = None
        
        print("📡 SNMP Trap Receiver başlatılıyor...")
        print(f"👂 Dinleme Portu: {listen_port}")
        print(f"🔐 Community: {community}")
    
    def start(self):
        """Trap receiver'ı başlat"""
        if self.running:
            print("⚠️  Trap receiver zaten çalışıyor!")
            return
        
        self.running = True
        self.receiver_thread = threading.Thread(target=self._listen_for_traps, daemon=True)
        self.receiver_thread.start()
        print("✅ SNMP Trap Receiver başlatıldı!")
        print("⏳ Trap'ler dinleniyor...")
    
    def stop(self):
        """Trap receiver'ı durdur"""
        self.running = False
        if self.receiver_thread:
            self.receiver_thread.join()
        print("⏹️  SNMP Trap Receiver durduruldu!")
    
    def _listen_for_traps(self):
        """Trap'leri dinle"""
        try:
            # SNMP Engine oluştur
            snmpEngine = engine.SnmpEngine()
            
            # Transport ayarla
            config.addTransport(
                snmpEngine,
                udp.domainName,
                UdpTransport().openServerMode(('0.0.0.0', self.listen_port))
            )
            
            # SNMPv2c ayarla
            config.addV1System(snmpEngine, 'my-area', self.community)
            
            # Trap handler oluştur
            def cbFun(snmpEngine, stateReference, varName, varBind, cbCtx):
                self._handle_trap(snmpEngine, stateReference, varName, varBind, cbCtx)
            
            # Trap handler'ı kaydet
            ntforg.NotificationOriginator().configure(snmpEngine, 'my-area', cbFun)
            
            print(f"🎯 Trap'ler dinleniyor: 0.0.0.0:{self.listen_port}")
            
            # Ana döngü
            snmpEngine.transportDispatcher.jobStarted(1)
            
            try:
                snmpEngine.transportDispatcher.runDispatcher()
            except Exception as e:
                if self.running:
                    print(f"❌ Trap dinleme hatası: {e}")
            
        except Exception as e:
            print(f"❌ Trap receiver başlatma hatası: {e}")
    
    def _handle_trap(self, snmpEngine, stateReference, varName, varBind, cbCtx):
        """Gelen trap'i işle"""
        try:
            # Trap bilgilerini al
            trap_oid = str(varBind[0][0])
            trap_value = str(varBind[0][1])
            
            # Zaman damgası
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Trap tipini belirle
            if '.7.0' in trap_oid:
                # Kol alarmı
                arm_num = trap_oid.split('.')[-3]
                alarm_type = "KOL ALARMI"
                location = f"Kol {arm_num}"
            elif '.7.' in trap_oid:
                # Batarya alarmı
                parts = trap_oid.split('.')
                arm_num = parts[-3]
                battery_num = parts[-1]
                alarm_type = "BATARYA ALARMI"
                location = f"Kol {arm_num}, Batarya {battery_num}"
            else:
                alarm_type = "BİLİNMEYEN ALARM"
                location = "Bilinmeyen"
            
            # Alarm durumunu belirle
            if 'ACTIVE' in trap_value:
                status = "🚨 AKTİF"
                status_color = "\033[91m"  # Kırmızı
            elif 'RESOLVED' in trap_value:
                status = "✅ ÇÖZÜLDÜ"
                status_color = "\033[92m"  # Yeşil
            else:
                status = "❓ BİLİNMEYEN"
                status_color = "\033[93m"  # Sarı
            
            # Reset color
            reset_color = "\033[0m"
            
            # Trap'i göster
            print("\n" + "="*60)
            print(f"📨 YENİ TRAP ALINDI - {timestamp}")
            print(f"🎯 OID: {trap_oid}")
            print(f"📍 Konum: {location}")
            print(f"🚨 Tip: {alarm_type}")
            print(f"📝 Mesaj: {trap_value}")
            print(f"⚡ Durum: {status_color}{status}{reset_color}")
            print("="*60)
            
            # Log dosyasına yaz
            self._log_trap(timestamp, trap_oid, location, alarm_type, trap_value, status)
            
        except Exception as e:
            print(f"❌ Trap işleme hatası: {e}")
    
    def _log_trap(self, timestamp, oid, location, alarm_type, message, status):
        """Trap'i log dosyasına yaz"""
        try:
            log_entry = f"{timestamp} | {oid} | {location} | {alarm_type} | {message} | {status}\n"
            
            with open('snmp_trap_log.txt', 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            print(f"❌ Log yazma hatası: {e}")

def main():
    """Ana fonksiyon"""
    print("📡 SNMP Trap Receiver - Alarm Bildirimleri")
    print("=" * 50)
    
    # Trap receiver oluştur
    receiver = SNMPTrapReceiver(listen_port=162, community='public')
    
    try:
        # Receiver'ı başlat
        receiver.start()
        
        print("\n📋 Komutlar:")
        print("  - 'status' - Durum kontrolü")
        print("  - 'log' - Log dosyasını göster")
        print("  - 'quit' - Çıkış")
        print("\n⏳ Receiver çalışıyor... (Ctrl+C ile durdur)")
        
        # Kullanıcı girişi bekle
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if command == 'quit':
                    break
                elif command == 'status':
                    print(f"📊 Durum: {'Çalışıyor' if receiver.running else 'Durduruldu'}")
                    print(f"👂 Port: {receiver.listen_port}")
                    print(f"🔐 Community: {receiver.community}")
                elif command == 'log':
                    try:
                        with open('snmp_trap_log.txt', 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            if lines:
                                print("\n📋 Son 10 trap:")
                                for line in lines[-10:]:
                                    print(line.strip())
                            else:
                                print("📝 Log dosyası boş")
                    except FileNotFoundError:
                        print("📝 Log dosyası bulunamadı")
                else:
                    print("❌ Bilinmeyen komut!")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Komut hatası: {e}")
    
    except KeyboardInterrupt:
        print("\n⏹️  Durduruluyor...")
    
    finally:
        # Receiver'ı durdur
        receiver.stop()
        print("👋 SNMP Trap Receiver kapatıldı!")

if __name__ == "__main__":
    main()
