import ChatPanel from '@/components/ChatPanel';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-muted/40 p-4 md:p-8">
      <ChatPanel />
    </main>
  );
}
