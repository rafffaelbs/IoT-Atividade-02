"""
Simulacao de Subscriber MQTT - Backend / Motor de Regras
Versao com saida visual aprimorada (biblioteca rich) para apresentacao/video.

A logica de conexao, assinatura e regras e IDENTICA ao subscriber.py original.
Only a formatacao da saida no terminal foi alterada.

"""

import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
USINA_ID = "us01"

TOPICO_WILDCARD = f"usina/{USINA_ID}/#"


def agora_iso():
    return datetime.now(timezone.utc).isoformat()


def topico(*partes):
    return "/".join(["usina", USINA_ID, *partes])


# ---------------------------------------------------------------------------
def log_heartbeat(topic, payload):
    node = topic.split("/")[-2]
    console.print(
        f"  [dim]♥ heartbeat[/dim]  [dim]{node:<18}[/dim] "
        f"[dim]bateria {payload.get('bateria_pct')}%  rssi {payload.get('rssi_dbm')}dBm[/dim]"
    )


def log_status(topic, payload, alarmante=False):
    if alarmante:
        console.print(f"  [bold yellow]⚠ status[/bold yellow]      [white]{topic}[/white]  {payload}")
    else:
        console.print(f"  [cyan]◦ status[/cyan]      [white]{topic}[/white]  {payload}")


def log_evento(topic, payload, alarmante=False):
    cor = "yellow" if alarmante else "green"
    icone = "⚠" if alarmante else "●"
    console.print(f"  [{cor}]{icone} evento[/{cor}]      [white]{topic}[/white]")
    for k, v in payload.items():
        if k != "ts":
            console.print(f"      [white]{k}[/white]: [bold]{v}[/bold]", end="  ")
    console.print()


def log_incidente(trecho, origem):
    texto = Text(f"INCIDENTE DETECTADO — trecho: {trecho}  (origem: {origem})", style="bold white on red")
    console.print(Panel(texto, expand=False, border_style="red"))


def log_comando(topic, payload):
    console.print(f"    [orange3]→ comando[/orange3]  [white]{topic}[/white]  {payload}")


def log_alerta(topic, payload):
    console.print(
        Panel(
            f"[bold]{payload.get('descricao')}[/bold]\ntópico: {topic}",
            title="🔔 ALERTA PUBLICADO",
            border_style="magenta",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# Callbacks MQTT 
# ---------------------------------------------------------------------------
def on_connect(client, userdata, flags, reason_code, properties=None):
    console.rule("[bold green]Conectado ao broker MQTT")
    console.print(f"Broker: [bold]{BROKER_HOST}:{BROKER_PORT}[/bold]   código: {reason_code}")
    client.subscribe(TOPICO_WILDCARD, qos=1)
    console.print(f"Inscrito em: [bold cyan]{TOPICO_WILDCARD}[/bold cyan]\n")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except (ValueError, UnicodeDecodeError):
        payload = msg.payload.decode(errors="replace")

    if msg.topic.endswith("/heartbeat"):
        log_heartbeat(msg.topic, payload)
        return

    if "/portao/" in msg.topic and msg.topic.endswith("/status"):
        aberto = isinstance(payload, dict) and payload.get("estado") == "aberto"
        log_status(msg.topic, payload, alarmante=aberto)
        if aberto:
            log_incidente(trecho=msg.topic.split("/")[-2], origem="portao")
            _responder_incidente(client, origem="portao", trecho=msg.topic.split("/")[-2])
        return

    if "/atuador/" in msg.topic:
        log_comando(msg.topic, payload)
        return

    if msg.topic.endswith("/alerta"):
        log_alerta(msg.topic, payload)
        return

    if "/perimetro/" in msg.topic and msg.topic.endswith("/evento"):
        log_evento(msg.topic, payload, alarmante=True)
        log_incidente(trecho=msg.topic.split("/")[-2], origem="perimetro")
        _responder_incidente(client, origem="perimetro", trecho=msg.topic.split("/")[-2])
        return

    if "/paineis/" in msg.topic and msg.topic.endswith("/vibracao"):
        alarmante = isinstance(payload, dict) and payload.get("inclinacao_graus", 0) > 20
        log_evento(msg.topic, payload, alarmante=alarmante)
        if alarmante:
            log_incidente(trecho=msg.topic.split("/")[-2], origem="paineis")
            _responder_incidente(client, origem="paineis", trecho=msg.topic.split("/")[-2])
        return


def _responder_incidente(client, origem, trecho):
    topico_sirene = topico("atuador", trecho, "sirene", "cmd")
    cmd_sirene = {"ts": agora_iso(), "acao": "ligar", "duracao_seg": 30}
    client.publish(topico_sirene, json.dumps(cmd_sirene), qos=2)

    topico_luz = topico("atuador", trecho, "luz", "cmd")
    cmd_luz = {"ts": agora_iso(), "acao": "ligar", "duracao_seg": 120}
    client.publish(topico_luz, json.dumps(cmd_luz), qos=1)

    topico_alerta = topico("alerta")
    alerta = {
        "ts": agora_iso(),
        "nivel": "alto",
        "origem": origem,
        "trecho": trecho,
        "descricao": f"Possivel incidente detectado em {trecho} (origem: {origem})",
    }
    client.publish(topico_alerta, json.dumps(alerta), qos=1)


def main():
    client = mqtt.Client(client_id=f"backend-sub-{int(time.time())}")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        console.rule("[bold red]Encerrando subscriber")
        client.disconnect()


if __name__ == "__main__":
    main()