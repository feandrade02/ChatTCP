using System;
using System.Collections.Generic;
using System.Threading;
using ConsoleAppTeste.Models;

namespace ConsoleAppTeste.Services
{
    public static class MonitoringService
    {
        public static void MonitorClients(List<ClientHandler> clients, object lockObj)
        {
            while (true)
            {
                Thread.Sleep(1000); // Check every second
                lock (lockObj)
                {
                    for (int i = clients.Count - 1; i >= 0; i--)
                    {
                        if ((DateTime.Now - clients[i].LastActivity).TotalSeconds > 60)
                        {
                            Console.WriteLine($"Client {clients[i].ClientId} is offline (inactive for over 1 minute). Disconnecting...");
                            clients[i].Client.Close();
                            clients.RemoveAt(i);
                        }
                    }
                }
            }
        }
    }
}
