import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "PropSignal",
  description: "Property signal ranking and dashboard",
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
