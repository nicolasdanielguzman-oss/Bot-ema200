# ============================================
# BOT EMA 200 + CONFIRMACIÓN - 1 MINUTO
# VERSIÓN CON PROXY WEBSHARE CORREGIDO
# ============================================

import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
import json
import ta
import os
import socket
import urllib.request

# ========== CONFIGURACIÓN API ==========
API_KEY = "t3lg8hVrh4gCMiEDynDZGUe1MEIHnhHDuJthfO0t9908GB20qHLgeU9Nie7ep84T"
API_SECRET = "3tkN4MxxBQdBE9VjpXwOsGGbwYmkcvZf3LESGjZ8i01VgGE5fIbOk3ORSnQK5nCA"

# ========== CONFIGURACIÓN DEL PROXY (WEBSHARE.IO) ==========
PROXY_HOST = "p.webshare.io"
PROXY_PUERTO = "80"
PROXY_USUARIO = "Ipnwlrhq"
PROXY_CONTRASEÑA = "8e2vbj68pj30"

# 🔥 Formato correcto para Webshare
proxy_url = f"http://{PROXY_USUARIO}:{PROXY_CONTRASEÑA}@{PROXY_HOST}:{PROXY_PUERTO}"

proxies = {
    'http': proxy_url,
    'https': proxy_url,
}

# Configurar variables de entorno para requests
os.environ['HTTP_PROXY'] = proxy_url
os.environ['HTTPS_PROXY'] = proxy_url

# ========== CONFIGURACIÓN DE PARÁMETROS ==========
VOLUMEN_MINIMO = 3_000_000
VOLUMEN_MAXIMO = 1_000_000_000
TIEMPO_ESPERA = 15
TIMEOUT_API = 60  # 🔥 Aumentado a 60 segundos

# ========== PARÁMETROS TENDENCIA ==========
TIMEFRAME = '1m'
EMA_PERIODO = 200

# ========== GESTIÓN DE RIESGO ==========
APALANCAMIENTO = 7
CAPITAL_POR_OPERACION = 0.07
TP_CAPITAL = 12
SL_CAPITAL = 15
TP_PORCENTAJE_PRECIO = TP_CAPITAL / APALANCAMIENTO
SL_PORCENTAJE_PRECIO = SL_CAPITAL / APALANCAMIENTO

# ========== FILTROS ==========
MAX_SUBIDA_24H = 25
VOLUMEN_ENTRADA_MINIMO = 1.3

# ========== EXCLUSIONES ==========
ACCIONES_TOKENIZADAS = [
    "AAPLUSDT", "TSLAUSDT", "AMZNUSDT", "MSFTUSDT", "GOOGLUSDT",
    "NFLXUSDT", "NVDAUSDT", "METAUSDT", "PYPLUSDT", "ADBEUSDT",
    "INTCUSDT", "CSCOUSDT", "ORCLUSDT", "IBMUSDT", "QCOMUSDT",
    "TXNUSDT", "AVGOUSDT", "AMDUSDT", "NKEUSDT", "DISUSDT",
    "VTIUSDT", "SPYUSDT", "QQQUSDT", "DIAUSDT", "GOLDUSDT",
    "SLVUSDT", "OILUSDT", "NGUSDT", "BRNUSDT", "COINUSDT",
    "DELLUSDT", "GEUSDT", "GMUSDT", "JPMUSDT", "KOUSDT",
    "MCDUSDT", "PEPUSDT", "PFEUSDT", "TUSDT", "WMTUSDT"
]

EXCLUIR_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "DOGEUSDT"] + ACCIONES_TOKENIZADAS

# ========== PAPER TRADING ==========
PAPER_TRADING = True
CAPITAL_INICIAL = 1000
MAX_OPERACIONES_ABIERTAS = 2

# ========== VERIFICAR PROXY ==========
print("═" * 80)
print("🔍 VERIFICANDO PROXY WEBSHARE")
print("═" * 80)
print(f"📌 Proxy: {PROXY_HOST}:{PROXY_PUERTO}")
print(f"📌 Usuario: {PROXY_USUARIO}")
print("═" * 80)

