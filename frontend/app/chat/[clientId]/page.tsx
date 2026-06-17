import { ChatWindow } from '@/components/chat/ChatWindow'

// Per-client console. The {clientId} segment makes each console URL unique;
// conversation scoping uses the same stable client id (see UserSync / getClientId).
export default function ChatConsolePage() {
  return <ChatWindow />
}
