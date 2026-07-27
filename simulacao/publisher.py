"""
Simulação de Publishers MQTT - Nós de campo da usina solar
Atividade Pratica 02 - Comunicacao em IoT utilizando MQTT

Simula 3 nos de campo (ESP32) publicando eventos de seguranca:
  - No de perimetro (sensor PIR)
  - No de portao (sensor magnetico)
  - No de painel/rack (acelerometro MPU6050)

Cada no publica tambem um heartbeat periodico e configura um
Last Will and Testament (LWT), para que o broker avise os
assinantes caso o no perca a conexao de forma inesperada.

Broker publico utilizado nesta simulacao: broker.hivemq.com (porta 1883)
Pode ser trocado por test.mosquitto.org ou por um broker EMQX publico.
"""

import json
import random
import time
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Configuracao geral
# ---------------------------------------------------------------------------
BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
USINA_ID = "us01"


def topico(*partes):
    return "/".join(["usina", USINA_ID, *partes])


def agora_iso():
    return datetime.now(timezone.utc).isoformat()


class NoDeCampo:
    """Representa um no ESP32 publicando em um topico especifico."""

    def __init__(self, node_id, topico_evento, qos, gerador_payload, retido=False):
        self.node_id = node_id
        self.topico_evento = topico_evento
        self.topico_heartbeat = topico("status", node_id, "heartbeat")
        self.qos = qos
        self.gerador_payload = gerador_payload
        self.retido = retido

        self.client = mqtt.Client(client_id=f"pub-{node_id}-{random.randint(1000,9999)}")

        # Last Will: se o no cair sem se desconectar corretamente, o broker
        # publica automaticamente este payload no topico de heartbeat.
        self.client.will_set(
            self.topico_heartbeat,
            payload=json.dumps({"ts": agora_iso(), "estado": "offline"}),
            qos=1,
            retain=True,
        )

    def conectar(self):
        self.client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        self.client.loop_start()

    def publicar_heartbeat(self):
        payload = {
            "ts": agora_iso(),
            "estado": "online",
            "bateria_pct": round(random.uniform(60, 100), 1),
            "rssi_dbm": random.randint(-95, -60),
        }
        self.client.publish(self.topico_heartbeat, json.dumps(payload), qos=0, retain=True)
        print(f"[HEARTBEAT] {self.topico_heartbeat} -> {payload}")

    def publicar_evento(self, forcar=False):
        # Probabilidade baixa de gerar evento a cada ciclo, simulando
        # ocorrencias esporadicas de movimento/abertura/vibracao.
        if forcar or random.random() < 0.25:
            payload = self.gerador_payload()
            self.client.publish(self.topico_evento, json.dumps(payload), qos=self.qos, retain=self.retido)
            print(f"[EVENTO]     {self.topico_evento} -> {payload}")


# ---------------------------------------------------------------------------
# Geradores de payload de cada tipo de no (formato das mensagens)
# ---------------------------------------------------------------------------
def payload_perimetro():
    return {
        "ts": agora_iso(),
        "tipo": "movimento",
        "valor": 1,
        "bateria_pct": round(random.uniform(60, 100), 1),
    }


def payload_portao():
    return {
        "ts": agora_iso(),
        "estado": random.choice(["aberto", "fechado"]),
        "bateria_pct": round(random.uniform(60, 100), 1),
    }


def payload_paineis():
    return {
        "ts": agora_iso(),
        "eixo_x": round(random.uniform(-2, 2), 2),
        "eixo_y": round(random.uniform(-2, 2), 2),
        "eixo_z": round(random.uniform(8, 11), 2),
        "inclinacao_graus": round(random.uniform(0, 35), 1),
    }


def main():
    nos = [
        NoDeCampo(
            node_id="perimetro-01",
            topico_evento=topico("perimetro", "perimetro-01", "evento"),
            qos=1,
            gerador_payload=payload_perimetro,
        ),
        NoDeCampo(
            node_id="portao-01",
            topico_evento=topico("portao", "portao-01", "status"),
            qos=1,
            gerador_payload=payload_portao,
            retido=True,
        ),
        NoDeCampo(
            node_id="paineis-setorA",
            topico_evento=topico("paineis", "setorA", "vibracao"),
            qos=1,
            gerador_payload=payload_paineis,
        ),
    ]

    for no in nos:
        no.conectar()
    time.sleep(1)

    print(f"\nPublicando para o broker {BROKER_HOST}:{BROKER_PORT}")
    print(f"Prefixo de topicos: \n")

    ciclo = 0
    try:
        while True:
            ciclo += 1
            for no in nos:
                # Heartbeat a cada 6 ciclos (~60s se o ciclo for de 10s)
                if ciclo % 6 == 0:
                    no.publicar_heartbeat()
                no.publicar_evento()
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nEncerrando publishers...")
        for no in nos:
            no.client.loop_stop()
            no.client.disconnect()


if __name__ == "__main__":
    main()
