# 🚨 SNMP Alarm Trap Sistemi

Bu sistem, kol ve batarya alarmlarını otomatik olarak SNMP trap olarak gönderir.

## 📋 Özellikler

- ✅ **Kol Alarmları**: Kol 1-4 için alarm durumu takibi
- ✅ **Batarya Alarmları**: Her kol için batarya alarmları takibi
- ✅ **Otomatik Trap Gönderimi**: Alarm durumu değiştiğinde otomatik trap
- ✅ **Çoklu Hedef**: Birden fazla hedefe trap gönderme
- ✅ **Durum Takibi**: Alarm aktif/çözüldü durumu takibi
- ✅ **Log Sistemi**: Tüm trap'ler log dosyasına kaydedilir

## 🚀 Kurulum

### 1. Gerekli Paketler
```bash
pip install pysnmp
```

### 2. Dosya Yapısı
```
snmp/
├── snmp_trap_server.py      # Trap gönderen server
├── snmp_trap_receiver.py    # Trap alan receiver
├── test_alarm_traps.py      # Test script'i
└── README_TRAPS.md          # Bu dosya
```

## 🔧 Kullanım

### 1. Modbus Server'ı Başlat
```bash
cd modbus
python modbus-tcp-server.py
```

### 2. Trap Receiver'ı Başlat (Bilgisayarınızda)
```bash
cd snmp
python snmp_trap_receiver.py
```

### 3. Test Script'ini Çalıştır
```bash
cd snmp
python test_alarm_traps.py
```

## 📡 Trap OID Yapısı

### Kol Alarmları
```
.1.3.6.1.4.1.1001.{KOL}.7.0
```
- **KOL**: 1-4 (Kol numarası)
- **Örnek**: `.1.3.6.1.4.1.1001.1.7.0` (Kol 1 alarmı)

### Batarya Alarmları
```
.1.3.6.1.4.1.1001.{KOL}.7.{BATARYA}
```
- **KOL**: 1-4 (Kol numarası)
- **BATARYA**: 1-120 (Batarya numarası)
- **Örnek**: `.1.3.6.1.4.1.1001.1.7.5` (Kol 1, Batarya 5 alarmı)

## 🎯 Trap Mesaj Formatı

### Aktif Alarm
```
KOL {KOL} ALARMI: {Açıklama} - Status: ACTIVE
BATARYA {KOL}-{BATARYA} ALARMI: {Açıklama} - Status: ACTIVE
```

### Çözülen Alarm
```
KOL {KOL} ALARMI: {Açıklama} - Status: RESOLVED
BATARYA {KOL}-{BATARYA} ALARMI: {Açıklama} - Status: RESOLVED
```

## ⚙️ Konfigürasyon

### Trap Hedefleri
`modbus/modbus-tcp-server.py` dosyasında:
```python
TRAP_TARGETS = [
    ('192.168.137.1', 162),  # Bilgisayarınız
    # ('192.168.1.100', 162),  # Başka bir sunucu
]
```

### Community String
```python
TRAP_COMMUNITY = 'public'
```

## 📊 Log Dosyası

Tüm trap'ler `snmp_trap_log.txt` dosyasına kaydedilir:
```
2025-09-13 16:30:15 | 1.3.6.1.4.1.1001.1.7.0 | Kol 1 | KOL ALARMI | Kol 1 Yüksek Sıcaklık - Status: ACTIVE | 🚨 AKTİF
```

## 🧪 Test Senaryoları

### 1. Kol Alarm Testi
- Kol 1, 2, 3'e alarm ekle
- Alarmları çöz
- Trap'lerin gönderildiğini kontrol et

### 2. Batarya Alarm Testi
- Farklı kollarda batarya alarmları ekle
- Alarmları çöz
- Trap'lerin gönderildiğini kontrol et

### 3. Karışık Test
- Aynı anda kol ve batarya alarmları
- Tüm alarmları çöz
- Trap'lerin gönderildiğini kontrol et

## 🔍 Sorun Giderme

### Trap Gönderilmiyor
1. Modbus server çalışıyor mu?
2. Trap hedefi doğru mu?
3. Ağ bağlantısı var mı?
4. Port 162 açık mı?

### Trap Alınmıyor
1. Receiver çalışıyor mu?
2. Port 162 dinleniyor mu?
3. Firewall engelliyor mu?
4. Community string doğru mu?

### Log Dosyası Boş
1. Receiver çalışıyor mu?
2. Dosya yazma izni var mı?
3. Disk alanı yeterli mi?

## 📈 Performans

- **Kontrol Sıklığı**: 5 saniye
- **Trap Gecikmesi**: < 1 saniye
- **Bellek Kullanımı**: Minimal
- **CPU Kullanımı**: Düşük

## 🔒 Güvenlik

- **Community String**: Varsayılan 'public' (değiştirin)
- **Port**: 162 (SNMP standart)
- **Ağ**: Sadece güvenilir ağlarda kullanın
- **Log**: Hassas bilgiler log'da olabilir

## 📞 Destek

Sorun yaşarsanız:
1. Log dosyalarını kontrol edin
2. Ağ bağlantısını test edin
3. Port durumunu kontrol edin
4. Modbus server durumunu kontrol edin
