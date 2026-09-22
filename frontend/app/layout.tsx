import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TigerGraph Agentic Fraud Investigation",
  description: "TigerGraph-first agentic fraud investigation analyst console",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
