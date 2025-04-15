using System;
using System.Collections.Generic;
using System.Text;
using System.Text.Json;
using ConsoleAppTeste.Models;
using ConsoleAppTeste.Enums;

namespace ConsoleAppTeste.Services
{
    public static class ClientHandlerService
    {
        public static void HandleClient(object obj, List<ClientHandler> clients, object lockObj)
        {
            ClientHandler clientHandler = (ClientHandler)obj;
            byte[] buffer = new byte[1024];
            int bytesRead;

            try
            {
                while (true)
                {
                    bytesRead = clientHandler.Stream.Read(buffer, 0, buffer.Length);
                    if (bytesRead == 0) break; // Client disconnected

                    string jsonMessage = Encoding.UTF8.GetString(buffer, 0, bytesRead).Trim();
                    Message message = JsonSerializer.Deserialize<Message>(jsonMessage);
                    
                    // Only display messages from the current conversation partner
                    if (message.SenderId == clientHandler.CurrentConversationWith)
                    {
                        Console.WriteLine($"Received from Client {message.SenderId}: {message.Content}");
                    }
                    
                    clientHandler.LastActivity = DateTime.Now;

                    if (message.Content == "heartbeat")
                    {
                        // Update the last activity timestamp without logging or processing
                        clientHandler.LastActivity = DateTime.Now;
                        continue;
                    }

                    // Handle commands
                    if (message.Content == "/list")
                    {
                        MessageService.SendClientList(clientHandler, clients, lockObj);
                    }
                    else if (message.Content.StartsWith("/connect"))
                    {
                        HandleConnectCommand(message.Content, clientHandler, clients, lockObj);
                    }
                    else if (message.Content == "/exit")
                    {
                        clientHandler.CurrentConversationWith = null;
                        MessageService.SendMessageToClient(clientHandler, "Exited conversation. You can start a new one with /connect <client_id>.");
                    }
                    else if (message.Content.StartsWith("/acknoledgment"))
                    {
                        HandleAcknowledgment(message, clients, lockObj);
                    }
                    else
                    {
                        // Send private message if in a conversation
                        if (clientHandler.CurrentConversationWith != null)
                        {
                            MessageService.SendPrivateMessage(clientHandler, message, clients, lockObj);
                        }
                        else
                        {
                            MessageService.SendMessageToClient(clientHandler, "You must start a conversation with /connect <client_id> before sending messages.");
                        }
                    }
                }
            }
            catch (Exception)
            {
                // Handle client disconnection
            }
            finally
            {
                lock (lockObj)
                {
                    clients.Remove(clientHandler);
                }
                clientHandler.Client.Close();
                Console.WriteLine($"Client {clientHandler.ClientId} disconnected.");
            }
        }

        private static void HandleConnectCommand(string message, ClientHandler sender, List<ClientHandler> clients, object lockObj)
        {
            string[] parts = message.Split(' ', 2);
            if (parts.Length != 2 || !int.TryParse(parts[1], out int recipientId))
            {
                MessageService.SendMessageToClient(sender, "Usage: /connect <client_id>");
                return;
            }

            lock (lockObj)
            {
                var recipient = clients.Find(c => c.ClientId == recipientId);
                if (recipient != null)
                {
                    sender.CurrentConversationWith = recipientId;
                    MessageService.SendMessageToClient(sender, $"You are now connected to Client {recipientId}. Type your messages.");
                }
                else
                {
                    MessageService.SendMessageToClient(sender, "Client not found.");
                }
            }
        }

        private static void HandleAcknowledgment(Message sender_message, List<ClientHandler> clients, object lockObj)
        {
            lock (lockObj)
            {
                var sender = clients.Find(c => c.ClientId == sender_message.SenderId);
                var recipient = clients.Find(c => c.ClientId == sender_message.ReceiverId);
                if (recipient != null)
                {
                    // Send acknowledgment to sender
                    Message ackMessage = new Message
                    {
                        SenderId = (int)SystemIds.Server,
                        ReceiverId = recipient.ClientId,
                        Content = "Message Reached!.",
                        Timestamp = DateTime.UtcNow.ToString("o"),
                        ConversationId = sender_message.ReceiverId
                    };
                    
                    string jsonAck = JsonSerializer.Serialize(ackMessage);
                    byte[] buffer = Encoding.UTF8.GetBytes(jsonAck);
                    recipient.Stream.Write(buffer, 0, buffer.Length);
                }
                else
                {
                    MessageService.SendMessageToClient(sender, "The client you were connected to is no longer available.");
                    sender.CurrentConversationWith = null; // Reset the conversation state
                }
            }
        }
    }
}
