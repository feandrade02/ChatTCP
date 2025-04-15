using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Text.Json;
using System.Reflection.Metadata;
using ConsoleAppTeste.Enums;
using ConsoleAppTeste.Models;
using ConsoleAppTeste.Services;

namespace ConsoleAppTeste
{
    class Program
    {
        static void Main(string[] args)
        {
            var server = new Server();
            server.Start();
        }
    }
}