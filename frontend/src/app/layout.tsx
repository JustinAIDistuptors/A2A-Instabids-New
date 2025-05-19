import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { cn } from "@/lib/utils"; 
import { AgentStatusBadge } from "@/components/agent-status-badge"; 
import { Toaster } from 'sonner'; // Import Toaster from 'sonner'

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

            {/* Navigation Links */}
            <nav className="hidden md:flex flex-grow items-center space-x-6 text-sm font-medium">
              <Link href="/" className="text-foreground/80 hover:text-foreground transition-colors">
                Chat
              </Link>
              <Link href="/bids/new" className="text-foreground/80 hover:text-foreground transition-colors">
                Create Bid
              </Link>
              <Link href="/bids" className="text-foreground/80 hover:text-foreground transition-colors">
                My Bids
              </Link>
              <Link href="/settings" className="text-foreground/80 hover:text-foreground transition-colors">
                Settings
              </Link>
            </nav>

            {/* Right side: User Profile/Settings Placeholder & Agent Status */}
            <div className="flex items-center space-x-4">
              <div className="hidden sm:block text-sm text-foreground/60">{/* User Profile Placeholder */}</div>
              <AgentStatusBadge status="online" />
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Footer Placeholder (Optional) */}
        <footer className="border-t py-6 md:py-0">
          <div className="container mx-auto flex flex-col items-center justify-center gap-4 md:h-24 md:flex-row">
            <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
              &copy; {new Date().getFullYear()} InstaBids. All rights reserved.
            </p>
          </div>
        </footer>
        <Toaster /> {/* Add Toaster here for global notifications */}
      </body>
    </html>
  );
}
