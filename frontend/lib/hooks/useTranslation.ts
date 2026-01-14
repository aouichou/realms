import enTranslations from "@/locales/en.json";
import frTranslations from "@/locales/fr.json";
import { useEffect, useState } from "react";

const translations = {
	en: enTranslations,
	fr: frTranslations,
};

export type Language = "en" | "fr";

export function useTranslation() {
	const [language, setLanguage] = useState<Language>("en");

	useEffect(() => {
		// Load saved language preference
		const savedLanguage = localStorage.getItem("dm_language") as Language;
		if (savedLanguage && (savedLanguage === "en" || savedLanguage === "fr")) {
			setLanguage(savedLanguage);
		}

		// Listen for language changes
		const handleStorageChange = (e: StorageEvent) => {
			if (e.key === "dm_language" && e.newValue) {
				const newLang = e.newValue as Language;
				if (newLang === "en" || newLang === "fr") {
					setLanguage(newLang);
				}
			}
		};

		// Listen for custom event (for same-window updates)
		const handleLanguageChange = ((e: CustomEvent) => {
			const newLang = e.detail as Language;
			if (newLang === "en" || newLang === "fr") {
				setLanguage(newLang);
			}
		}) as EventListener;

		window.addEventListener("storage", handleStorageChange);
		window.addEventListener("languageChange", handleLanguageChange);

		return () => {
			window.removeEventListener("storage", handleStorageChange);
			window.removeEventListener("languageChange", handleLanguageChange);
		};
	}, []);

	const t = (key: string): string => {
		const keys = key.split(".");
		let value: any = translations[language];

		for (const k of keys) {
			if (value && typeof value === "object") {
				value = value[k];
			} else {
				return key; // Return key if translation not found
			}
		}

		return typeof value === "string" ? value : key;
	};

	return { t, language, setLanguage };
}
