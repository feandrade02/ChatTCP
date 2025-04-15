using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using ConsoleAppTeste.Models;
using ConsoleAppTeste.Services;

namespace ConsoleAppTeste
{
    public class Server
    {
        private List<ClientHandler> clients;
        private int nextClientId;
        private readonly object lockObj;
        private bool isServerRunning;
        private readonly TcpListener tcpListener;

        public Server(int port = 8888)
        {
            clients = new List<ClientHandler>();
            nextClientId = 1;
            lockObj = new object();
            isServerRunning = true;
            tcpListener = new TcpListener(IPAddress.Any, port);
        }

        public void Start()
        {
            tcpListener.Start();
            Console.WriteLine("Server started...");

            Thread monitorThread = new Thread(() => MonitoringService.MonitorClients(clients, lockObj));
            monitorThread.Start();

            while (isServerRunning)
            {
                TcpClient client = tcpListener.AcceptTcpClient();
                lock (lockObj)
                {
                    var clientHandler = new ClientHandler(client, nextClientId++);
                    clients.Add(clientHandler);
                    Console.WriteLine($"Client {clientHandler.ClientId} connected.");

                    // Send assigned Client ID to the client
                    MessageService.SendClientId(clientHandler);

                    Thread clientThread = new Thread(() => ClientHandlerService.HandleClient(clientHandler, clients, lockObj));
                    clientThread.Start();
                }
            }
        }

        public void Stop()
        {
            isServerRunning = false;
            tcpListener.Stop();
        }
    }
}
