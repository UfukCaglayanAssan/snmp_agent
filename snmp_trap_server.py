#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SNMP Trap Server - Batarya Alarm Sistemi
Kol veya batarya alarma girerse otomatik trap gönderir
"""

import threading
import time
import json
from datetime import datetime
from pysnmp.hlapi import *
from pysnmp.entity import engine, config
from pysnmp.carrier.udp.udp import UdpTransport
from pysnmp.entity.rfc3413 import ntforg, context
from pysnmp.smi import rfc1902

class SNMPTrapServer:
    def __init__(self, trap_port=162, community='public'):
        self.trap_port = trap_port
        self.community = community
        self.running = False
        self.trap_thread = None
        
        # Alarm durumları (önceki durumları takip etmek için)
        self.previous_alarms = {
            'arm_alarms': {},  # {arm_num: alarm_description}
            'battery_alarms': {}  # {f"{arm_num}_{battery_num}": alarm_description}
        }
        
        # Trap gönderilecek hedefler
        self.trap_targets = [
            ('192.168.137.1', 162),  # Bilgisayarınız
            # ('192.168.1.100', 162),  # Başka bir sunucu
        ]
        
        print("🚨 SNMP Trap Server başlatılıyor...")
        print(f"📡 Trap Port: {trap_port}")
        print(f"🔐 Community: {community}")
        print(f"🎯 Hedefler: {self.trap_targets}")
    
    def start(self):
        """Trap server'ı başlat"""
        if self.running:
            print("⚠️  Trap server zaten çalışıyor!")
            return
        
        self.running = True
        self.trap_thread = threading.Thread(target=self._monitor_alarms, daemon=True)
        self.trap_thread.start()
        print("✅ SNMP Trap Server başlatıldı!")
    
    def stop(self):
        """Trap server'ı durdur"""
        self.running = False
        if self.trap_thread:
            self.trap_thread.join()
        print("⏹️  SNMP Trap Server durduruldu!")
    
    def _monitor_alarms(self):
        """Alarm durumlarını sürekli kontrol et"""
        print("🔍 Alarm durumları kontrol ediliyor...")
        
        while self.running:
            try:
                # Kol alarmlarını kontrol et
                self._check_arm_alarms()
                
                # Batarya alarmlarını kontrol et
                self._check_battery_alarms()
                
                # 5 saniye bekle
                time.sleep(5)
                
            except Exception as e:
                print(f"❌ Alarm kontrol hatası: {e}")
                time.sleep(10)
    
    def _check_arm_alarms(self):
        """Kol alarmlarını kontrol et"""
        try:
            # Burada gerçek alarm verilerini alacaksın
            # Şimdilik örnek veri kullanıyoruz
            current_alarms = self._get_current_arm_alarms()
            
            for arm_num, alarm_desc in current_alarms.items():
                previous_desc = self.previous_alarms['arm_alarms'].get(arm_num)
                
                # Yeni alarm mı?
                if alarm_desc and not previous_desc:
                    print(f"🚨 YENİ KOL ALARMI: Kol {arm_num} - {alarm_desc}")
                    self._send_trap('arm_alarm', arm_num, 0, alarm_desc, 'ACTIVE')
                
                # Alarm çözüldü mü?
                elif not alarm_desc and previous_desc:
                    print(f"✅ KOL ALARMI ÇÖZÜLDÜ: Kol {arm_num}")
                    self._send_trap('arm_alarm', arm_num, 0, previous_desc, 'RESOLVED')
                
                # Alarm durumunu güncelle
                self.previous_alarms['arm_alarms'][arm_num] = alarm_desc
                
        except Exception as e:
            print(f"❌ Kol alarm kontrol hatası: {e}")
    
    def _check_battery_alarms(self):
        """Batarya alarmlarını kontrol et"""
        try:
            # Burada gerçek alarm verilerini alacaksın
            # Şimdilik örnek veri kullanıyoruz
            current_alarms = self._get_current_battery_alarms()
            
            for key, alarm_desc in current_alarms.items():
                arm_num, battery_num = key.split('_')
                previous_desc = self.previous_alarms['battery_alarms'].get(key)
                
                # Yeni alarm mı?
                if alarm_desc and not previous_desc:
                    print(f"🚨 YENİ BATARYA ALARMI: Kol {arm_num}, Batarya {battery_num} - {alarm_desc}")
                    self._send_trap('battery_alarm', int(arm_num), int(battery_num), alarm_desc, 'ACTIVE')
                
                # Alarm çözüldü mü?
                elif not alarm_desc and previous_desc:
                    print(f"✅ BATARYA ALARMI ÇÖZÜLDÜ: Kol {arm_num}, Batarya {battery_num}")
                    self._send_trap('battery_alarm', int(arm_num), int(battery_num), previous_desc, 'RESOLVED')
                
                # Alarm durumunu güncelle
                self.previous_alarms['battery_alarms'][key] = alarm_desc
                
        except Exception as e:
            print(f"❌ Batarya alarm kontrol hatası: {e}")
    
    def _get_current_arm_alarms(self):
        """Mevcut kol alarmlarını al (gerçek veri kaynağından)"""
        # Burada gerçek alarm verilerini alacaksın
        # Şimdilik örnek veri döndürüyoruz
        return {
            1: "Kol 1 Yüksek Sıcaklık",
            2: None,  # Alarm yok
            3: "Kol 3 Düşük Gerilim",
            4: None   # Alarm yok
        }
    
    def _get_current_battery_alarms(self):
        """Mevcut batarya alarmlarını al (gerçek veri kaynağından)"""
        # Burada gerçek alarm verilerini alacaksın
        # Şimdilik örnek veri döndürüyoruz
        return {
            "1_5": "Batarya 1-5 Yüksek Sıcaklık",
            "1_12": None,  # Alarm yok
            "2_3": "Batarya 2-3 Düşük Gerilim",
            "3_8": "Batarya 3-8 Yüksek Akım"
        }
    
    def _send_trap(self, alarm_type, arm_num, battery_num, alarm_desc, status):
        """SNMP Trap gönder"""
        try:
            # Trap OID'leri
            if alarm_type == 'arm_alarm':
                trap_oid = f'1.3.6.1.4.1.1001.{arm_num}.7.0'
                trap_name = f"Arm {arm_num} Alarm"
            else:  # battery_alarm
                trap_oid = f'1.3.6.1.4.1.1001.{arm_num}.7.{battery_num}'
                trap_name = f"Battery {arm_num}-{battery_num} Alarm"
            
            # Trap mesajı
            trap_message = f"{trap_name}: {alarm_desc} - Status: {status}"
            
            print(f"📤 Trap gönderiliyor: {trap_message}")
            
            # Her hedefe trap gönder
            for target_ip, target_port in self.trap_targets:
                try:
                    self._send_single_trap(target_ip, target_port, trap_oid, trap_message)
                    print(f"✅ Trap gönderildi: {target_ip}:{target_port}")
                except Exception as e:
                    print(f"❌ Trap gönderme hatası {target_ip}:{target_port}: {e}")
                    
        except Exception as e:
            print(f"❌ Trap gönderme genel hatası: {e}")
    
    def _send_single_trap(self, target_ip, target_port, trap_oid, message):
        """Tek bir trap gönder"""
        try:
            # SNMP Trap gönder
            errorIndication, errorStatus, errorIndex, varBinds = next(
                sendNotification(
                    SnmpEngine(),
                    CommunityData(self.community),
                    UdpTransportTarget((target_ip, target_port)),
                    ContextData(),
                    'trap',
                    NotificationType(
                        ObjectIdentity(trap_oid),
                        [ObjectType(ObjectIdentity('1.3.6.1.4.1.1001.999.1.1'), OctetString(message))]
                    )
                )
            )
            
            if errorIndication:
                print(f"❌ Trap hatası: {errorIndication}")
            else:
                print(f"✅ Trap başarılı: {target_ip}")
                
        except Exception as e:
            print(f"❌ Trap gönderme hatası: {e}")
    
    def add_trap_target(self, ip, port=162):
        """Yeni trap hedefi ekle"""
        self.trap_targets.append((ip, port))
        print(f"➕ Yeni trap hedefi eklendi: {ip}:{port}")
    
    def remove_trap_target(self, ip, port=162):
        """Trap hedefini kaldır"""
        if (ip, port) in self.trap_targets:
            self.trap_targets.remove((ip, port))
            print(f"➖ Trap hedefi kaldırıldı: {ip}:{port}")
        else:
            print(f"⚠️  Trap hedefi bulunamadı: {ip}:{port}")

