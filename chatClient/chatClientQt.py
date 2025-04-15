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
import time

# Classe para sinais customizados (para thread-safe UI updates)
class Communicator(QObject):
    message_received = pyqtSignal(str)
    client_id_received = pyqtSignal(str)
    clients_list_received = pyqtSignal(list)

class ChatClient(QWidget):
    def __init__(self):
        super().__init__()
        self.comm = Communicator()
        self.comm.message_received.connect(self.append_message)
        self.comm.client_id_received.connect(self.set_client_id)
        self.comm.clients_list_received.connect(self.update_clients_list)

        self.client_socket = None
        self.client_id = None

        self.current_chat_id = None
        self.chat_areas = {}  # id_cliente: QTextEdit

        self.init_ui()

        # Inicia a thread de conexão depois que a UI estiver pronta
        threading.Thread(target=self.start_chat, daemon=True).start()

    def init_ui(self):
        self.setWindowTitle('Bat Papo')
        self.setGeometry(100, 100, 1000, 800)

        main_layout = QHBoxLayout(self)

        # Barra lateral esquerda
        self.sidebar = QVBoxLayout()
        
        # Título da barra lateral
        self.sidebar_title = QLabel("Clientes Online")
        self.sidebar_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.sidebar.addWidget(self.sidebar_title)
        
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

        # Área de mensagens
        self.messages_area = QTextEdit()
        self.messages_area.setReadOnly(True)
        center_layout.addWidget(self.messages_area, 10)

        # Área de entrada
        entry_layout = QHBoxLayout()
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("Digite sua mensagem...")
        entry_layout.addWidget(self.entry)
        self.send_button = QPushButton('Enviar')
        self.send_button.clicked.connect(self.send_message)
        entry_layout.addWidget(self.send_button)
        center_layout.addLayout(entry_layout)

        main_layout.addLayout(center_layout, 4)
        self.setLayout(main_layout)

        self.entry.returnPressed.connect(self.send_message)

        # Adiciona a área geral ao dicionário
        self.chat_areas["geral"] = self.messages_area

    def request_clients_list(self):
        if self.client_socket and self.client_id:
            try:
                message = {
                    "SenderId": self.safe_int_conversion(self.client_id),
                    "ReceiverId": 0,  # Servidor
                    "Content": "/list",
                    "Timestamp": None,  # O servidor vai ignorar este campo
                    "ConversationId": 0
                }
                self.client_socket.send(json.dumps(message).encode())
            except Exception as e:
                self.messages_area.append(f"[Erro ao solicitar lista de clientes]: {e}")
    
    def update_clients_list(self, clients):
        # Remove todos os botões de cliente (mantendo o título)
        for i in reversed(range(self.sidebar.count())):
            widget = self.sidebar.itemAt(i).widget()
            if widget and widget != self.sidebar_title:
                widget.setParent(None)
        
        # Adiciona o título novamente se foi removido
        if self.sidebar.indexOf(self.sidebar_title) == -1:
            self.sidebar.addWidget(self.sidebar_title)
        
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
            message = {
                "SenderId": self.safe_int_conversion(self.client_id),
                "ReceiverId": 0,  # Servidor
                "Content": f"/connect {client_id}",
                "Timestamp": None,
                "ConversationId": 0
            }
            self.client_socket.send(json.dumps(message).encode())
            self.messages_area.append(f"[Sistema] Conectando com Cliente {client_id}...")
        
        self.current_chat_id = client_id

    def append_message(self, message):
        self.messages_area.append(message)

    def set_client_id(self, client_id):
        self.client_id = client_id
        self.client_id_label.setText(f"Meu ID: {client_id}")
        
        # Configura o timer para atualizar a lista de clientes periodicamente
        self.timer = QTimer()
        self.timer.timeout.connect(self.request_clients_list)
        self.timer.start(5000)  # 5 segundos
        
        # Configura o timer para enviar heartbeat periodicamente
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)
        self.heartbeat_timer.start(15000)  # 15 segundos
        
        # Solicita lista de clientes imediatamente
        self.request_clients_list()

    def send_heartbeat(self):
        if self.client_socket and self.client_id:
            try:
                message = {
                    "SenderId": self.safe_int_conversion(self.client_id),
                    "ReceiverId": 0,  # Servidor
                    "Content": "heartbeat",
                    "Timestamp": None,
                    "ConversationId": 0
                }
                self.client_socket.send(json.dumps(message).encode())
            except Exception as e:
                self.messages_area.append(f"[Erro ao enviar heartbeat]: {e}")

    def send_message(self):
        message_text = self.entry.text().strip()
        if not message_text:
            return
            
        if message_text == "/list":
            self.request_clients_list()
            self.entry.clear()
            return
        elif message_text.startswith("/connect"):
            parts = message_text.split()
            if len(parts) == 2 and parts[1].isdigit():
                self.connect_to_client(parts[1])
            else:
                self.messages_area.append("[Sistema] Uso: /connect <id_cliente>")
            self.entry.clear()
            return
        elif message_text == "/exit":
            if self.current_chat_id:
                message = {
                    "SenderId": self.safe_int_conversion(self.client_id),
                    "ReceiverId": 0,  # Servidor
                    "Content": "/exit",
                    "Timestamp": None,
                    "ConversationId": 0
                }
                self.client_socket.send(json.dumps(message).encode())
                old_chat = self.current_chat_id
                self.current_chat_id = None
                self.messages_area.append(f"[Sistema] Saiu da conversa com Cliente {old_chat}")
            self.entry.clear()
            return
        elif self.client_socket:
            try:
                data = {
                    "SenderId": self.safe_int_conversion(self.client_id),
                    "ReceiverId": self.safe_int_conversion(self.current_chat_id) if self.current_chat_id else 0,
                    "Content": message_text,
                    "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                    "ConversationId": self.safe_int_conversion(self.current_chat_id) if self.current_chat_id else 0
                }
                
                if self.current_chat_id:
                    self.client_socket.send(json.dumps(data).encode())
                    self.messages_area.append(f"Você para Cliente {self.current_chat_id}: {message_text}")
                else:
                    self.messages_area.append("[Sistema] Você precisa conectar com um cliente primeiro usando /connect <id_cliente>")
                
                self.entry.clear()
            except Exception as e:
                self.messages_area.append(f"[Erro ao enviar]: {e}")

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(4096).decode()
                if not message:
                    self.comm.message_received.emit("[Sistema] Desconectado do servidor.")
                    break

                # Tenta processar como JSON
                try:
                    data = json.loads(message)
                    
                    # Verifica se é a resposta do comando /list
                    if data.get("SenderId") == 0 and "Active clients:" in data.get("Content", ""):
                        client_ids = []
                        for line in data["Content"].splitlines()[1:]:  # Pular a primeira linha (título)
                            match = re.match(r"ID:\s*(\d+)", line)
                            if match:
                                client_ids.append(match.group(1))
                        
                        # Emitir sinal para atualizar lista de clientes
                        self.comm.clients_list_received.emit(client_ids)
                        continue
                    
                    # Verifica se é uma mensagem sobre ID do cliente
                    if "Your assigned client ID is" in data.get("Content", ""):
                        client_id = data.get("ReceiverId")
                        if client_id:
                            self.comm.client_id_received.emit(str(client_id))
                        continue
                    
                    # Envia mensagem periódica para manter conexão ativa (heartbeat)
                    if data.get("SenderId") == 0 and data.get("Content") == "Message delivered.":
                        # Não mostra os confirmations de entrega
                        continue
                    
                    # Mensagem normal de um cliente ou do servidor
                    sender_id = data.get("SenderId", "Desconhecido")
                    content = data.get("Content", "")
                    sender_name = "Servidor" if sender_id == 0 else f"Cliente {sender_id}"
                    
                    # Mostrar mensagem na área principal
                    self.comm.message_received.emit(f"{sender_name}: {content}")
                    
                except json.JSONDecodeError:
                    # Mensagem não é JSON (provavelmente texto puro do sistema)
                    self.comm.message_received.emit(message)
                    
            except Exception as e:
                self.comm.message_received.emit(f"[Erro ao receber]: {e}")
                break
    
    def start_chat(self):
        HOST = '127.0.0.1'
        PORT = 8888
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
            self.comm.message_received.emit(f"[Sistema] Conectado ao servidor {HOST}:{PORT}")
            
            # Inicia thread para receber mensagens
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except Exception as e:
            self.comm.message_received.emit(f"[Erro ao conectar]: {e}")

    def safe_int_conversion(self, value, default=0):
        try:
            if value is None:
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatClient()
    window.show()
    sys.exit(app.exec_())