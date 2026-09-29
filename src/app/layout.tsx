import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Desk Assistant",
  description: "AI Desktop Assistant — Ollama + Claude",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" suppressHydrationWarning>
      <body className="h-screen overflow-hidden bg-[#1e1e1e]">
        {children}
      </body>
    </html>
  );
}
