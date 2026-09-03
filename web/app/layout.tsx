import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Project Meltdown — Salle de crise",
  description: "Trois jours. Quatre parties prenantes. Chaque décision compte.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
