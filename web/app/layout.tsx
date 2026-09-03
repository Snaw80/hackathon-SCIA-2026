import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Project Meltdown — Crisis room",
  description: "Three days. Four stakeholders. Every decision matters.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
