/** App shell that mounts the WhatsApp-style triage chatbot. */
import { TriageChat } from "./components/TriageChat/TriageChat";

export function App() {
  return (
    <div style={{ height: "100vh" }}>
      <TriageChat />
    </div>
  );
}

