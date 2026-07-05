import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ControlGastos Web",
  description: "Next.js web app for ControlGastos migration to Vercel and Supabase.",
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
