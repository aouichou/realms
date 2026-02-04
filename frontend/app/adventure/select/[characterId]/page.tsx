"use client";

import AdventurePreview from "@/components/adventure/AdventurePreview";
import { CustomAdventureWizard } from "@/components/adventure/CustomAdventureWizard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { apiClient } from "@/lib/api-client";
import { useTranslation } from "@/lib/hooks/useTranslation";
import { ArrowRight, Scroll, Sparkles, Sword } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface PresetAdventure {
	id: string;
	title: string;
	description: string;
	recommended_level: number;
	setting: string;
}

interface CustomAdventure {
	id: string;
	character_id: string;
	setting: string;
	goal: string;
	tone: string;
	title: string;
	description: string;
	scenes: any[];
	is_completed: boolean;
	created_at: string;
}

interface Character {
	id: string;
	name: string;
	level: number;
	character_class: string;
	race: string;
}

export default function AdventureSelectionPage() {
	const params = useParams();
	const router = useRouter();
	const { showToast } = useToast();
	const { t } = useTranslation();
	const characterId = params.characterId as string;

	const [character, setCharacter] = useState<Character | null>(null);
	const [presetAdventures, setPresetAdventures] = useState<PresetAdventure[]>([]);
	const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [showCustomWizard, setShowCustomWizard] = useState(false);
	const [generatedAdventure, setGeneratedAdventure] = useState<CustomAdventure | null>(null);
	const [customAdventures, setCustomAdventures] = useState<CustomAdventure[]>([]);
	const [activeTab, setActiveTab] = useState<"preset" | "custom">("preset");

	useEffect(() => {
		loadCharacter();
		loadPresetAdventures();
		loadCustomAdventures();
	}, [characterId]);

	const loadCharacter = async () => {
		try {
			const response = await apiClient.get(`/api/v1/characters/${characterId}`);
			if (response.ok) {
				const data = await response.json();
				setCharacter(data);
			}
		} catch (error) {
			console.error("Error loading character:", error);
			showToast("Failed to load character", "error");
		}
	};

	const loadPresetAdventures = async () => {
		try {
			const response = await apiClient.get("/api/v1/adventures/list");
			if (response.ok) {
				const data = await response.json();
				setPresetAdventures(data);
			}
		} catch (error) {
			console.error("Error loading adventures:", error);
		}
	};

	const loadCustomAdventures = async () => {
		try {
			const response = await apiClient.get(`/api/v1/adventures/custom/character/${characterId}`);
			if (response.ok) {
				const data = await response.json();
				setCustomAdventures(data);
			}
		} catch (error) {
			console.error("Error loading custom adventures:", error);
		}
	};

	const startPresetAdventure = async (adventureId: string) => {
		setIsLoading(true);
		try {
			const response = await apiClient.post("/api/v1/adventures/start-preset", {
				character_id: characterId,
				adventure_id: adventureId,
			});

			if (response.ok) {
				const data = await response.json();
				showToast(t('adventure.select.adventureStarted'), "success");
				// Redirect to game page with session data
				router.push(`/game/${characterId}?session=${data.session_id}`);
			} else {
				showToast(t('adventure.select.startFailed'), "error");
			}
		} catch (error) {
			console.error("Error starting adventure:", error);
			showToast(t('adventure.select.startFailed'), "error");
		} finally {
			setIsLoading(false);
		}
	};

	const handleCustomWizardComplete = (adventureId: string, adventure: CustomAdventure) => {
		setGeneratedAdventure(adventure);
		setShowCustomWizard(false);
	};

	const handleStartCustomAdventure = async (adventureId: string) => {
		setIsLoading(true);
		try {
			const response = await apiClient.post("/api/v1/adventures/start-custom", {
				character_id: characterId,
				adventure_id: adventureId,
			});

			if (response.ok) {
				const data = await response.json();
				showToast(t('adventure.select.customStarting'), "success");
				// Redirect to game page with session data
				router.push(`/game/${characterId}?session=${data.session_id}`);
			} else {
				showToast(t('adventure.select.startFailed'), "error");
			}
		} catch (error) {
			console.error("Error starting custom adventure:", error);
			showToast(t('adventure.select.startFailed'), "error");
		} finally {
			setIsLoading(false);
		}
	};

	if (!character) {
		return (
			<div className="min-h-screen flex items-center justify-center">
				<LoadingSpinner />
			</div>
		);
	}

	// Show custom wizard if active
	if (showCustomWizard) {
		return (
			<CustomAdventureWizard
				characterId={characterId}
				onComplete={handleCustomWizardComplete}
				onCancel={() => setShowCustomWizard(false)}
			/>
		);
	}

	// Show generated adventure preview
	if (generatedAdventure) {
		return (
			<AdventurePreview
				adventure={generatedAdventure}
				onStart={handleStartCustomAdventure}
				onCancel={() => setGeneratedAdventure(null)}
			/>
		);
	}

	return (
		<div className="min-h-screen bg-linear-to-br from-primary-900 via-secondary-600 to-primary-900 p-8">
			<div className="max-w-6xl mx-auto">
				{/* Header */}
				<div className="text-center mb-8">
					<h1 className="font-display text-5xl text-accent-200 mb-2">
						{t('adventure.select.title')}
					</h1>
					<p className="text-accent-200/80 font-body text-lg">
						{t('adventure.select.welcome')}, <span className="font-semibold text-accent-400">{character.name}</span> the{" "}
						<span className="font-semibold text-accent-400">{character.race} {character.character_class}</span>
					</p>
					<p className="text-accent-200/70 mt-2">
						{t('adventure.select.subtitle')}
					</p>
				</div>

				{/* Tabs for Preset vs Custom */}
				<Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "preset" | "custom")}>
					<TabsList className="grid w-full max-w-md mx-auto grid-cols-2 mb-8">
						<TabsTrigger value="preset" className="flex items-center gap-2">
							<Scroll className="h-4 w-4" />
							{t('adventure.select.presetTab')}
						</TabsTrigger>
						<TabsTrigger value="custom" className="flex items-center gap-2">
							<Sparkles className="h-4 w-4" />
							{t('adventure.select.customTab')}
						</TabsTrigger>
					</TabsList>

					{/* Preset Adventures Tab */}
					<TabsContent value="preset">
						<div className="grid gap-4 md:grid-cols-2">
							{presetAdventures.map((adventure) => {
								const isSelected = selectedPreset === adventure.id;
								const isAppropriateLevel = adventure.recommended_level <= character.level + 1;

								return (
									<Card
										key={adventure.id}
										className={`cursor-pointer transition-all hover:border-primary hover:shadow-lg ${isSelected ? "border-primary ring-2 ring-primary" : ""
											}`}
										onClick={() => setSelectedPreset(adventure.id)}
									>
										<CardHeader>
											<div className="flex items-start justify-between">
												<div className="flex-1">
													<CardTitle className="flex items-center gap-2">
														<Sword className="h-5 w-5 text-red-500" />
														{adventure.title}
													</CardTitle>
													<CardDescription className="text-sm mt-1">
														{adventure.setting}
													</CardDescription>
												</div>
												<Badge
													variant={isAppropriateLevel ? "default" : "destructive"}
													className="ml-2"
												>
													{t('adventure.select.levelLabel')} {adventure.recommended_level}
												</Badge>
											</div>
										</CardHeader>
										<CardContent>
											<p className="text-sm text-accent-200/70 mb-4">
												{adventure.description}
											</p>
											{!isAppropriateLevel && (
												<p className="text-xs text-amber-600 dark:text-amber-400">
													{t('adventure.select.challengingWarning')}
												</p>
											)}
										</CardContent>
									</Card>
								);
							})}
						</div>

						{/* Start Preset Adventure Button */}
						<div className="flex justify-center mt-8">
							<Button
								size="lg"
								onClick={() => selectedPreset && startPresetAdventure(selectedPreset)}
								disabled={!selectedPreset || isLoading}
								className="px-8 border-2 border-accent-600 shadow-lg hover:border-accent-400 transition-colors"
							>
								{isLoading ? (
									<LoadingSpinner />
								) : (
									<>
										{t('adventure.select.beginAdventure')}
										<ArrowRight className="ml-2 h-5 w-5" />
									</>
								)}
							</Button>
						</div>
					</TabsContent>

					{/* Custom Adventure Tab */}
					<TabsContent value="custom">					{customAdventures.length > 0 && (
						<div className="mb-8">
							<h2 className="text-2xl font-display text-accent-200 mb-4">{t('adventure.select.customTitle')}</h2>
							<div className="grid gap-4 md:grid-cols-2">
								{customAdventures.map((adventure) => (
									<Card
										key={adventure.id}
										className="cursor-pointer transition-all hover:border-accent-600 hover:shadow-lg border-accent-600/30"
										onClick={() => setGeneratedAdventure(adventure)}
									>
										<CardHeader>
											<CardTitle className="text-xl">{adventure.title}</CardTitle>
											<CardDescription className="text-xs">
												{t('adventure.select.created')} {new Date(adventure.created_at).toLocaleDateString()}
											</CardDescription>
										</CardHeader>
										<CardContent>
											<p className="text-sm text-accent-200/70 line-clamp-3">
												{adventure.description}
											</p>
											<div className="flex gap-2 mt-3">
												<Badge variant="secondary">{adventure.setting}</Badge>
												<Badge variant="secondary">{adventure.goal}</Badge>
												<Badge variant="secondary">{adventure.tone}</Badge>
											</div>
										</CardContent>
									</Card>
								))}
							</div>
						</div>
					)}
						<Card className="max-w-2xl mx-auto">
							<CardHeader>
								<CardTitle className="flex items-center gap-2 text-2xl">
									<Sparkles className="h-6 w-6 text-amber-500" />
									{t('adventure.select.aiGeneratedTitle')}
								</CardTitle>
								<CardDescription>
									{t('adventure.select.aiGeneratedDescription')}
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-4">
								<div className="bg-muted p-4 rounded-lg">
									<h3 className="font-semibold mb-2">{t('adventure.select.howItWorksTitle')}</h3>
									<ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
										<li>{t('adventure.select.howItWorks1')}</li>
										<li>{t('adventure.select.howItWorks2')}</li>
										<li>{t('adventure.select.howItWorks3')}</li>
										<li>{t('adventure.select.howItWorks4')}</li>
									</ol>
								</div>

								<div className="flex flex-col gap-3">
									<Button
										size="lg"
										onClick={() => setShowCustomWizard(true)}
										className="w-full"
									>
										<Sparkles className="mr-2 h-5 w-5" />
										{t('adventure.select.createCustom')}
									</Button>
									<Button
										variant="outline"
										size="lg"
										onClick={() => setActiveTab("preset")}
										className="w-full"
									>
										{t('adventure.select.backToPreset')}
									</Button>
								</div>
							</CardContent>
						</Card>
					</TabsContent>
				</Tabs>
			</div>
		</div>
	);
}
