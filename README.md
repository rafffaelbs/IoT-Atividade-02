# Sistema IoT para Segurança de Usinas Solares — Comunicação MQTT

Atividade Prática 02 — Disciplina de Internet das Coisas (IoT)
Evolução da Atividade Prática 01 (planejamento da solução de segurança e monitoramento de usinas fotovoltaicas), agora com foco em **comunicação entre dispositivos via MQTT**.

## 1. Sobre o projeto

Usinas solares ocupam grandes áreas rurais, com pouca vigilância humana, o que as torna alvo de furto de painéis, cabos e equipamentos. Este projeto planeja um sistema de segurança baseado em IoT que monitora o perímetro e os ativos críticos da usina (painéis, racks, portões), envia alertas em tempo real para as equipes de segurança e O&M, e aciona dispositivos de dissuasão (sirene, iluminação) automaticamente.

Esta etapa (Atividade 02) evolui a arquitetura da Atividade 01 detalhando **como os dispositivos se comunicam**, usando o protocolo **MQTT** — Publisher, Broker e Subscriber — e realiza uma prova de conceito com um broker público, como base para a futura integração com a **AWS IoT Core**.

## 2. Estrutura do repositório

```
.
├── README.md
├── docs/
│   └── Atividade02_Comunicacao_MQTT_Usinas_Solares.pdf   # documento completo da atividade
├── diagramas/
│   └── arquitetura_mqtt.png                               # diagrama Publisher/Broker/Subscriber
└── simulacao/
    ├── publisher.py         # simula os nós de campo (sensores) publicando no broker
    ├── subscriber.py        # simula o backend/motor de regras assinando e reagindo
    └── requirements.txt
```

## 3. Arquitetura MQTT (resumo)

- **Publishers**: nós de campo (ESP32) — sensor de perímetro, sensor de portão, sensor de vibração/inclinação em painéis, e o gateway de borda (câmera + heartbeat).
- **Broker MQTT**: broker público (HiveMQ ou Mosquitto) nesta fase de prova de conceito; substituído pela **AWS IoT Core** na implementação final.
- **Subscribers**: backend/motor de regras (protótipo em Node-RED, futuramente AWS Lambda), banco de dados, dashboard web/app mobile, e os próprios atuadores (sirene e iluminação), que também assinam tópicos de comando.

O diagrama completo está em `diagramas/arquitetura_mqtt.png` e a explicação detalhada no PDF em `docs/`.

## 4. Tópicos MQTT

Todos os tópicos seguem o padrão:

```
usina/<usina_id>/<categoria>/<identificador>/<subtopico>
```

| Tópico | Publisher | Subscriber | QoS | Retido |
|---|---|---|---|---|
| `usina/{id}/perimetro/{node}/evento` | Nó de perímetro | Backend | 1 | Não |
| `usina/{id}/portao/{node}/status` | Nó de portão | Backend | 1 | Sim |
| `usina/{id}/paineis/{setor}/vibracao` | Nó de painel/rack | Backend | 1 | Não |
| `usina/{id}/camera/{cam}/evento` | Gateway edge | Backend | 1 | Não |
| `usina/{id}/status/{node}/heartbeat` | Todos os nós | Backend | 0 | Sim |
| `usina/{id}/alerta` | Backend | Dashboard / App | 1 | Não |
| `usina/{id}/atuador/{node}/sirene/cmd` | Backend | Nó atuador sirene | 2 | Não |
| `usina/{id}/atuador/{node}/luz/cmd` | Backend | Nó atuador luz | 1 | Não |

Detalhamento completo (formato JSON de cada mensagem, frequência de envio e justificativa de QoS) está no PDF em `docs/`.

## 5. Executando a simulação

A simulação usa o broker público **broker.hivemq.com** (porta 1883, sem TLS — apenas para fins didáticos; nunca usar um broker público sem TLS/autenticação em produção).

```bash
# 1. Clonar o repositório
git clone https://github.com/<seu-usuario>/<seu-repo>.git
cd <seu-repo>/simulacao

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Em um terminal, iniciar o subscriber (representa o backend)
python3 subscriber.py

# 4. Em outro terminal, iniciar o publisher (representa os nós de campo)
python3 publisher.py
```

Você verá no terminal do `subscriber.py` as mensagens de telemetria chegando e, quando um evento de perímetro ou de vibração acima do limiar é recebido, o próprio subscriber publica de volta os comandos para os atuadores (`sirene/cmd`, `luz/cmd`) e um alerta consolidado (`alerta`) — fechando o ciclo publish → broker → subscribe → publish (comando).


## 6. Integração futura com AWS IoT Core

O broker público é usado apenas nesta fase de prova de conceito. O planejamento de migração para produção prevê:

- Cadastro de cada dispositivo no **AWS IoT Device Registry**, com certificado X.509 individual;
- **IoT Policies** restringindo cada dispositivo a publicar/assinar apenas nos tópicos que lhe cabem (princípio do menor privilégio);
- **Device Shadow** para manter o último estado conhecido de cada nó, mesmo offline;
- **IoT Rules Engine** roteando mensagens para AWS Lambda, Amazon Timestream (séries temporais), DynamoDB (estado atual) e S3 (mídia dos eventos);
- **Amazon SNS / Amazon Location Service** para notificações e visualização geográfica dos eventos.

Detalhes completos no PDF em `docs/`.

## 7. Vídeo de demonstração

Link do vídeo (2–5 min): _adicionar aqui após a gravação_

## 8. Autor

Rafael — Trabalho individual, disciplina de Internet das Coisas (IoT).
