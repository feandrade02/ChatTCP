namespace ConsoleAppTeste.Models
{
    public class Message
    {
        public int SenderId { get; set; }
        public int ReceiverId { get; set; }
        public string Content { get; set; }
        public string Timestamp { get; set; }
        public int ConversationId { get; set; }
    }
}
