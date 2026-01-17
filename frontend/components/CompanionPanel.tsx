"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { apiClient } from "@/lib/api-client";
import { useTranslation } from "@/lib/hooks/useTranslation";
import { Bot, Heart, MessageSquare, Shield, Sparkles, Users } from "lucide-react";
import { useEffect, useState } from "react";

interface CompanionMessage {
	id: number;
	speech: string;
	personality: string;
	trigger: string;
	timestamp: string;
}

interface CompanionPanelProps {
	characterId: string;
	gameContext: {
		player_hp: number;
		player_max_hp: number;
		in_combat: boolean;
		location: string;
		enemies?: string;
		enemy_count?: number;
		situation?: string;
	};
	onSpeechGenerated?: (speech: string) => void;
}

const PERSONALITY_INFO = {
	helpful: {
		name: "Helpful",
		icon: Heart,
		color: "text-green-400",
		bgColor: "bg-green-400/20",
		borderColor: "border-green-400/30",
		description: "Provides tactical advice and warns of dangers",
	},
	brave: {
		name: "Brave",
		icon: Shield,
		color: "text-red-400",
		bgColor: "bg-red-400/20",
		borderColor: "border-red-400/30",
		description: "Encourages heroic actions and bold strategies",
	},
	cautious: {
		name: "Cautious",
		icon: Users,
		color: "text-yellow-400",
		bgColor: "bg-yellow-400/20",
		borderColor: "border-yellow-400/30",
		description: "Prioritizes safety and warns about risks",
	},
	sarcastic: {
		name: "Sarcastic",
		icon: MessageSquare,
		color: "text-purple-400",
		bgColor: "bg-purple-400/20",
		borderColor: "border-purple-400/30",
		description: "Witty and humorous commentary",
	},
	mysterious: {
		name: "Mysterious",
		icon: Sparkles,
		color: "text-indigo-400",
		bgColor: "bg-indigo-400/20",
		borderColor: "border-indigo-400/30",
		description: "Cryptic hints and hidden knowledge",
	},
	scholarly: {
		name: "Scholarly",
		icon: Bot,
		color: "text-blue-400",
		bgColor: "bg-blue-400/20",
		borderColor: "border-blue-400/30",
		description: "Academic knowledge and lore",
	},
};

const TRIGGERS = [
	{ value: "combat_start", label: "Combat Start" },
	{ value: "player_low_hp", label: "Low HP" },
	{ value: "exploration", label: "Exploration" },
	{ value: "victory", label: "Victory" },
	{ value: "puzzle", label: "Puzzle" },
	{ value: "monster_encounter", label: "Monster" },
	{ value: "player_action", label: "Player Action" },
	{ value: "lore_discovery", label: "Lore Discovery" },
];

