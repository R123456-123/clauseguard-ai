import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClauseGuard AI — Legal Document Assistant",
  description:
    "AI-powered legal document assistant for contract risk review, clause explanations, and document Q&A.",
  keywords: [
    "legal AI",
    "contract review",
    "document assistant",
    "legal risk analysis",
    "contract Q&A",
    "clause explanation",
    "negotiation prep",
  ],
  robots: "index, follow",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
