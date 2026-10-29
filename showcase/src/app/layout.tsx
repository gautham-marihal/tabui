import type { Metadata } from "next";
import Script from "next/script";
import { ClerkProvider } from "@clerk/nextjs";

import { clerkConfigured } from "@/lib/clerkSetting";

import { Geist, Geist_Mono } from "next/font/google";

import "./css/reset.scss";
import "./css/globals.scss";
import "./css/page-styles.scss";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Tetherfi MX Bots",
  description: "Tetherfi Multi Modal AI Agent",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const page = (
    <html lang="en">
      <head>
        <link rel="icon" href="/tetherfi-favicon.png" sizes="any" />

        <link rel="stylesheet" href="/tab-widget/tab-widget.css" />
        <Script
          src="/tab-widget/tab-widget.iife.js"
          strategy="beforeInteractive"
        ></Script>
      </head>

      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );

  // sign-in wraps the site only when it is set up (see lib/auth.ts)
  return clerkConfigured ? <ClerkProvider>{page}</ClerkProvider> : page;
}
