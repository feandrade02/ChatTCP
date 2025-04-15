using System;
using System.Net.Sockets;

namespace ConsoleAppTeste.Models
{
    public class ClientHandler
    {
        public TcpClient Client { get; set; }
        public int ClientId { get; set; }
        public string ClientName { get; set; }
        public NetworkStream Stream { get; set; }
        public DateTime LastActivity { get; set; }
        public int? CurrentConversationWith { get; set; } // ID of the client the user is currently talking to

        public ClientHandler(TcpClient client, int clientId)
        {
            Client = client;
            ClientId = clientId;
            Stream = client.GetStream();
            LastActivity = DateTime.Now;
            CurrentConversationWith = null;
        }
    }
}
