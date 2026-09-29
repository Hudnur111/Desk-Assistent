'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/appStore';
import { TitleBar } from '@/components/TitleBar';
import { Sidebar } from '@/components/Sidebar';
import { ChatPanel } from '@/components/ChatPanel';
import { StatusBar } from '@/components/StatusBar';

export default function HomePage() {
  const router = useRouter();
  const { isSetupComplete, sidebarOpen } = useAppStore();

  useEffect(() => {
    if (!isSetupComplete) router.push('/setup');
  }, [isSetupComplete, router]);

  if (!isSetupComplete) return null;

  return (
    <div className="h-screen flex flex-col bg-[#1e1e1e] overflow-hidden">
      <TitleBar />
      <div className="flex flex-1 overflow-hidden">
        {sidebarOpen && <Sidebar />}
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatPanel />
        </main>
      </div>
      <StatusBar />
    </div>
  );
}
