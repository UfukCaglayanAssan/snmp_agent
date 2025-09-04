import time
import datetime
import threading
import queue
import math
import pigpio
from collections import defaultdict

from pysnmp.entity.engine import SnmpEngine
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.entity import config
from pysnmp.entity.rfc3413 import cmdrsp
from pysnmp.smi import rfc1902

# SNMP ayarları
SNMP_AGENT_PORT = 161
SNMP_COMMUNITY = 'public'
SNMP_ENTERPRISE_OID = '1.3.6.1.4.1.99999'

# UART ve RAM ayarları
RX_PIN = 16
TX_PIN = 26
BAUD_RATE = 9600

buffer = bytearray()
data_queue = queue.Queue()
battery_data_ram = defaultdict(dict)
data_lock = threading.Lock()

last_k_value = None
last_k_value_lock = threading.Lock()
period_active = False
current_period_timestamp = None
last_data_received = time.time()

# pigpio başlat
pi = pigpio.pi()
pi.set_mode(TX_PIN, pigpio.OUTPUT)

# -----------------------------
# Yardımcı Fonksiyonlar
# -----------------------------

def Calc_SOC(x):
    if x is None:
        return None
    try:
        a1, a2, a3, a4 = 112.1627, 14.3937, 0, 10.5555
        b1, b2, b3, b4 = 14.2601, 11.6890, 12.7872, 10.9406
        c1, c2, c3, c4 = 1.8161, 0.8211, 0.0025, 0.3866
        soc = (a1 * math.exp(-((x-b1)/c1)**2) +
               a2 * math.exp(-((x-b2)/c2)**2) +
               a3 * math.exp(-((x-b3)/c3)**2) +
               a4 * math.exp(-((x-b4)/c4)**2))
        return min(max(round(soc,4),0),100)
    except:
        return None

def Calc_SOH(x):
    if x is None:
        return None
    try:
        a1, b1, c1 = 85.918, 0.0181, 0.0083
        a2, b2, c2 = 85.11, 0.0324, 0.0104
        a3, b3, c3 = 0.3085, 0.0342, 0.0021
        a4, b4, c4 = 16.521, 0.0382, 0.0013
        a5, b5, c5 = -13.874, 0.0381, 0.0011
        a6, b6, c6 = 40.077, 0.0474, 0.0079
        a7, b7, c7 = 18.207, 0.0556, 0.0048
        soh = (a1*math.exp(-((x-b1)/c1)**2)+
               a2*math.exp(-((x-b2)/c2)**2)+
               a3*math.exp(-((x-b3)/c3)**2)+
               a4*math.exp(-((x-b4)/c4)**2)+
               a5*math.exp(-((x-b5)/c5)**2)+
               a6*math.exp(-((x-b6)/c6)**2)+
               a7*math.exp(-((x-b7)/c7)**2))
        return min(round(soh,4),100)
    except:
        return None

def get_period_timestamp():
    global current_period_timestamp, period_active, last_data_received
    if not period_active:
        current_period_timestamp = int(time.time()*1000)
        period_active = True
        last_data_received = time.time()
    return current_period_timestamp

def reset_period():
    global current_period_timestamp, period_active
    current_period_timestamp = None
    period_active = False

def update_last_k_value(k):
    global last_k_value
    with last_k_value_lock:
        last_k_value = k

def get_last_k_value():
    with last_k_value_lock:
        return last_k_value

# -----------------------------
# RAM işlemleri
# -----------------------------

def update_battery_data_ram(arm,k,dtype,value):
    with data_lock:
        if arm not in battery_data_ram:
            battery_data_ram[arm] = {}
        if k not in battery_data_ram[arm]:
            battery_data_ram[arm][k] = {}
        battery_data_ram[arm][k][dtype] = {
            'value': value,
            'timestamp': int(time.time()*1000)
        }

def get_battery_data_ram(arm=None,k=None,dtype=None):
    with data_lock:
        if arm is None:
            return dict(battery_data_ram)
        if k is None:
            return dict(battery_data_ram.get(arm,{}))
        if dtype is None:
            return dict(battery_data_ram.get(arm,{}).get(k,{}))
        return battery_data_ram.get(arm,{}).get(k,{}).get(dtype,None)

def clear_battery_data_ram():
    with data_lock:
        battery_data_ram.clear()

