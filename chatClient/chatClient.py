from sre_parse import State
import tkinter as tk
from tkinter import scrolledtext
import socket
import threading
import json
import time

receiver_id = 0
conversation_id = 0
client_id = 0 

# Função para receber mensagens
def receive_messages(sock, client_id, text_area):
    while True:
        try:
            message = sock.recv(1024).decode('utf-8')
            if message:
                data = json.loads(message)
                if 'SenderId' in data and data['SenderId'] == 0:
                    text_area.insert(tk.END, f"Server: {data['Content']}\n")
                else:
                    text_area.insert(tk.END, f"{data['Content']}\n")
                text_area.see(tk.END)
                if 'SenderId' in data and data['SenderId'] != 0:
                    acknoledgment(sock, data, client_id)
        except Exception as e:
            text_area.insert(tk.END, f"Erro: {str(e)}\n")
            break

def send_message(sock, client_id, entry, text_area):
    global conversation_id
    global receiver_id
    
    message = entry.get()
    entry.delete(0, tk.END)
    
    if message.lower() == 'exit':
        sock.close()
        window.quit()
        return
    
    if message.lower() == '/exit':
        conversation_id = 0
        receiver_id = 0
        return
    
    if message:
        msg_dict = {
            "SenderId": client_id,
            "ReceiverId": receiver_id,
            "Content": message,
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "ConversationId": conversation_id
        }
        json_message = json.dumps(msg_dict)
        sock.send(json_message.encode('utf-8'))

def send_heartbeat(sock, client_id):
    while True:
        time.sleep(3)
        try:
            msg_dict = {
                "SenderId": client_id,
                "ReceiverId": receiver_id,
                "Content": "heartbeat",
                "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                "ConversationId": conversation_id
            }
            json_message = json.dumps(msg_dict)
            sock.send(json_message.encode('utf-8'))
        except:
            break

def acknoledgment(sock, data, client_id):
    global conversation_id
    global receiver_id
    
    if data['SenderId'] != conversation_id:
        conversation_id = data['SenderId']
        receiver_id = data["SenderId"]
        msg_dict = {
            "SenderId": client_id,
            "ReceiverId": receiver_id,
            "Content": "/acknoledgment",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "ConversationId": conversation_id
        }
        json_message = json.dumps(msg_dict)
        sock.send(json_message.encode('utf-8'))
    else:
        msg_dict = {
            "SenderId": client_id,
            "ReceiverId": receiver_id,
            "Content": "/acknoledgment",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "ConversationId": conversation_id
        }
        json_message = json.dumps(msg_dict)
        sock.send(json_message.encode('utf-8'))

def start_chat():
    global client_socket
    server_ip = "127.0.0.1"
    server_port = 8888 
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    
    # Receber o ID do cliente
    while True:
        message = client_socket.recv(1024).decode('utf-8')
        if message:
            data = json.loads(message)
            if 'Content' in data and 'Your assigned client ID is' in data['Content']:
                client_id = data['ReceiverId']
                client_id_label.config(text=f"Meu ID: {client_id}")
                break
    
    # Iniciar threads
    threading.Thread(target=receive_messages, args=(client_socket, client_id, text_area), daemon=True).start()
    # threading.Thread(target=send_heartbeat, args=(client_socket, client_id), daemon=True).start()

# Configurar a janela principal
window = tk.Tk()
window.title("Bat Papo")
window.geometry("1000x800")

# Área de texto para exibir mensagens
frame = tk.Frame(window)
frame.pack(fill=tk.BOTH, expand=True)

client_id_label = tk.Label(frame, font=('Arial', 12))
client_id_label.pack(pady=5)

text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state='disabled')
text_area.pack(fill=tk.BOTH, expand=True)

text_area.insert(tk.END, "Enter command ('/list' to see clients, '/connect <client_id>' to start conversation, '/exit' to leave conversation, 'exit' to quit): \n")

# Área de entrada de mensagem
entry_frame = tk.Frame(window)
entry_frame.pack(fill=tk.X, side=tk.BOTTOM)

entry = tk.Entry(entry_frame)
entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

send_button = tk.Button(entry_frame, text="Enviar", command=lambda: send_message(client_socket, client_id, entry, text_area))
send_button.pack(side=tk.RIGHT)

# Iniciar o chat quando a janela for aberta
window.after(100, start_chat)

# Bind para enviar mensagem com Enter
entry.bind('<Return>', lambda event: send_message(client_socket, client_id, entry, text_area))

window.mainloop()