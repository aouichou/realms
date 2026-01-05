import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ToastProvider } from "@/components/ui/toast";
import type { Metadata } from "next";
import { Cinzel, UnifrakturMaguntia } from "next/font/google";
import "./globals.css";

const unifraktur = UnifrakturMaguntia({
	weight: "400",
	variable: "--font-display",
	subsets: ["latin"],
});

const cinzel = Cinzel({
	weight: ["400", "500", "600", "700"],
	variable: "--font-body",
	subsets: ["latin"],
});

export const metadata: Metadata = {
	title: "Mistral Realms - AI-Powered D&D Adventures",
	description: "Embark on AI-powered Dungeons & Dragons adventures with Mistral AI",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html lang="en">
			<body
				className={`${unifraktur.variable} ${cinzel.variable} antialiased`}
			>
				<ErrorBoundary>
					<ToastProvider>
						{children}
					</ToastProvider>
				</ErrorBoundary>
			</body>
		</html>
	);
}
