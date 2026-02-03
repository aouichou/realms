"use client";

import { LanguageSelector } from "@/components/LanguageSelector";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/contexts/AuthContext";
import { LogOut, User as UserIcon } from "lucide-react";

export function AppHeader() {
	const { user, isLoading, logout } = useAuth();

	return (
		<header className="sticky top-0 z-50 w-full border-b border-neutral-500/20 bg-primary-900/95 backdrop-blur-md shadow-md">
			<div className="container flex h-16 items-center justify-between px-4 md:px-6">
				{/* Logo/Brand */}
				<div className="flex items-center gap-2">
					<h1 className="font-display text-xl md:text-2xl text-accent-400 hover:text-accent-600 transition-colors cursor-default">
						Mistral Realms
					</h1>
				</div>

				{/* Right Side: Language Selector + User Menu */}
				<div className="flex items-center gap-3">
					{/* Language Selector */}
					<LanguageSelector />

					{/* User Info & Logout (only when logged in) */}
					{!isLoading && user && (
						<>
							{/* User Info - hidden on small screens */}
							<div className="hidden md:flex items-center gap-2 text-sm text-accent-200">
								<UserIcon className="h-4 w-4" />
								<span className="font-body">
									{user.username}
									{user.is_guest && (
										<span className="ml-1 text-xs text-accent-400">(Guest)</span>
									)}
								</span>
							</div>

							{/* Logout Button */}
							<Button
								variant="outline"
								size="sm"
								onClick={logout}
								className="border-accent-600 bg-accent-600 hover:bg-accent-400 text-primary-900 font-body font-semibold transition-all"
								title="Logout"
							>
								<LogOut className="h-4 w-4 mr-0 sm:mr-2" />
								<span className="hidden sm:inline">Logout</span>
							</Button>
						</>
					)}
				</div>
			</div>
		</header>
	);
}
