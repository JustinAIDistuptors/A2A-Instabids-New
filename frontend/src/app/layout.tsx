import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils"; 
import { AgentStatusBadge } from "@/components/agent-status-badge"; 

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "InstaBids",
  description: "AI-Powered Bidding for Homeowners and Contractors",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          inter.variable
        )}
      >
        {/* Enhanced Header */}
        <header className="border-b sticky top-0 z-50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
            {/* App Name/Logo Placeholder */}
            <div className="mr-6 flex items-center">
              <a href="/" className="font-bold text-xl">InstaBids</a>
            </div>

            {/* Navigation Links Placeholder */}
            <nav className="hidden md:flex flex-grow items-center space-x-6 text-sm font-medium">
              {/* <a href="/dashboard" className="text-foreground/60 hover:text-foreground/80">Dashboard</a> */}
              {/* <a href="/bids" className="text-foreground/60 hover:text-foreground/80">My Bids</a> */}
              {/* <a href="/settings" className="text-foreground/60 hover:text-foreground/80">Settings</a> */}
              <p className="text-foreground/60">Nav Links Placeholder</p>
            </nav>

            {/* Right side: User Profile/Settings Placeholder & Agent Status */}
            <div className="flex items-center space-x-4">
              <div className="hidden sm:block text-sm text-foreground/60">{/* User Profile Placeholder */}</div>
              <AgentStatusBadge status="online" />
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-grow">
          {children}
        </main>

        {/* Footer Placeholder (Optional) */}
        {/* <footer className="py-6 md:px-8 md:py-0 border-t">
          <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
            <p className="text-balance text-center text-sm leading-loose text-muted-foreground md:text-left">
              &copy; {new Date().getFullYear()} InstaBids. All rights reserved.
            </p>
          </div>
        </footer> */}
      </body>
    </html>
  );
}
