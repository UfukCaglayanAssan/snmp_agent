#!/bin/bash
# SNMP Agent Test Komutları

echo "🧪 SNMP Agent Test Komutları"
echo "================================"

echo ""
echo "1️⃣ Sistem Bilgileri Test:"
echo "------------------------"
echo "Batarya Sayısı:"
snmpget -v2c -c public localhost 1.3.6.1.4.1.99999.1.1.1.0

echo ""
echo "Kol Sayısı:"
snmpget -v2c -c public localhost 1.3.6.1.4.1.99999.1.1.2.0

echo ""
echo "Sistem Durumu:"
snmpget -v2c -c public localhost 1.3.6.1.4.1.99999.1.1.3.0

echo ""
echo "Son Güncelleme:"
snmpget -v2c -c public localhost 1.3.6.1.4.1.99999.1.1.4.0

echo ""
echo "Veri Sayısı:"
snmpget -v2c -c public localhost 1.3.6.1.4.1.99999.2.2.0

echo ""
echo "2️⃣ Tüm Sistem Bilgileri (snmpwalk):"
echo "-----------------------------------"
snmpwalk -v2c -c public localhost 1.3.6.1.4.1.99999.1.1

echo ""
echo "3️⃣ Batarya Verileri (snmpwalk):"
echo "-------------------------------"
snmpwalk -v2c -c public localhost 1.3.6.1.4.1.99999.4

echo ""
echo "4️⃣ Tekil Batarya Verisi Test:"
echo "-----------------------------"
echo "Arm 1, k=3, dtype=10 (Gerilim):"
snmpget -v2c -c public localhost 1.3.6.1.4.1.99999.4.1.3.10.0

echo ""
echo "Arm 2, k=4, dtype=11 (SOH):"
snmpget -v2c -c public localhost 1.3.6.1.4.1.99999.4.2.4.11.0

echo ""
echo "Arm 3, k=2, dtype=12 (NTC1):"
snmpget -v2c -c public localhost 1.3.6.1.4.1.99999.4.3.2.12.0

echo ""
echo "✅ Test tamamlandı!"

