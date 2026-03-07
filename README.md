# Sistema para Controle de Fluxo na Usina do Conhecimento

Este projeto implementa um sistema de contagem de pessoas utilizando Visão Computacional com o Raspberry Pi 4 Model B. Os dados de entrada e saída são armazenados em um banco de dados local e visualizados em tempo real através de um dashboard.

## Passo a passo para execução

### 1. Manutenção do sistema

Mantenha o sistema operacional atualizado:

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Instalação das dependências do sistema
Instale as bibliotecas do Picamera2 e OpenCV que possuem dependências nativas usando o gerenciador de pacotes do sistema:

```bash
sudo apt install -y python3-picamera2
sudo apt install -y python3-opencv
```

### 3. Configuração da câmera
A câmera geralmente é habilitada automaticamente em versões mais recentes do Raspberry OS. No entanto, verifique se a câmera está habilitada:

```bash
sudo raspi-config
```

Navegue até "Interface Options" e verifique a câmera, caso não tenha essa opção ela já está ativada. Teste a câmera executando o aplicativo de linha de comando:

```bash
rpicam-hello
```

### 4. Configuração do ambiente virtual
Crie o ambiente virtual com herança de pacotes para que as bibliotecas instaladas anteriormente sejam acessíveis:

```bash
python -m venv venv --system-site-packages
```

Ative o ambiente virtual:

```bash
source venv/bin/activate
```

Se o ambiente estiver ativo, a linha de comando mostrará (venv) ao lado da linha do nome de usuário.

### 5. Instalação das bibliotecas
Instale as bibliotecas restantes dentro do ambiente virtual ativo:

```bash
pip install dash pandas plotly
```