# -----------------------------
# SNMP fonksiyonu
# -----------------------------

def get_snmp_value(oid_str):
    try:
        oid_parts = oid_str.split(".")
        if len(oid_parts) < 10:
            return rfc1902.NoSuchObject()
        if ".".join(oid_parts[:7]) != SNMP_ENTERPRISE_OID:
            return rfc1902.NoSuchObject()
        arm_num = int(oid_parts[7])
        k_value = int(oid_parts[8])
        dtype   = int(oid_parts[9])
        data = get_battery_data_ram(arm_num,k_value,dtype)
        if data is None:
            return rfc1902.NoSuchObject()
        value = data.get("value",0)
        if isinstance(value,int):
            return rfc1902.Integer(value)
        elif isinstance(value,float):
            return rfc1902.Gauge32(int(value*100))
        elif isinstance(value,str):
            return rfc1902.OctetString(value)
        else:
            return rfc1902.NoSuchObject()
    except:
        return rfc1902.NoSuchObject()

# -----------------------------
# UART veri okuma
# -----------------------------

def read_serial(pi):
    global buffer
    buffer.clear()
    while True:
        try:
            count,data = pi.bb_serial_read(RX_PIN)
            if count>0:
                buffer.extend(data)
                while len(buffer)>=3:
                    header_index = -1
                    for i,b in enumerate(buffer):
                        if b==0x80 or b==0x81:
                            header_index=i
                            break
                    if header_index==-1:
                        buffer.clear()
                        break
                    if header_index>0:
                        buffer = buffer[header_index:]
                    if len(buffer)>=3:
                        dtype = buffer[2]
                        packet_length = 11
                        if len(buffer)>=packet_length:
                            packet = buffer[:packet_length]
                            buffer = buffer[packet_length:]
                            hex_packet=[f"{b:02x}" for b in packet]
                            data_queue.put(hex_packet)
                        else:
                            break
                    else:
                        break
            time.sleep(0.01)
        except Exception as e:
            print(f"UART read error: {e}")
            time.sleep(1)

# -----------------------------
# Veri işleme thread
# -----------------------------

def data_processor():
    global last_data_received
    while True:
        try:
            data = data_queue.get(timeout=1)
            if data is None:
                break
            last_data_received=time.time()
            if len(data)==11:
                arm=int(data[3],16)
                k=int(data[1],16)
                dtype=int(data[2],16)
                update_last_k_value(k)
                value=int(data[4],16)
                update_battery_data_ram(arm,k,dtype,value)
            data_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Data processor error: {e}")
            continue

# -----------------------------
# SNMP Agent Başlatma
# -----------------------------

def snmp_agent():
    try:
        engine = SnmpEngine()
        config.add_transport(engine, udp.DOMAIN_NAME, udp.UdpTransport().open_server_mode(("0.0.0.0", SNMP_AGENT_PORT)))
        config.add_v1_system(engine, "my-area", SNMP_COMMUNITY)

        def request_handler(snmpEngine, stateReference, contextEngineId,
                            contextName, varBinds, cbCtx):
            rsp=[]
            for oid,val in varBinds:
                rsp.append((oid,get_snmp_value(".".join([str(x) for x in oid]))))
            return rsp

        cmdrsp.GetCommandResponder(engine, cbFun=request_handler)
        cmdrsp.NextCommandResponder(engine, cbFun=request_handler)
        cmdrsp.SetCommandResponder(engine, cbFun=request_handler)

        engine.transportDispatcher.jobStarted(1)
        engine.transportDispatcher.runDispatcher()
    except Exception as e:
        print(f"SNMP agent error: {e}")

# -----------------------------
# Main Fonksiyon
# -----------------------------

def main():
    clear_battery_data_ram()
    print("RAM temizlendi.")
    pi.write(TX_PIN,1)
    pi.bb_serial_read_open(RX_PIN, BAUD_RATE)
    threading.Thread(target=read_serial,args=(pi,),daemon=True).start()
    threading.Thread(target=data_processor,daemon=True).start()
    threading.Thread(target=snmp_agent,daemon=True).start()
    print("Sistem başlatıldı. Program çalışıyor... (Ctrl+C ile durdurun)")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Program sonlandırılıyor...")
    finally:
        pi.bb_serial_read_close(RX_PIN)
        pi.stop()

if __name__=='__main__':
    main()
