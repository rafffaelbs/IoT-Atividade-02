"""
Simulacao de Subscriber MQTT - Backend / Motor de Regras
Atividade Pratica 02 - Comunicacao em IoT utilizando MQTT

Este script representa o papel que, na arquitetura final, sera
executado pelo Node-RED / AWS Lambda: ele assina TODOS os topicos
de telemetria da usina (wildcard '#'), aplica uma regra simples de
correlacao e, quando identifica um evento relevante, publica:
  - um comando para os atuadores (sirene/luz)
  - um alerta consolidado para o dashboard/app

Broker publico utilizado nesta simulacao: broker.hivemq.com (porta 1883)
"""

import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
USINA_ID = "us01"

TOPICO_WILDCARD = f"/usina/{USINA_ID}/#"


def agora_iso():
    return datetime.now(timezone.utc).isoformat()


def topico(*partes):
    return "/".join(["usina", USINA_ID, *partes])


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"Conectado ao broker com codigo: {reason_code}")
    client.subscribe(TOPICO_WILDCARD, qos=1)
    print(f"Inscrito em: {TOPICO_WILDCARD}\n")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except (ValueError, UnicodeDecodeError):
        payload = msg.payload.decode(errors="replace")

    print(f"[RECEBIDO] {msg.topic} -> {payload}")

    # ------------------------------------------------------------------
    # Regra simples de correlacao (equivalente a um flow do Node-RED):
    # qualquer evento de perimetro ou vibracao de painel dispara resposta
    # imediata (sirene + iluminacao) e gera um alerta para o dashboard.
    # ------------------------------------------------------------------
    if "/perimetro/" in msg.topic and msg.topic.endswith("/evento"):
        _responder_incidente(client, origem="perimetro", trecho=msg.topic.split("/")[-2])

    elif "/paineis/" in msg.topic and msg.topic.endswith("/vibracao"):
        if isinstance(payload, dict) and payload.get("inclinacao_graus", 0) > 20:
            _responder_incidente(client, origem="paineis", trecho=msg.topic.split("/")[-2])


def _responder_incidente(client, origem, trecho):
    # Publica comando para a sirene do trecho correspondente
    topico_sirene = topico("atuador", f"{trecho}", "sirene", "cmd")
    cmd_sirene = {"ts": agora_iso(), "acao": "ligar", "duracao_seg": 30}
    client.publish(topico_sirene, json.dumps(cmd_sirene), qos=2)
    print(f"[COMANDO]    {topico_sirene} -> {cmd_sirene}")

    # Publica comando para a iluminacao do trecho correspondente
    topico_luz = topico("atuador", f"{trecho}", "luz", "cmd")
    cmd_luz = {"ts": agora_iso(), "acao": "ligar", "duracao_seg": 120}
    client.publish(topico_luz, json.dumps(cmd_luz), qos=1)
    print(f"[COMANDO]    {topico_luz} -> {cmd_luz}")

    # Publica alerta consolidado para o dashboard/app (assinantes finais)
    topico_alerta = topico("alerta")
    alerta = {
        "ts": agora_iso(),
        "nivel": "alto",
        "origem": origem,
        "trecho": trecho,
        "descricao": f"Possivel incidente detectado em {trecho} (origem: {origem})",
    }
    client.publish(topico_alerta, json.dumps(alerta), qos=1)
    print(f"[ALERTA]     {topico_alerta} -> {alerta}\n")


def main():
    client = mqtt.Client(client_id=f"backend-sub-{int(time.time())}")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    print(f"Conectando ao broker {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nEncerrando subscriber...")
        client.disconnect()


if __name__ == "__main__":
    main()
