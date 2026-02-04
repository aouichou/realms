"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
	Gem,
	MapPin,
	Palette,
	Play,
	Sparkles,
	Swords,
	Target,
	Users,
	X
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

			{/* Adventure Overview - No Spoilers */}
			<div className="mb-6">
				<Card>
					<CardHeader>
						<CardTitle className="flex items-center gap-2">
							<Sparkles className="h-5 w-5 text-amber-500" />
							What Awaits You
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<p className="text-muted-foreground">
							Your journey will unfold across <strong>{adventure.scenes.length} major scenes</strong>,
							filled with challenges, mysteries, and rewards.
						</p>
						<div className="grid gap-3 md:grid-cols-2">
							<div className="flex items-start gap-2 p-3 bg-muted rounded-lg">
								<Users className="h-5 w-5 text-primary mt-0.5" />
								<div>
									<div className="font-semibold text-sm">Characters & NPCs</div>
									<div className="text-xs text-muted-foreground">
										Meet allies and adversaries along your path
									</div>
								</div>
							</div>
							<div className="flex items-start gap-2 p-3 bg-muted rounded-lg">
								<Swords className="h-5 w-5 text-red-500 mt-0.5" />
								<div>
									<div className="font-semibold text-sm">Encounters & Challenges</div>
									<div className="text-xs text-muted-foreground">
										Face dangers and test your abilities
									</div>
								</div>
							</div>
							<div className="flex items-start gap-2 p-3 bg-muted rounded-lg">
								<Target className="h-5 w-5 text-accent-400 mt-0.5" />
								<div>
									<div className="font-semibold text-sm">Your Goal</div>
									<div className="text-xs text-muted-foreground">
										{GOAL_NAMES[adventure.goal] || adventure.goal}
									</div>
								</div>
							</div>
							<div className="flex items-start gap-2 p-3 bg-muted rounded-lg">
								<Gem className="h-5 w-5 text-accent-400 mt-0.5" />
								<div>
									<div className="font-semibold text-sm">Treasures</div>
									<div className="text-xs text-muted-foreground">
										Discover valuable loot and artifacts
									</div>
								</div>
							</div>
						</div>
						<div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
							<p className="text-sm text-amber-900 dark:text-amber-100">
								<strong>Note:</strong> The details of your adventure will unfold as you play.
								The AI Dungeon Master will reveal scenes, encounters, and secrets at the right moments!
							</p>
						</div>
					</CardContent>
				</Card>
			</div>

			{/* Action Buttons */}
			<div className="flex justify-end gap-3">
				<Button variant="outline" onClick={onCancel} disabled={startingAdventure}>
					Cancel
				</Button>
				<Button
					onClick={handleStart}
					disabled={startingAdventure}
					size="lg"
					className="border-2 border-accent-600 shadow-lg hover:border-accent-400 transition-colors"
				>
					<Play className="h-5 w-5 mr-2" />
					{startingAdventure ? "Starting Adventure..." : "Start Adventure"}
				</Button>
			</div>
		</div>
	);
}
