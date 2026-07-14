import { ChatWindow } from "@/components/ChatWindow";

export default function Home() {
  return (
    <main className="min-h-dvh overflow-y-auto bg-[var(--app-bg)] text-zinc-950 md:h-dvh md:overflow-hidden">
      <ChatWindow />
    </main>
  );
}
