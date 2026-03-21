import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

const display = Fraunces({
  variable: "--font-display",
  subsets: ["latin"],
});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

/** Server-render on each request so `next build` does not require the API to be up. */
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: {
    default: "StoryDiff",
    template: "%s · StoryDiff",
  },
  description: "Consensus, coverage, and framing across outlets",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${display.variable} ${geistSans.variable} ${geistMono.variable}`}
      >
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