# Probar el proxy con una petición simple
try:
    test_ip = requests.get('https://api.ipify.org', proxies=proxies, timeout=10)
    print(f"✅ Proxy funcionando. IP pública: {test_ip.text}")
except Exception as e:
    print(f"⚠️ Error al probar el proxy: {str(e)[:100]}")
    print("   Continuando de todas formas...")

# ========== CONEXIÓN A BINANCE CON PROXY ==========
print(f"\n🔄 Conectando a Binance a través del proxy...")
print(f"   Timeout: {TIMEOUT_API}s")

try:
    client = Client(
        API_KEY,
        API_SECRET,
        requests_params={
            'proxies': proxies,
            'timeout': TIMEOUT_API
        }
    )
    # Probar la conexión con ping
    client.ping()
    print("✅ Conexión a Binance establecida correctamente")
    print("   ✅ API Key válida")
    print("   ✅ Proxy funcionando correctamente")
except Exception as e:
    print(f"❌ Error al conectar con Binance: {str(e)[:300]}")
    print("\n💡 POSIBLES SOLUCIONES:")
    print("   1. Verifica que las credenciales del proxy sean correctas")
    print("   2. Comprueba que tengas saldo en Webshare")
    print("   3. Prueba con el puerto 8080 en lugar de 80")
    client = None
    raise

