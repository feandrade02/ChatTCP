using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;
using ConsoleAppTeste.Models;
using ConsoleAppTeste.Enums;

namespace ConsoleAppTeste.Services
{
    public static class MessageService
    {
        public static void SendClientId(ClientHandler clientHandler)
        {
            var message = new Message
            {
                SenderId = (int)SystemIds.Server, // Server ID
                ReceiverId = clientHandler.ClientId,
                Content = $"Your assigned client ID is {clientHandler.ClientId}.",
                Timestamp = DateTime.UtcNow.ToString("o"),
                ConversationId = -1
            };
            string jsonResponse = JsonSerializer.Serialize(message);
            byte[] buffer = Encoding.UTF8.GetBytes(jsonResponse);
            clientHandler.Stream.Write(buffer, 0, buffer.Length);
        }

        public static void SendMessageToClient(ClientHandler clientHandler, string content)
        {
            Message message = new Message
            {
                SenderId = (int)SystemIds.Server, // Server ID
                ReceiverId = clientHandler.ClientId,
                Content = content,
                Timestamp = DateTime.UtcNow.ToString("o"),
                ConversationId = 0 // No specific conversation ID for server messages
            };
            string jsonResponse = JsonSerializer.Serialize(message);
            byte[] buffer = Encoding.UTF8.GetBytes(jsonResponse);
            clientHandler.Stream.Write(buffer, 0, buffer.Length);
        }

        public static void SendPrivateMessage(ClientHandler sender, Message message, List<ClientHandler> clients, object lockObj)
        {
            lock (lockObj)
            {
                var recipient = clients.Find(c => c.ClientId == sender.CurrentConversationWith);
                if (recipient != null)
                {
                    Message newMessage = new Message
                    {
                        SenderId = sender.ClientId,
                        ReceiverId = recipient.ClientId,
                        Content = message.Content,
                        Timestamp = DateTime.UtcNow.ToString("o"),
                        ConversationId = (int)sender.CurrentConversationWith
                    };
                    string jsonResponse = JsonSerializer.Serialize(newMessage);
                    byte[] buffer = Encoding.UTF8.GetBytes(jsonResponse);
                    recipient.Stream.Write(buffer, 0, buffer.Length);

                    // Send acknowledgment to sender
                    Message ackMessage = new Message
                    {
                        SenderId = (int)SystemIds.Server,
                        ReceiverId = recipient.ClientId,
                        Content = "Message delivered.",
                        Timestamp = DateTime.UtcNow.ToString("o"),
                        ConversationId = (int)sender.CurrentConversationWith
                    };
                    string jsonAck = JsonSerializer.Serialize(ackMessage);
                    buffer = Encoding.UTF8.GetBytes(jsonAck);
                    sender.Stream.Write(buffer, 0, buffer.Length);
                }
                else
                {
                    SendMessageToClient(sender, "The client you were connected to is no longer available.");
                    sender.CurrentConversationWith = null; // Reset the conversation state
                }
            }
        }

        public static void SendClientList(ClientHandler requester, List<ClientHandler> clients, object lockObj)
        {
            StringBuilder clientList = new StringBuilder("Active clients:\n");
            lock (lockObj)
            {
                foreach (var client in clients)
                {
                    if (client.ClientId != requester.ClientId)
                    {
                        clientList.AppendLine($"ID: {client.ClientId}, Name: {client.ClientName ?? "Anonymous"}");
                    }
                }
            }
            SendMessageToClient(requester, clientList.ToString());
        }
    }
}
