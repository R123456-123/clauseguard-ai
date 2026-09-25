import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClauseGuard AI — Legal Contract Risk Analysis",
  description:
    "AI-powered legal contract risk analysis tool. Upload contracts, identify risky clauses, " +
    "and generate negotiation preparation packs using Google Gemini AI.",
  keywords: [
    "legal",
    "contract",
    "risk analysis",
    "AI",
    "clause extraction",
    "negotiation",
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