export function CompanionPanel({ characterId, gameContext, onSpeechGenerated }: CompanionPanelProps) {
	const { t } = useTranslation();
	const [messages, setMessages] = useState<CompanionMessage[]>([]);
	const [selectedPersonality, setSelectedPersonality] = useState<string>("helpful");
	const [selectedTrigger, setSelectedTrigger] = useState<string>("exploration");
	const [companionName, setCompanionName] = useState<string>("Aria");
	const [companionRace, setCompanionRace] = useState<string>("Elf");
	const [companionClass, setCompanionClass] = useState<string>("Ranger");
	const [isGenerating, setIsGenerating] = useState(false);
	const [autoRespond, setAutoRespond] = useState(true);

	// Load messages from localStorage on mount
	useEffect(() => {
		const savedMessages = localStorage.getItem(`companion_messages_${characterId}`);
		if (savedMessages) {
			try {
				setMessages(JSON.parse(savedMessages));
			} catch (e) {
				console.error("Failed to load companion messages:", e);
			}
		}

		// Load companion settings
		const savedSettings = localStorage.getItem(`companion_settings_${characterId}`);
		if (savedSettings) {
			try {
				const settings = JSON.parse(savedSettings);
				setSelectedPersonality(settings.personality || "helpful");
				setCompanionName(settings.name || "Aria");
				setCompanionRace(settings.race || "Elf");
				setCompanionClass(settings.class || "Ranger");
			} catch (e) {
				console.error("Failed to load companion settings:", e);
			}
		}
	}, [characterId]);

	// Save messages to localStorage
	useEffect(() => {
		if (messages.length > 0) {
			localStorage.setItem(`companion_messages_${characterId}`, JSON.stringify(messages));
		}
	}, [messages, characterId]);

	// Save companion settings
	useEffect(() => {
		localStorage.setItem(
			`companion_settings_${characterId}`,
			JSON.stringify({
				personality: selectedPersonality,
				name: companionName,
				race: companionRace,
				class: companionClass,
			})
		);
	}, [selectedPersonality, companionName, companionRace, companionClass, characterId]);

	// Auto-respond to specific game events
	useEffect(() => {
		if (!autoRespond) return;

		// Auto-trigger on combat start
		if (gameContext.in_combat && messages.length === 0) {
			generateSpeech("combat_start");
		}

		// Auto-trigger on low HP
		const hpPercentage = (gameContext.player_hp / gameContext.player_max_hp) * 100;
		if (hpPercentage < 30 && hpPercentage > 0) {
			const lastMessage = messages[messages.length - 1];
			const timeSinceLastMessage = lastMessage
				? Date.now() - new Date(lastMessage.timestamp).getTime()
				: Infinity;

			// Only trigger if it's been at least 30 seconds since last message
			if (timeSinceLastMessage > 30000) {
				generateSpeech("player_low_hp");
			}
		}
	}, [gameContext.in_combat, gameContext.player_hp, autoRespond]);

	const generateSpeech = async (trigger?: string) => {
		setIsGenerating(true);
		try {
			const response = await apiClient.post("/api/v1/companion/speech", {
				personality: selectedPersonality,
				companion_name: companionName,
				companion_race: companionRace,
				companion_class: companionClass,
				trigger: trigger || selectedTrigger,
				context: {
					...gameContext,
					companion_hp: 30, // TODO: Get from actual companion stats
					companion_max_hp: 30,
				},
			});

			if (response.ok) {
				const data = await response.json();
				const newMessage: CompanionMessage = {
					id: Date.now(),
					speech: data.speech,
					personality: data.personality,
					trigger: data.trigger,
					timestamp: new Date().toISOString(),
				};

				setMessages((prev) => [...prev, newMessage]);

				if (onSpeechGenerated) {
					onSpeechGenerated(data.speech);
				}
			}
		} catch (error) {
			console.error("Error generating companion speech:", error);
		} finally {
			setIsGenerating(false);
		}
	};

	const clearMessages = () => {
		setMessages([]);
		localStorage.removeItem(`companion_messages_${characterId}`);
	};

	const personalityInfo = PERSONALITY_INFO[selectedPersonality as keyof typeof PERSONALITY_INFO];
	const PersonalityIcon = personalityInfo.icon;

	return (
		<Card className="h-full flex flex-col">
			<CardHeader className="pb-3">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						<PersonalityIcon className={`h-5 w-5 ${personalityInfo.color}`} />
						<CardTitle className="text-lg">{t('game.companion.title')}</CardTitle>
					</div>
					<Badge variant="outline" className={personalityInfo.borderColor}>
						{companionName}
					</Badge>
				</div>
				<CardDescription className="text-xs">
					{personalityInfo.description}
				</CardDescription>
			</CardHeader>

			<CardContent className="flex-1 flex flex-col gap-3 overflow-hidden">
				{/* Personality Selection */}
				<div className="space-y-2">
					<label className="text-xs font-medium">{t('game.companion.personality')}</label>
					<Select value={selectedPersonality} onValueChange={setSelectedPersonality}>
						<SelectTrigger className="h-8 text-sm">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							{Object.entries(PERSONALITY_INFO).map(([key, info]) => {
								const Icon = info.icon;
								return (
									<SelectItem key={key} value={key}>
										<div className="flex items-center gap-2">
											<Icon className={`h-4 w-4 ${info.color}`} />
											<span>{t(`game.companion.personalities.${key}`)}</span>
										</div>
									</SelectItem>
								);
							})}
						</SelectContent>
					</Select>
				</div>

				{/* Trigger Selection */}
				<div className="space-y-2">
					<label className="text-xs font-medium">{t('game.companion.trigger')}</label>
					<Select value={selectedTrigger} onValueChange={setSelectedTrigger}>
						<SelectTrigger className="h-8 text-sm">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							{TRIGGERS.map((trigger) => (
								<SelectItem key={trigger.value} value={trigger.value}>
									{t(`game.companion.triggers.${trigger.value}`)}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				</div>

				{/* Generate Button */}
				<Button
					onClick={() => generateSpeech()}
					disabled={isGenerating}
					className="w-full h-8 text-sm"
					size="sm"
				>
					{isGenerating ? t('game.companion.generating') : t('game.companion.generateSpeech')}
				</Button>

				{/* Auto-respond Toggle */}
				<div className="flex items-center justify-between text-xs">
					<span className="text-muted-foreground">{t('game.companion.autoRespond')}</span>
					<Button
						variant="outline"
						size="sm"
						className="h-6 px-2"
						onClick={() => setAutoRespond(!autoRespond)}
					>
						{autoRespond ? t('game.companion.on') : t('game.companion.off')}
					</Button>
				</div>

				{/* Messages */}
				<div className="flex-1 flex flex-col min-h-0">
					<div className="flex items-center justify-between mb-2">
						<label className="text-xs font-medium">{t('game.companion.messages')} ({messages.length})</label>
						{messages.length > 0 && (
							<Button
								variant="ghost"
								size="sm"
								className="h-6 px-2 text-xs"
								onClick={clearMessages}
							>
								{t('game.companion.clear')}
							</Button>
						)}
					</div>

					<ScrollArea className="flex-1 border rounded-md p-2">
						<div className="space-y-2">
							{messages.length === 0 ? (
								<div className="text-center text-xs text-muted-foreground py-8">
									<Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
									<p>{t('game.companion.noMessages')}</p>
									<p className="text-[10px] mt-1">
										{t('game.companion.speakDuringMoments')}
									</p>
								</div>
							) : (
								messages.map((message) => {
									const msgPersonality = PERSONALITY_INFO[message.personality as keyof typeof PERSONALITY_INFO];
									return (
										<div
											key={message.id}
											className={`p-2 rounded-lg ${msgPersonality.bgColor} ${msgPersonality.borderColor} border`}
										>
											<div className="flex items-center gap-1 mb-1">
												<Badge variant="outline" className="h-5 px-1.5 text-[10px]">
													{message.trigger.replace(/_/g, " ")}
												</Badge>
												<span className="text-[9px] text-muted-foreground">
													{new Date(message.timestamp).toLocaleTimeString()}
												</span>
											</div>
											<p className="text-xs leading-relaxed">{message.speech}</p>
										</div>
									);
								})
							)}
						</div>
					</ScrollArea>
				</div>
			</CardContent>
		</Card>
	);
}
