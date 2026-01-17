"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { apiClient } from "@/lib/api-client";
import {
	BookOpen,
	Brain,
	Coins,
	Eye,
	Heart,
	MessageCircle,
	Shield,
	Sparkles,
	Swords,
	Zap,
} from "lucide-react";
import { useEffect, useState } from "react";

interface AbilityScore {
	score: number;
	modifier: number;
}

interface CharacterStats {
	// Ability scores
	strength: number;
	dexterity: number;
	constitution: number;
	intelligence: number;
	wisdom: number;
	charisma: number;

	// Modifiers
	strength_modifier: number;
	dexterity_modifier: number;
	constitution_modifier: number;
	intelligence_modifier: number;
	wisdom_modifier: number;
	charisma_modifier: number;

	// Combat stats
	armor_class: number;
	base_armor_class: number;
	proficiency_bonus: number;
	initiative_bonus: number;
	melee_attack_bonus: number;
	ranged_attack_bonus: number;
	spell_save_dc: number;

	// HP
	hp_current: number;
	hp_max: number;

	// Skills and saves
	skills: Record<string, number | { modifier: number; proficient: boolean }>;
	saving_throws: Record<string, number>;

	// Equipment bonuses
	equipped_items: Array<{
		item_name: string;
		ac_bonus: number;
		attack_bonus: number;
	}>;
}

interface SpellSlots {
	[level: string]: {
		total: number;
		used: number;
	};
}

interface EnhancedCharacterSheetProps {
	characterId: string;
	characterName: string;
	characterClass: string;
	level: number;
}

