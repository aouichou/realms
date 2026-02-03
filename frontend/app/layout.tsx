import { AppHeader } from "@/components/AppHeader";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ToastProvider } from "@/components/ui/toast";
import { AuthProvider } from "@/lib/contexts/AuthContext";
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
					<QueryProvider>
						<AuthProvider>
							<ToastProvider>
								<AppHeader />
								{children}
							</ToastProvider>
						</AuthProvider>
					</QueryProvider>
				</ErrorBoundary>
			</body>
		</html>
	);
}