def main():
    """Ana fonksiyon"""
    print("🚨 SNMP Trap Server - Batarya Alarm Sistemi")
    print("=" * 50)
    
    # Trap server oluştur
    trap_server = SNMPTrapServer(trap_port=162, community='public')
    
    try:
        # Server'ı başlat
        trap_server.start()
        
        print("\n📋 Komutlar:")
        print("  - 'add <ip> <port>' - Yeni hedef ekle")
        print("  - 'remove <ip> <port>' - Hedef kaldır")
        print("  - 'list' - Hedefleri listele")
        print("  - 'quit' - Çıkış")
        print("\n⏳ Server çalışıyor... (Ctrl+C ile durdur)")
        
        # Kullanıcı girişi bekle
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if command == 'quit':
                    break
                elif command.startswith('add '):
                    parts = command.split()
                    if len(parts) == 3:
                        ip, port = parts[1], int(parts[2])
                        trap_server.add_trap_target(ip, port)
                    else:
                        print("❌ Kullanım: add <ip> <port>")
                elif command.startswith('remove '):
                    parts = command.split()
                    if len(parts) == 3:
                        ip, port = parts[1], int(parts[2])
                        trap_server.remove_trap_target(ip, port)
                    else:
                        print("❌ Kullanım: remove <ip> <port>")
                elif command == 'list':
                    print("🎯 Mevcut hedefler:")
                    for i, (ip, port) in enumerate(trap_server.trap_targets, 1):
                        print(f"  {i}. {ip}:{port}")
                else:
                    print("❌ Bilinmeyen komut!")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Komut hatası: {e}")
    
    except KeyboardInterrupt:
        print("\n⏹️  Durduruluyor...")
    
    finally:
        # Server'ı durdur
        trap_server.stop()
        print("👋 SNMP Trap Server kapatıldı!")

if __name__ == "__main__":
    main()
