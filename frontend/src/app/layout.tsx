import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Logopädie Report Agent",
  description:
    "KI-gestütztes Tool zur automatischen Erstellung strukturierter logopädischer Berichte.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className="h-full antialiased" style={{ colorScheme: "dark" }}>
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