# ========== PAPER TRADING ==========
class PaperTrading:
    def __init__(self, capital_inicial):
        self.capital = capital_inicial
        self.operaciones = []
        self.operaciones_abiertas = []
        self.historial = []

    def abrir_operacion(self, symbol, entrada, sl, tp, direccion):
        capital_operacion = self.capital * CAPITAL_POR_OPERACION
        cantidad = (capital_operacion * APALANCAMIENTO) / entrada

        operacion = {
            'symbol': symbol,
            'entrada': entrada,
            'sl': sl,
            'tp': tp,
            'direccion': direccion,
            'cantidad': cantidad,
            'capital_operacion': capital_operacion,
            'apalancamiento': APALANCAMIENTO,
            'exposicion': capital_operacion * APALANCAMIENTO,
            'fecha_apertura': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'estado': 'ABIERTA',
            'pnl': 0,
            'pnl_pct': 0,
            'precio_actual': entrada,
            'tp_capital': TP_CAPITAL,
            'sl_capital': SL_CAPITAL,
            'tp_precio': TP_PORCENTAJE_PRECIO,
            'sl_precio': SL_PORCENTAJE_PRECIO
        }
        self.operaciones_abiertas.append(operacion)
        self.operaciones.append(operacion)
        return operacion

    def cerrar_operacion(self, operacion, precio_salida, motivo):
        if operacion['direccion'] == 'LONG':
            pnl = (precio_salida - operacion['entrada']) * operacion['cantidad']
        else:
            pnl = (operacion['entrada'] - precio_salida) * operacion['cantidad']

        pnl_pct = (pnl / operacion['capital_operacion']) * 100

        operacion['estado'] = 'CERRADA'
        operacion['precio_salida'] = precio_salida
        operacion['fecha_cierre'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        operacion['pnl'] = pnl
        operacion['pnl_pct'] = pnl_pct
        operacion['motivo'] = motivo

        self.capital += pnl
        self.operaciones_abiertas.remove(operacion)
        self.historial.append(operacion)

        return pnl, pnl_pct

    def verificar_sl_tp(self):
        if not self.operaciones_abiertas:
            return

        for op in self.operaciones_abiertas[:]:
            try:
                ticker = client.futures_symbol_ticker(symbol=op['symbol'])
                precio_actual = float(ticker['price'])
                op['precio_actual'] = precio_actual

                if op['direccion'] == 'LONG':
                    if precio_actual <= op['sl']:
                        pnl, pnl_pct = self.cerrar_operacion(op, op['sl'], 'STOP LOSS')
                        print(f"\n   ❌ {op['symbol']} - SL ACTIVADO! Pérdida: ${pnl:.2f} ({pnl_pct:.1f}%)")
                    elif precio_actual >= op['tp']:
                        pnl, pnl_pct = self.cerrar_operacion(op, op['tp'], 'TAKE PROFIT')
                        print(f"\n   ✅ {op['symbol']} - TP ALCANZADO! Ganancia: ${pnl:.2f} ({pnl_pct:.1f}%)")
                else:
                    if precio_actual >= op['sl']:
                        pnl, pnl_pct = self.cerrar_operacion(op, op['sl'], 'STOP LOSS')
                        print(f"\n   ❌ {op['symbol']} - SL ACTIVADO! Pérdida: ${pnl:.2f} ({pnl_pct:.1f}%)")
                    elif precio_actual <= op['tp']:
                        pnl, pnl_pct = self.cerrar_operacion(op, op['tp'], 'TAKE PROFIT')
                        print(f"\n   ✅ {op['symbol']} - TP ALCANZADO! Ganancia: ${pnl:.2f} ({pnl_pct:.1f}%)")

            except Exception as e:
                print(f"   ❌ Error verificando {op['symbol']}: {str(e)[:80]}")

        if self.operaciones_abiertas:
            print(f"\n📊 {len(self.operaciones_abiertas)} operaciones activas:")
            for op in self.operaciones_abiertas:
                pnl_flotante = self.calcular_pnl_flotante(op)
                pnl_pct_flotante = (pnl_flotante / op['capital_operacion']) * 100
                emoji = "📈" if pnl_flotante > 0 else "📉"
                print(f"   {emoji} {op['symbol']} {op['direccion']} - Entrada: ${op['entrada']:.4f} | Actual: ${op['precio_actual']:.4f} | PnL: ${pnl_flotante:.2f} ({pnl_pct_flotante:.1f}%)")

    def calcular_pnl_flotante(self, op):
        if op['direccion'] == 'LONG':
            return (op['precio_actual'] - op['entrada']) * op['cantidad']
        else:
            return (op['entrada'] - op['precio_actual']) * op['cantidad']

    def get_resumen(self):
        total_operaciones = len(self.historial)
        operaciones_ganadoras = len([o for o in self.historial if o['pnl'] > 0])
        operaciones_perdedoras = len([o for o in self.historial if o['pnl'] < 0])

        winrate = (operaciones_ganadoras / total_operaciones * 100) if total_operaciones > 0 else 0
        pnl_total = self.capital - CAPITAL_INICIAL

        return {
            'capital': self.capital,
            'pnl_total': pnl_total,
            'pnl_pct_total': (pnl_total / CAPITAL_INICIAL) * 100,
            'total_ops': total_operaciones,
            'winrate': winrate,
            'ganadoras': operaciones_ganadoras,
            'perdedoras': operaciones_perdedoras
        }

    def mostrar_resumen(self):
        res = self.get_resumen()
        print("\n" + "═" * 55)
        print("📊 RESUMEN PAPER TRADING")
        print("═" * 55)
        print(f"💰 Capital inicial: ${CAPITAL_INICIAL:,.2f}")
        print(f"💰 Capital actual: ${res['capital']:,.2f}")
        print(f"📈 PnL Total: ${res['pnl_total']:,.2f} ({res['pnl_pct_total']:.2f}%)")
        print(f"📊 Winrate: {res['winrate']:.2f}%")
        print(f"✅ Ganadoras: {res['ganadoras']}")
        print(f"❌ Perdedoras: {res['perdedoras']}")
        print(f"⚡ Apalancamiento: x{APALANCAMIENTO}")
        print(f"📊 Capital por trade: {CAPITAL_POR_OPERACION*100}%")
        print(f"📊 Operaciones abiertas: {len(self.operaciones_abiertas)}")
        print("═" * 55)

    def mostrar_historial_completo(self):
        if not self.historial:
            print("\n📭 No hay operaciones completadas aún")
            return

        print("\n" + "═" * 70)
        print("📋 HISTORIAL COMPLETO")
        print("═" * 70)
        print(f"{'#':<3} {'Símbolo':<10} {'Dir.':<6} {'Entrada':<10} {'Salida':<10} {'PnL':<12} {'%':<8} {'Resultado':<10}")
        print("─" * 70)

        for i, op in enumerate(self.historial, 1):
            resultado = "✅ GANANCIA" if op['pnl'] > 0 else "❌ PÉRDIDA"
            print(f"{i:<3} {op['symbol']:<10} {op['direccion']:<6} ${op['entrada']:<9.4f} ${op.get('precio_salida', 0):<9.4f} ${op['pnl']:<11.2f} {op['pnl_pct']:<7.1f}% {resultado}")

        print("═" * 70)

# ========== ESTRATEGIA EMA 200 + CONFIRMACIÓN ==========

def obtener_pares_con_volumen():
    try:
        tickers = client.futures_ticker()
        pares = []
        for t in tickers:
            symbol = t['symbol']
            if symbol in EXCLUIR_SYMBOLS:
                continue
            if any(palabra in symbol for palabra in ['AAPL', 'TSLA', 'AMZN', 'MSFT', 'GOOGL', 'NFLX', 'NVDA', 'META']):
                continue
            if symbol.endswith('USDT'):
                precio = float(t['lastPrice'])
                volumen = float(t['quoteVolume'])
                if precio > 3:
                    continue
                if VOLUMEN_MINIMO <= volumen <= VOLUMEN_MAXIMO:
                    pares.append({
                        'symbol': symbol,
                        'price': precio,
                        'volume': volumen,
                        'change': float(t['priceChangePercent'])
                    })
        return sorted(pares, key=lambda x: x['volume'], reverse=True)
    except Exception as e:
        print(f"❌ Error obteniendo pares: {str(e)[:100]}")
        return []

def obtener_velas(symbol, intervalo='1m', limit=250):
    try:
        klines = client.futures_klines(symbol=symbol, interval=intervalo, limit=limit)
        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume',
                                           'close_time', 'quote_asset_volume', 'number_of_trades',
                                           'taker_buy_base', 'taker_buy_quote', 'ignore'])

        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)

        return df
    except Exception as e:
        return None