export function EnhancedCharacterSheet({
	characterId,
	characterName,
	characterClass,
	level,
}: EnhancedCharacterSheetProps) {
	const [stats, setStats] = useState<CharacterStats | null>(null);
	const [spellSlots, setSpellSlots] = useState<SpellSlots>({});
	const [gold, setGold] = useState<number>(0);
	const [silver, setSilver] = useState<number>(0);
	const [copper, setCopper] = useState<number>(0);
	const [backgroundName, setBackgroundName] = useState<string>('');
	const [backgroundDescription, setBackgroundDescription] = useState<string>('');
	const [personalityTrait, setPersonalityTrait] = useState<string>('');
	const [ideal, setIdeal] = useState<string>('');
	const [bond, setBond] = useState<string>('');
	const [flaw, setFlaw] = useState<string>('');
	const [skillProficiencies, setSkillProficiencies] = useState<string[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		fetchCharacterData();
	}, [characterId]);

	const fetchCharacterData = async () => {
		try {
			// Fetch character info for background
			const charResponse = await apiClient.get(`/api/v1/characters/${characterId}`);
			if (charResponse.ok) {
				const charData = await charResponse.json();
				setBackgroundName(charData.background_name || '');
				setBackgroundDescription(charData.background_description || '');
				setPersonalityTrait(charData.personality_trait || '');
				setIdeal(charData.ideal || '');
				setBond(charData.bond || '');
				setFlaw(charData.flaw || '');
				setSkillProficiencies(charData.skill_proficiencies || []);
				// Set currency
				setGold(charData.gold || 0);
				setSilver(charData.silver || 0);
				setCopper(charData.copper || 0);
			} else {
				console.warn('Failed to fetch character data:', charResponse.status);
			}

			// Fetch stats
			const statsResponse = await apiClient.get(`/api/v1/characters/${characterId}/stats`);
			const statsData = await statsResponse.json();
			setStats(statsData);

			// Fetch spell slots
			const slotsResponse = await apiClient.get(`/api/v1/spells/character/${characterId}/slots`);
			const slotsData = await slotsResponse.json();
			setSpellSlots(slotsData.spell_slots || {});
		} catch (error) {
			console.error("Failed to fetch character data:", error);
		} finally {
			setLoading(false);
		}
	};

	const formatModifier = (modifier: number) => {
		return modifier >= 0 ? `+${modifier}` : `${modifier}`;
	};

	const hpPercentage = stats ? (stats.hp_current / stats.hp_max) * 100 : 0;
	const hpColor = hpPercentage > 50 ? "bg-green-500" : hpPercentage > 25 ? "bg-yellow-500" : "bg-red-500";

	if (loading) {
		return (
			<Card>
				<CardHeader>
					<CardTitle>Character Sheet</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="flex items-center justify-center h-64">
						<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
					</div>
				</CardContent>
			</Card>
		);
	}

	if (!stats) return null;

	const abilities = [
		{ name: "Strength", short: "STR", score: stats.strength, modifier: stats.strength_modifier, icon: Swords },
		{ name: "Dexterity", short: "DEX", score: stats.dexterity, modifier: stats.dexterity_modifier, icon: Zap },
		{ name: "Constitution", short: "CON", score: stats.constitution, modifier: stats.constitution_modifier, icon: Heart },
		{ name: "Intelligence", short: "INT", score: stats.intelligence, modifier: stats.intelligence_modifier, icon: Brain },
		{ name: "Wisdom", short: "WIS", score: stats.wisdom, modifier: stats.wisdom_modifier, icon: Eye },
		{ name: "Charisma", short: "CHA", score: stats.charisma, modifier: stats.charisma_modifier, icon: MessageCircle },
	];

	return (
		<div className="space-y-4">
			{/* Header Card */}
			<Card>
				<CardHeader>
					<div className="flex items-center justify-between">
						<div>
							<CardTitle className="text-2xl">{characterName}</CardTitle>
							<p className="text-muted-foreground">
								Level {level} {characterClass}
							</p>
						</div>
						<Badge variant="outline" className="text-lg px-4 py-2">
							Prof. Bonus: +{stats.proficiency_bonus}
						</Badge>
					</div>
				</CardHeader>
			</Card>

			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				{/* Ability Scores */}
				<Card className="md:col-span-1">
					<CardHeader>
						<CardTitle className="text-lg">Ability Scores</CardTitle>
					</CardHeader>
					<CardContent className="space-y-3">
						{abilities.map(({ name, short, score, modifier, icon: Icon }) => (
							<div key={short} className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<Icon className="w-4 h-4 text-muted-foreground" />
									<span className="font-medium">{short}</span>
								</div>
								<div className="flex items-center gap-3">
									<span className="text-2xl font-bold">{score}</span>
									<Badge variant="secondary" className="min-w-15 justify-center">
										{formatModifier(modifier)}
									</Badge>
								</div>
							</div>
						))}
					</CardContent>
				</Card>

				{/* Combat Stats */}
				<Card className="md:col-span-2">
					<CardHeader>
						<CardTitle className="text-lg">Combat Stats</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						{/* HP */}
						<div>
							<div className="flex items-center justify-between mb-2">
								<div className="flex items-center gap-2">
									<Heart className="w-4 h-4 text-red-500" />
									<span className="font-medium">Hit Points</span>
								</div>
								<span className="text-lg font-bold">
									{stats.hp_current} / {stats.hp_max}
								</span>
							</div>
							<Progress value={hpPercentage} className={hpColor} />
						</div>

						<Separator />

						{/* Combat Grid */}
						<div className="grid grid-cols-3 gap-4">
							<div className="text-center">
								<div className="flex items-center justify-center gap-1 mb-1">
									<Shield className="w-4 h-4 text-blue-500" />
									<p className="text-sm text-muted-foreground">AC</p>
								</div>
								<p className="text-2xl font-bold">{stats.armor_class}</p>
								{stats.equipped_items.length > 0 && (
									<p className="text-xs text-muted-foreground">
										(Base: {stats.base_armor_class})
									</p>
								)}
							</div>
							<div className="text-center">
								<div className="flex items-center justify-center gap-1 mb-1">
									<Zap className="w-4 h-4 text-yellow-500" />
									<p className="text-sm text-muted-foreground">Initiative</p>
								</div>
								<p className="text-2xl font-bold">{formatModifier(stats.initiative_bonus)}</p>
							</div>
							<div className="text-center">
								<div className="flex items-center justify-center gap-1 mb-1">
									<Sparkles className="w-4 h-4 text-purple-500" />
									<p className="text-sm text-muted-foreground">Spell DC</p>
								</div>
								<p className="text-2xl font-bold">{stats.spell_save_dc}</p>
							</div>
						</div>

						<div className="grid grid-cols-2 gap-4">
							<div className="text-center">
								<p className="text-sm text-muted-foreground mb-1">Melee Attack</p>
								<p className="text-xl font-bold">{formatModifier(stats.melee_attack_bonus)}</p>
							</div>
							<div className="text-center">
								<p className="text-sm text-muted-foreground mb-1">Ranged Attack</p>
								<p className="text-xl font-bold">{formatModifier(stats.ranged_attack_bonus)}</p>
							</div>
						</div>

						{/* Equipped Items */}
						{stats.equipped_items.length > 0 && (
							<div>
								<p className="text-sm font-medium mb-2">Equipped Items</p>
								<div className="space-y-1">
									{stats.equipped_items.map((item, index) => (
										<div key={index} className="text-sm flex justify-between">
											<span>{item.item_name}</span>
											<span className="text-muted-foreground">
												{item.ac_bonus > 0 && `+${item.ac_bonus} AC`}
												{item.attack_bonus > 0 && ` +${item.attack_bonus} ATK`}
											</span>
										</div>
									))}
								</div>
							</div>
						)}
					</CardContent>
				</Card>
			</div>

			{/* Wealth Card */}
			<Card>
				<CardHeader>
					<CardTitle className="text-lg flex items-center gap-2">
						<Coins className="w-5 h-5 text-yellow-500" />
						Wealth
					</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="grid grid-cols-3 gap-6">
						<div className="flex flex-col items-center">
							<div className="text-sm text-muted-foreground mb-1">Gold</div>
							<div className="text-3xl font-bold text-yellow-500">{gold}</div>
							<div className="text-xs text-muted-foreground mt-1">GP</div>
						</div>
						<div className="flex flex-col items-center">
							<div className="text-sm text-muted-foreground mb-1">Silver</div>
							<div className="text-3xl font-bold text-gray-400">{silver}</div>
							<div className="text-xs text-muted-foreground mt-1">SP</div>
						</div>
						<div className="flex flex-col items-center">
							<div className="text-sm text-muted-foreground mb-1">Copper</div>
							<div className="text-3xl font-bold text-amber-600">{copper}</div>
							<div className="text-xs text-muted-foreground mt-1">CP</div>
						</div>
					</div>
					<div className="mt-4 pt-4 border-t border-border text-center text-sm text-muted-foreground">
						1 GP = 10 SP = 100 CP
					</div>
				</CardContent>
			</Card>

			{/* Spell Slots */}
			{Object.keys(spellSlots).length > 0 && (
				<Card>
					<CardHeader>
						<CardTitle className="text-lg flex items-center gap-2">
							<Sparkles className="w-5 h-5" />
							Spell Slots
						</CardTitle>
					</CardHeader>
					<CardContent>
						<div className="grid grid-cols-5 gap-4">
							{Object.entries(spellSlots)
								.sort(([a], [b]) => parseInt(a) - parseInt(b))
								.map(([level, slots]) => (
									<div key={level} className="text-center">
										<p className="text-sm text-muted-foreground mb-2">Level {level}</p>
										<div className="flex gap-1 justify-center flex-wrap">
											{Array.from({ length: slots.total }).map((_, i) => (
												<div
													key={i}
													className={`w-3 h-3 rounded-full border-2 ${i < slots.used
														? "bg-gray-300 border-gray-400"
														: "bg-purple-500 border-purple-600"
														}`}
												/>
											))}
										</div>
										<p className="text-xs text-muted-foreground mt-1">
											{slots.total - slots.used} / {slots.total}
										</p>
									</div>
								))}
						</div>
					</CardContent>
				</Card>
			)}

			{/* Background */}
			{backgroundName && (
				<Card>
					<CardHeader>
						<CardTitle className="text-lg flex items-center gap-2">
							<BookOpen className="w-5 h-5" />
							Background: {backgroundName}
						</CardTitle>
					</CardHeader>
					<CardContent>
						<p className="text-sm text-muted-foreground whitespace-pre-wrap">
							{backgroundDescription}
						</p>
					</CardContent>
				</Card>
			)}

			{/* Personality */}
			{(personalityTrait || ideal || bond || flaw) && (
				<Card>
					<CardHeader>
						<CardTitle className="text-lg flex items-center gap-2">
							<Sparkles className="w-5 h-5" />
							Personality
						</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						{personalityTrait && (
							<div>
								<h4 className="text-sm font-semibold mb-1">Personality Trait</h4>
								<p className="text-sm text-muted-foreground line-clamp-3">{personalityTrait}</p>
							</div>
						)}
						{ideal && (
							<div>
								<h4 className="text-sm font-semibold mb-1">Ideal</h4>
								<p className="text-sm text-muted-foreground line-clamp-3">{ideal}</p>
							</div>
						)}
						{bond && (
							<div>
								<h4 className="text-sm font-semibold mb-1">Bond</h4>
								<p className="text-sm text-muted-foreground line-clamp-3">{bond}</p>
							</div>
						)}
						{flaw && (
							<div>
								<h4 className="text-sm font-semibold mb-1">Flaw</h4>
								<p className="text-sm text-muted-foreground line-clamp-3">{flaw}</p>
							</div>
						)}
					</CardContent>
				</Card>
			)}

			{/* Skills */}
			<Card>
				<CardHeader>
					<CardTitle className="text-lg">Skills</CardTitle>
				</CardHeader>
				<CardContent>
					<ScrollArea className="h-50">
						<div className="grid grid-cols-2 gap-3">
							{Object.entries(stats.skills).map(([skill, skillData]) => {
								// Handle both old (number) and new ({modifier, proficient}) formats
								const modifier = typeof skillData === 'number' ? skillData : skillData.modifier;
								const proficient = typeof skillData === 'object' && skillData.proficient;

								return (
									<div key={skill} className="flex justify-between items-center">
										<div className="flex items-center gap-2">
											<span className="text-sm">{skill}</span>
											{proficient && (
												<Badge variant="default" className="text-xs px-1.5 py-0.5 bg-blue-600 text-white">
													PROF
												</Badge>
											)}
										</div>
										<Badge variant="outline">{formatModifier(modifier)}</Badge>
									</div>
								);
							})}
						</div>
					</ScrollArea>
				</CardContent>
			</Card>

			{/* Saving Throws */}
			<Card>
				<CardHeader>
					<CardTitle className="text-lg">Saving Throws</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="grid grid-cols-3 gap-4">
						{Object.entries(stats.saving_throws).map(([ability, modifier]) => (
							<div key={ability} className="text-center">
								<p className="text-sm text-muted-foreground mb-1">{ability}</p>
								<Badge variant="secondary" className="text-lg">
									{formatModifier(modifier)}
								</Badge>
							</div>
						))}
					</div>
				</CardContent>
			</Card>
		</div>
	);
}
