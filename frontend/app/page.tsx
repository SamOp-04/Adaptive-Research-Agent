import { ChatWindow } from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="h-dvh overflow-hidden bg-[var(--app-bg)] text-[var(--app-text-primary)]">
      <ChatWindow />
    </main>
  );
}