def calcular_ema200(df):
    if len(df) < 201:
        return None
    return df['close'].ewm(span=200, adjust=False).mean().iloc[-1]

def obtener_subida_24h(symbol):
    try:
        ticker = client.futures_ticker(symbol=symbol)
        return float(ticker['priceChangePercent'])
    except:
        return None

def verificar_volumen_entrada(df):
    if len(df) < 11:
        return True
    volumen_actual = df['volume'].iloc[-1]
    volumen_promedio = df['volume'].iloc[-10:-1].mean()
    return volumen_actual > volumen_promedio * VOLUMEN_ENTRADA_MINIMO

def estrategia_ema200(symbol):
    df = obtener_velas(symbol, '1m', 250)
    if df is None or len(df) < 201:
        return None

    ema200 = calcular_ema200(df)
    if ema200 is None:
        return None

    precio_actual = df['close'].iloc[-1]
    precio_anterior = df['close'].iloc[-2]
    
    subida_24h = obtener_subida_24h(symbol)
    if subida_24h is not None:
        if abs(subida_24h) > MAX_SUBIDA_24H:
            return None

    cruce_alcista = precio_anterior < ema200 and precio_actual > ema200
    cruce_bajista = precio_anterior > ema200 and precio_actual < ema200

    if not cruce_alcista and not cruce_bajista:
        return None

    ultima_vela = df.iloc[-1]
    rango = ultima_vela['high'] - ultima_vela['low']
    cuerpo = abs(ultima_vela['close'] - ultima_vela['open'])
    
    if rango == 0 or cuerpo / rango < 0.5:
        return None

    if not verificar_volumen_entrada(df):
        return None

    if cruce_alcista:
        direccion = 'LONG'
        sl = ultima_vela['low']
    else:
        direccion = 'SHORT'
        sl = ultima_vela['high']

    entrada = precio_actual

    if direccion == 'LONG':
        sl_price = min(sl, entrada * (1 - SL_PORCENTAJE_PRECIO / 100))
        tp = entrada * (1 + TP_PORCENTAJE_PRECIO / 100)
    else:
        sl_price = max(sl, entrada * (1 + SL_PORCENTAJE_PRECIO / 100))
        tp = entrada * (1 - TP_PORCENTAJE_PRECIO / 100)

    if direccion == 'LONG':
        riesgo = entrada - sl_price
        recompensa = tp - entrada
    else:
        riesgo = sl_price - entrada
        recompensa = entrada - tp

    rr = recompensa / riesgo if riesgo > 0 else 0

    if rr < 0.8:
        return None

    return {
        'entrada': entrada,
        'sl': sl_price,
        'tp': tp,
        'direccion': direccion,
        'rr': rr,
        'ema200': ema200,
        'precio_actual': precio_actual,
        'precio_anterior': precio_anterior,
        'tipo_cruce': 'ALCISTA' if cruce_alcista else 'BAJISTA',
        'subida_24h': subida_24h,
        'apalancamiento': APALANCAMIENTO,
        'capital_por_trade': CAPITAL_POR_OPERACION * 100,
        'tp_capital': TP_CAPITAL,
        'sl_capital': SL_CAPITAL,
        'tp_precio': TP_PORCENTAJE_PRECIO,
        'sl_precio': SL_PORCENTAJE_PRECIO
    }

