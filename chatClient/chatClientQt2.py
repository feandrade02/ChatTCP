import sys
import socket
import threading
import json
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QScrollArea, QFrame
)
from PyQt5.QtCore import pyqtSignal, QObject, QTimer

# Classe para sinais customizados (para thread-safe UI updates)
class Communicator(QObject):
    message_received = pyqtSignal(str)
    client_id_received = pyqtSignal(str)

class ChatClient(QWidget):
    def __init__(self):
        super().__init__()
        self.comm = Communicator()
        self.comm.message_received.connect(self.append_message)
        self.comm.client_id_received.connect(self.set_client_id)
        self.comm.clients_list_received = pyqtSignal(list) # atualizar lista de clientes

        self.client_socket = None
        self.client_id = None

        self.current_chat_id = None
        self.chat_areas = {}  # id_cliente: QTextEdit

        self.init_ui()

        # Timer para atualizar lista de clientes
        self.timer = QTimer()
        self.timer.timeout.connect(self.request_clients_list)
        self.timer.start(5000)  # 5 segundos
        
        threading.Thread(target=self.start_chat, daemon=True).start()

    def init_ui(self):
        self.setWindowTitle('Bat Papo')
        self.setGeometry(100, 100, 1000, 800)

        main_layout = QHBoxLayout(self)

        # Barra lateral esquerda
        self.sidebar = QVBoxLayout()
        self.sidebar_widget = QWidget()
        self.sidebar_widget.setLayout(self.sidebar)
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setWidget(self.sidebar_widget)
        main_layout.addWidget(self.sidebar_scroll, 1)

        # Área central (mensagens)
        center_layout = QVBoxLayout()
        self.client_id_label = QLabel("Meu ID: ")
        center_layout.addWidget(self.client_id_label)

        # Área de mensagens por conversa
        self.stacked_messages = QVBoxLayout()
        self.message_frame = QFrame()
        self.message_frame.setLayout(self.stacked_messages)
        center_layout.addWidget(self.message_frame, 10)

        # Área de entrada
        entry_layout = QHBoxLayout()
        self.entry = QLineEdit()
        entry_layout.addWidget(self.entry)
        self.send_button = QPushButton('Enviar')
        self.send_button.clicked.connect(self.send_message)
        entry_layout.addWidget(self.send_button)
        center_layout.addLayout(entry_layout)

        main_layout.addLayout(center_layout, 4)
        self.setLayout(main_layout)

        self.entry.returnPressed.connect(self.send_message)

    def request_clients_list(self):
        if self.client_socket:
            try:
                self.client_socket.send(json.dumps({"SenderId": self.client_id, "Content": "/list"}).encode())
            except Exception as e:
                pass
    
    def update_clients_list(self, clients):
        # Limpa sidebar
        for i in reversed(range(self.sidebar.count())):
            widget = self.sidebar.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Adiciona botões para cada cliente
        for client_id in clients:
            if str(client_id) == str(self.client_id):
                continue  # Não mostra a si mesmo
            btn = QPushButton(f"Cliente {client_id}")
            btn.clicked.connect(lambda _, cid=client_id: self.connect_to_client(cid))
            self.sidebar.addWidget(btn)
    
    def connect_to_client(self, client_id):
        # Envia comando de conexão
        if self.client_socket:
            self.client_socket.send(json.dumps({"SenderId": self.client_id, "Content": f"/connect {client_id}"}).encode())
        # Troca área de mensagens
        if client_id not in self.chat_areas:
            area = QTextEdit()
            area.setReadOnly(True)
            self.chat_areas[client_id] = area
            self.stacked_messages.addWidget(area)
        # Esconde todas as áreas e mostra só a do cliente selecionado
        for cid, area in self.chat_areas.items():
            area.setVisible(cid == client_id)
        self.current_chat_id = client_id

    def append_message(self, message):
        # Exibe mensagem na área da conversa atual
        if self.current_chat_id and self.current_chat_id in self.chat_areas:
            self.chat_areas[self.current_chat_id].append(message)
        else:
            # Mensagem geral (sem conversa ativa)
            if "geral" not in self.chat_areas:
                area = QTextEdit()
                area.setReadOnly(True)
                self.chat_areas["geral"] = area
                self.stacked_messages.addWidget(area)
            self.chat_areas["geral"].append(message)

    def set_client_id(self, client_id):
        self.client_id_label.setText(f"Meu ID: {client_id}")

    def send_message(self):
        message = self.entry.text()
        if message and self.client_socket:
            try:
                data = {
                    "SenderId": self.client_id,
                    "Content": message
                }
                self.client_socket.send(json.dumps(data).encode())
                self.comm.message_received.emit(f"Você: {message}")
                self.entry.clear()
            except Exception as e:
                self.comm.message_received.emit(f"[Erro ao enviar]: {e}")

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(4096).decode()
                if not message:
                    break

                # Detecta se é a lista de clientes ativos
                if message.startswith("Active clients:"):
                    # Extrai os IDs dos clientes usando regex
                    client_ids = []
                    for line in message.splitlines()[1:]:
                        match = re.match(r"ID:\s*(\d+)", line)
                        if match:
                            client_ids.append(match.group(1))
                    self.update_clients_list(client_ids)
                    continue

                # Detecta se é uma mensagem de sistema com o ID do cliente
                try:
                    data = json.loads(message)
                    if 'Content' in data and 'Your assigned client ID is' in data['Content']:
                        self.client_id = data['ReceiverId']
                        self.comm.client_id_received.emit(str(self.client_id))
                        continue
                    # Mensagem normal de chat
                    sender = data.get("SenderId", "Outro")
                    content = data.get("Content", "")
                    # Direciona para a área da conversa correta
                    if sender not in self.chat_areas:
                        area = QTextEdit()
                        area.setReadOnly(True)
                        self.chat_areas[sender] = area
                        self.stacked_messages.addWidget(area)
                    self.chat_areas[sender].append(f"{sender}: {content}")
                    # Se estiver conversando com esse cliente, mostra a área
                    if self.current_chat_id == sender:
                        for cid, area in self.chat_areas.items():
                            area.setVisible(cid == sender)
                except Exception:
                    # Caso a mensagem não seja JSON (mensagem de sistema/texto puro)
                    self.comm.message_received.emit(message)
            except Exception as e:
                self.comm.message_received.emit(f"[Erro ao receber]: {e}")
                break
    
    def start_chat(self):
        HOST = '127.0.0.1'
        PORT = 8888
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((HOST, PORT))

        # Recebe o ID do cliente
        while True:
            message = self.client_socket.recv(1024).decode()
            data = json.loads(message)
            if 'Content' in data and 'Your assigned client ID is' in data['Content']:
                self.client_id = data['ReceiverId']
                self.comm.client_id_received.emit(str(self.client_id))
                break

        # Inicia thread para receber mensagens
        threading.Thread(target=self.receive_messages, daemon=True).start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatClient()
    window.show()
    sys.exit(app.exec_())