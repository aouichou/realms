"use client";

import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
	ChevronRight,
	Gem,
	MapPin,
	Palette,
	Play,
	Sparkles,
	Swords,
	Target,
	Users,
	X,
} from "lucide-react";
import { useState } from "react";

interface NPC {
	name: string;
	race: string;
	role: string;
	personality: string;
}

interface LootItem {
	item: string;
	description: string;
	value: number;
}

interface Scene {
	scene_number: number;
	title: string;
	description: string;
	encounters: string[];
	npcs: NPC[];
	loot: LootItem[];
}

interface Adventure {
	id: string;
	character_id: string;
	setting: string;
	goal: string;
	tone: string;
	title: string;
	description: string;
	scenes: Scene[];
	is_completed: boolean;
	created_at: string;
}

interface AdventurePreviewProps {
	adventure: Adventure;
	onStart: (adventureId: string) => void;
	onCancel: () => void;
}

// Setting/Goal/Tone display names
const SETTING_NAMES: Record<string, string> = {
	haunted_castle: "Haunted Castle",
	ancient_ruins: "Ancient Ruins",
	dark_forest: "Dark Forest",
	underground_dungeon: "Underground Dungeon",
	pirate_port: "Pirate Port",
	desert_oasis: "Desert Oasis",
	mountain_peak: "Mountain Peak",
	mystical_academy: "Mystical Academy",
};

const GOAL_NAMES: Record<string, string> = {
	rescue_mission: "Rescue Mission",
	find_artifact: "Find Artifact",
	defeat_villain: "Defeat Villain",
	solve_mystery: "Solve Mystery",
	treasure_hunt: "Treasure Hunt",
	diplomatic_mission: "Diplomatic Mission",
	exploration: "Exploration",
	survival: "Survival",
};

const TONE_NAMES: Record<string, string> = {
	epic_heroic: "Epic & Heroic",
	dark_gritty: "Dark & Gritty",
	lighthearted: "Lighthearted",
	horror: "Horror",
	mystery: "Mystery",
};

export default function AdventurePreview({
	adventure,
	onStart,
	onCancel,
}: AdventurePreviewProps) {
	const [startingAdventure, setStartingAdventure] = useState(false);

	const handleStart = async () => {
		setStartingAdventure(true);
		try {
			await onStart(adventure.id);
		} catch (error) {
			console.error("Failed to start adventure:", error);
			setStartingAdventure(false);
		}
	};

	return (
		<div className="container mx-auto max-w-4xl p-6">
			{/* Header */}
			<div className="mb-6">
				<div className="flex items-start justify-between">
					<div className="flex-1">
						<h1 className="text-3xl font-bold mb-2 flex items-center gap-2">
							<Sparkles className="h-8 w-8 text-amber-500" />
							{adventure.title}
						</h1>
						<p className="text-muted-foreground">{adventure.description}</p>
					</div>
					<Button variant="ghost" size="icon" onClick={onCancel}>
						<X className="h-5 w-5" />
					</Button>
				</div>

				{/* Adventure Metadata */}
				<div className="flex flex-wrap gap-2 mt-4">
					<Badge variant="secondary" className="flex items-center gap-1">
						<MapPin className="h-3 w-3" />
						{SETTING_NAMES[adventure.setting] || adventure.setting}
					</Badge>
					<Badge variant="secondary" className="flex items-center gap-1">
						<Target className="h-3 w-3" />
						{GOAL_NAMES[adventure.goal] || adventure.goal}
					</Badge>
					<Badge variant="secondary" className="flex items-center gap-1">
						<Palette className="h-3 w-3" />
						{TONE_NAMES[adventure.tone] || adventure.tone}
					</Badge>
				</div>
			</div>

			<Separator className="my-6" />

			{/* Scenes */}
			<div className="mb-6">
				<h2 className="text-2xl font-bold mb-4">Adventure Scenes</h2>
				<ScrollArea className="h-[500px] pr-4">
					<Accordion type="single" collapsible className="space-y-4">
						{adventure.scenes.map((scene, index) => (
							<AccordionItem
								key={scene.scene_number}
								value={`scene-${scene.scene_number}`}
								className="border rounded-lg"
							>
								<AccordionTrigger className="px-4 hover:no-underline">
									<div className="flex items-center gap-3 text-left">
										<div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">
											{scene.scene_number}
										</div>
										<span className="font-semibold">{scene.title}</span>
									</div>
								</AccordionTrigger>
								<AccordionContent className="px-4 pb-4">
									<p className="text-muted-foreground mb-4">{scene.description}</p>

									{/* Encounters */}
									{scene.encounters && scene.encounters.length > 0 && (
										<Card className="mb-4">
											<CardHeader className="pb-3">
												<CardTitle className="flex items-center gap-2 text-lg">
													<Swords className="h-5 w-5 text-red-500" />
													Encounters
												</CardTitle>
											</CardHeader>
											<CardContent>
												<ul className="space-y-2">
													{scene.encounters.map((encounter, idx) => (
														<li key={idx} className="flex items-start gap-2">
															<ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground" />
															<span>{encounter}</span>
														</li>
													))}
												</ul>
											</CardContent>
										</Card>
									)}

									{/* NPCs */}
									{scene.npcs && scene.npcs.length > 0 && (
										<Card className="mb-4">
											<CardHeader className="pb-3">
												<CardTitle className="flex items-center gap-2 text-lg">
													<Users className="h-5 w-5 text-blue-500" />
													NPCs
												</CardTitle>
											</CardHeader>
											<CardContent>
												<div className="space-y-3">
													{scene.npcs.map((npc, idx) => (
														<div key={idx} className="border-l-2 border-blue-500 pl-3">
															<div className="font-semibold">{npc.name}</div>
															<div className="text-sm text-muted-foreground">
																{npc.race} • {npc.role}
															</div>
															<div className="text-sm italic mt-1">{npc.personality}</div>
														</div>
													))}
												</div>
											</CardContent>
										</Card>
									)}

									{/* Loot */}
									{scene.loot && scene.loot.length > 0 && (
										<Card>
											<CardHeader className="pb-3">
												<CardTitle className="flex items-center gap-2 text-lg">
													<Gem className="h-5 w-5 text-amber-500" />
													Loot & Rewards
												</CardTitle>
											</CardHeader>
											<CardContent>
												<div className="space-y-2">
													{scene.loot.map((item, idx) => (
														<div
															key={idx}
															className="flex items-start justify-between gap-2 p-2 rounded bg-muted/50"
														>
															<div className="flex-1">
																<div className="font-semibold">{item.item}</div>
																<div className="text-sm text-muted-foreground">
																	{item.description}
																</div>
															</div>
															<div className="text-amber-600 font-bold whitespace-nowrap">
																{item.value} gp
															</div>
														</div>
													))}
												</div>
											</CardContent>
										</Card>
									)}
								</AccordionContent>
							</AccordionItem>
						))}
					</Accordion>
				</ScrollArea>
			</div>

			{/* Action Buttons */}
			<div className="flex justify-end gap-3">
				<Button variant="outline" onClick={onCancel} disabled={startingAdventure}>
					Cancel
				</Button>
				<Button onClick={handleStart} disabled={startingAdventure} size="lg">
					<Play className="h-5 w-5 mr-2" />
					{startingAdventure ? "Starting Adventure..." : "Start Adventure"}
				</Button>
			</div>
		</div>
	);
}