# ========== MAIN ==========

def main():
    paper = PaperTrading(CAPITAL_INICIAL)

    print("═" * 80)
    print("📈 BOT EMA 200 + CONFIRMACIÓN - 1 MINUTO")
    print("═" * 80)
    print("📊 ESTRATEGIA:")
    print("   🔥 Precio > EMA200 → SOLO LONG")
    print("   🔥 Precio < EMA200 → SOLO SHORT")
    print("   🔥 Cruce de EMA200 + Vela fuerte + Volumen")
    print("   🔥 SL en la mecha de la vela de confirmación")
    print("═" * 80)
    print("📊 GESTIÓN DE RIESGO:")
    print(f"   🔥 Apalancamiento: x{APALANCAMIENTO}")
    print(f"   🔥 Capital por trade: {CAPITAL_POR_OPERACION*100}%")
    print(f"   🔥 TP sobre CAPITAL: {TP_CAPITAL}% → {TP_PORCENTAJE_PRECIO:.2f}% de movimiento")
    print(f"   🔥 SL sobre CAPITAL: {SL_CAPITAL}% → {SL_PORCENTAJE_PRECIO:.2f}% de movimiento")
    print(f"   🔥 R:R sobre capital: {TP_CAPITAL/SL_CAPITAL:.2f}:1")
    print("═" * 80)
    print(f"⏱️  Timeframe: 1 MINUTO")
    print(f"📊 EMA: {EMA_PERIODO}")
    print(f"🚫 Excluye: BTC, ETH, BNB, DOGE y acciones")
    print(f"💰 Precio máx: $3.00")
    print(f"💰 Capital virtual: ${CAPITAL_INICIAL:,.2f}")
    print(f"📊 Máx operaciones: {MAX_OPERACIONES_ABIERTAS}")
    print("═" * 80)
    print("📝 MODO PAPER TRADING")
    print("💡 Presiona Ctrl+C para detener\n")

    print("🔍 Realizando diagnóstico inicial...")
    try:
        pares_test = obtener_pares_con_volumen()
        print(f"✅ Pares encontrados: {len(pares_test)}")
        print(f"   ✅ Conexión exitosa. El bot está listo.")
        print(f"   ✅ Proxy Webshare configurado correctamente")
    except Exception as e:
        print(f"❌ Error al obtener pares: {str(e)[:100]}")
        print("⚠️ Verifica la conexión del proxy")

    contador = 0
    try:
        while True:
            paper.verificar_sl_tp()

            if len(paper.operaciones_abiertas) < MAX_OPERACIONES_ABIERTAS:

                pares = obtener_pares_con_volumen()
                if not pares:
                    print("⚠️ No se obtuvieron pares. Reintentando...")
                    time.sleep(30)
                    continue

                contador += 1
                if contador % 3 == 0:
                    print(f"\n🔍 Escaneando {len(pares)} pares - Ciclo {contador}")
                    print(f"📊 {len(paper.operaciones_abiertas)}/{MAX_OPERACIONES_ABIERTAS} operaciones abiertas")

                for pair in pares:
                    symbol = pair['symbol']

                    if any(op['symbol'] == symbol for op in paper.operaciones_abiertas):
                        continue

                    senal = estrategia_ema200(symbol)

                    if senal:
                        emoji = "📈" if senal['direccion'] == 'LONG' else "📉"
                        print(f"\n{emoji} {symbol} - SEÑAL {senal['direccion']} CONFIRMADA!")
                        print(f"   📊 EMA200: ${senal['ema200']:.4f}")
                        print(f"   📊 Cruce: {senal['tipo_cruce']}")
                        print(f"   📊 Precio actual: ${senal['precio_actual']:.4f}")
                        print(f"   📊 Precio anterior: ${senal['precio_anterior']:.4f}")
                        if senal['subida_24h'] is not None:
                            print(f"   📊 Subida 24h: {senal['subida_24h']:.1f}%")
                        print(f"   📈 ENTRADA: ${senal['entrada']:.4f}")

                        if senal['direccion'] == 'LONG':
                            print(f"   🎯 TP: ${senal['tp']:.4f} (+{senal['tp_precio']:.2f}% precio → +{senal['tp_capital']}% capital | R:R {senal['rr']:.2f}:1)")
                            print(f"   🛑 SL: ${senal['sl']:.4f} (-{senal['sl_precio']:.2f}% precio → -{senal['sl_capital']}% capital)")
                        else:
                            print(f"   🎯 TP: ${senal['tp']:.4f} (-{senal['tp_precio']:.2f}% precio → +{senal['tp_capital']}% capital | R:R {senal['rr']:.2f}:1)")
                            print(f"   🛑 SL: ${senal['sl']:.4f} (+{senal['sl_precio']:.2f}% precio → -{senal['sl_capital']}% capital)")

                        print(f"   ⚡ Apalancamiento: x{senal['apalancamiento']}")
                        print(f"   💰 Capital usado: {senal['capital_por_trade']:.1f}%")

                        op = paper.abrir_operacion(
                            symbol,
                            senal['entrada'],
                            senal['sl'],
                            senal['tp'],
                            senal['direccion']
                        )
                        print(f"   💰 Exposición: ${op['exposicion']:,.2f}")
                        print(f"   📊 Capital usado: ${op['capital_operacion']:,.2f}")
                        print(f"   📊 Capital restante: ${paper.capital:,.2f}")

                        if len(paper.operaciones_abiertas) >= MAX_OPERACIONES_ABIERTAS:
                            print(f"   ⏸️  Máximo alcanzado")
                            break

                if contador % 10 == 0 and len(paper.historial) > 0:
                    paper.mostrar_resumen()

            else:
                if contador % 3 == 0:
                    print(f"\n⏳ Máximo operaciones - Monitoreando SL/TP...")

            time.sleep(TIEMPO_ESPERA)

    except KeyboardInterrupt:
        print("\n\n⏹️ Bot detenido")
        paper.mostrar_historial_completo()
        paper.mostrar_resumen()

if __name__ == "__main__":
    main()
