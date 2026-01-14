"use client";

import { Button } from "@/components/ui/button";
import { Globe } from "lucide-react";
import { useEffect, useState } from "react";

interface LanguageSelectorProps {
	onLanguageChange?: (language: string) => void;
}

export function LanguageSelector({ onLanguageChange }: LanguageSelectorProps) {
	const [language, setLanguage] = useState<string>("en");

	useEffect(() => {
		// Load saved language preference
		const savedLanguage = localStorage.getItem("dm_language");
		if (savedLanguage) {
			setLanguage(savedLanguage);
		}
	}, []);

	const handleLanguageToggle = () => {
		const newLanguage = language === "en" ? "fr" : "en";
		setLanguage(newLanguage);
		localStorage.setItem("dm_language", newLanguage);

		// Dispatch custom event for same-window updates
		window.dispatchEvent(
			new CustomEvent("languageChange", { detail: newLanguage })
		);

		// Callback for parent components
		if (onLanguageChange) {
			onLanguageChange(newLanguage);
		}
	};

	return (
		<Button
			variant="outline"
			size="sm"
			onClick={handleLanguageToggle}
			className="flex items-center gap-2"
			title={`Switch to ${language === "en" ? "French" : "English"}`}
		>
			<Globe className="h-4 w-4" />
			<span className="font-medium">{language === "en" ? "EN" : "FR"}</span>
		</Button>
	);
}
