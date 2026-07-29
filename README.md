🏗️ Projeto em desenvolvimento...

# Sistema de controle de fluxo da Usina do Conhecimento

Sistema de contagem de pessoas com visão computacional para a Usina do Conhecimento. O projeto registra entradas e saídas em banco SQLite e disponibiliza visualização dos dados em dashboard.

## Tecnologias utilizadas

- Python
- OpenCV
- YOLOv8 (Ultralytics)
- Picamera2
- SQLite
- Dash
- Pandas
- Plotly

## Estrutura do projeto

- `contagem.py`: captura pela câmera do Raspberry Pi, detecta movimento com OpenCV e registra eventos no banco.
- `contagem-teste.py`: versão de teste com OpenCV em vídeo, usando subtração de fundo, filtros morfológicos e rastreamento simples.
- `contagem-yolov8.py`: versão de teste com YOLOv8 para detecção e rastreamento de pessoas em vídeo.
- `dashboard.py`: dashboard web para acompanhar entradas e saídas registradas no banco.
- `dados-teste.py`: gera dados fictícios no banco para testar o dashboard.
- `usina_dados.db`: banco SQLite com a tabela `fluxo_pessoas`.

## Execução

### 1. Atualize o sistema

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Instale dependências do sistema

```bash
sudo apt install -y python3-picamera2
sudo apt install -y python3-opencv
```

### 3. Configure a câmera no Raspberry Pi

Verifique se a câmera está habilitada:

```bash
sudo raspi-config
```

Teste a câmera:

```bash
rpicam-hello
```

### 4. Crie e ative o ambiente virtual

```bash
python -m venv venv --system-site-packages
source venv/bin/activate
```

No Windows:

```cmd
venv\scripts\activate
```

### 5. Instale as dependências Python

```bash
pip install dash pandas plotly ultralytics
```

## Implementação com OpenCV

O arquivo `contagem.py` é a implementação pensada para execução no Raspberry Pi. O fluxo atual:

1. Captura frames com `Picamera2`.
2. Aplica subtração de fundo com OpenCV.
3. Detecta contornos de movimento.
4. Rastreia objetos pelo centro do bounding box.
5. Conta cruzamentos em uma linha horizontal.
6. Registra `Entrada` e `Saida` no banco `usina_dados.db`.

Para executar:

```bash
python contagem.py
```

## Implementação com YOLOv8

O arquivo `contagem-yolov8.py` usa o modelo `yolov8n.pt` para processar um vídeo e contar pessoas com rastreamento por ID.

Esse fluxo faz:

1. Carregamento do modelo YOLOv8.
2. Leitura do vídeo `teste_usina.mp4`.
3. Detecção apenas da classe pessoa.
4. Rastreamento com IDs persistentes.
5. Contagem de entrada e saída ao cruzar a linha configurada.
6. Geração de vídeo anotado com o resultado final.

Para executar:

```bash
python contagem-yolov8.py
```

Arquivos usados nessa etapa:

- `teste_usina.mp4`
- `yolov8n.pt`
- `resultado_yolov8_teste.mp4`

## Parte de teste

O projeto possui uma rotina separada para testes em vídeo, sem depender da câmera do Raspberry Pi.

### Teste com OpenCV

O arquivo `contagem-teste.py` processa `teste_usina.mp4` com:

- subtração de fundo `MOG2`
- região de interesse
- filtros de área, largura, altura e proporção
- união de detecções próximas
- rastreamento simples por posição

Para executar:

```bash
python contagem-teste.py
```

Saída gerada:

- `resultado_teste_video.mp4`

### Teste do dashboard

Para popular o banco com dados fictícios:

```bash
python dados-teste.py
```

Depois inicie o dashboard:

```bash
python dashboard.py
```

O painel ficará disponível em:

```text
http://localhost:8050
```

## Banco de dados

Os eventos são gravados na tabela `fluxo_pessoas` com os campos:

- `id`
- `data_hora`
- `evento`

Os valores de `evento` usados no projeto são:

- `Entrada`
- `Saida`

## Observações

- A implementação com `contagem.py` depende de Raspberry Pi com câmera configurada.
- As versões de teste usam vídeo local para calibração e validação da contagem.
- Os parâmetros de linha de contagem, resolução e filtros podem ser ajustados conforme o ambiente real.
