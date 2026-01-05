"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Info } from "lucide-react";
import { useState } from "react";
import { Spell, SpellBrowser } from "./spells/SpellBrowser";

interface SpellSelectionStepProps {
	characterClass: string;
	level: number;
	abilityScores: {
		intelligence: number;
		wisdom: number;
		charisma: number;
	};
	selectedSpells: Set<string>;
	onSpellsChange: (spells: Set<string>) => void;
}

// D&D 5e spell rules by class
const SPELL_CASTING_CLASSES = {
	wizard: {
		type: "prepared",
		spellcastingAbility: "intelligence",
		cantripsKnown: { 1: 3, 4: 4, 10: 5 },
		spellsKnown: "prepared", // INT mod + level
		spellsInSpellbook: 6, // at level 1
	},
	sorcerer: {
		type: "known",
		spellcastingAbility: "charisma",
		cantripsKnown: { 1: 4, 4: 5, 10: 6 },
		spellsKnown: { 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10, 10: 11, 11: 12, 13: 13, 14: 14, 15: 15 },
	},
	cleric: {
		type: "prepared",
		spellcastingAbility: "wisdom",
		cantripsKnown: { 1: 3, 4: 4, 10: 5 },
		spellsKnown: "prepared", // WIS mod + level
	},
	druid: {
		type: "prepared",
		spellcastingAbility: "wisdom",
		cantripsKnown: { 1: 2, 4: 3, 10: 4 },
		spellsKnown: "prepared", // WIS mod + level
	},
	bard: {
		type: "known",
		spellcastingAbility: "charisma",
		cantripsKnown: { 1: 2, 4: 3, 10: 4 },
		spellsKnown: { 1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10, 8: 11, 9: 12, 10: 14, 11: 15, 13: 16, 14: 18, 15: 19, 17: 20 },
	},
	warlock: {
		type: "known",
		spellcastingAbility: "charisma",
		cantripsKnown: { 1: 2, 4: 3, 10: 4 },
		spellsKnown: { 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10, 11: 11, 13: 12, 15: 13, 17: 14, 19: 15 },
	},
	paladin: {
		type: "prepared",
		spellcastingAbility: "charisma",
		cantripsKnown: { 1: 0 }, // No cantrips
		spellsKnown: "prepared", // CHA mod + half level
		minLevel: 2, // Gets spells at level 2
	},
	ranger: {
		type: "known",
		spellcastingAbility: "wisdom",
		cantripsKnown: { 1: 0 }, // No cantrips
		spellsKnown: { 2: 2, 3: 3, 5: 4, 7: 5, 9: 6, 11: 7, 13: 8, 15: 9, 17: 10, 19: 11 },
		minLevel: 2, // Gets spells at level 2
	},
};

function calculateModifier(score: number): number {
	return Math.floor((score - 10) / 2);
}

function getCantripsKnown(classData: any, level: number): number {
	const cantrips = classData.cantripsKnown;
	let count = 0;
	for (const [lvl, num] of Object.entries(cantrips)) {
		if (level >= parseInt(lvl)) {
			count = num as number;
		}
	}
	return count;
}

function getSpellsKnown(classData: any, level: number, abilityMod: number): number {
	if (classData.spellsKnown === "prepared") {
		// Prepared casters: ability mod + level (min 1)
		if (classData.spellcastingAbility === "charisma") {
			// Paladin uses half level
			return Math.max(1, abilityMod + Math.floor(level / 2));
		}
		return Math.max(1, abilityMod + level);
	}

	// Known casters: look up by level
	const known = classData.spellsKnown;
	let count = 0;
	for (const [lvl, num] of Object.entries(known)) {
		if (level >= parseInt(lvl)) {
			count = num as number;
		}
	}
	return count;
}

export function SpellSelectionStep({
	characterClass,
	level,
	abilityScores,
	selectedSpells,
	onSpellsChange,
}: SpellSelectionStepProps) {
	const [spellLevels, setSpellLevels] = useState<Map<string, number>>(new Map());

	const classData = SPELL_CASTING_CLASSES[characterClass as keyof typeof SPELL_CASTING_CLASSES];

	// Check if this class can cast spells at this level
	if (!classData || ('minLevel' in classData && classData.minLevel && level < classData.minLevel)) {
		return null; // Non-spellcaster or too low level
	}

	const abilityMod = calculateModifier(
		abilityScores[classData.spellcastingAbility as keyof typeof abilityScores]
	);

	const maxCantrips = getCantripsKnown(classData, level);
	const maxSpells = getSpellsKnown(classData, level, abilityMod);

	const handleSpellSelect = (spell: Spell) => {
		const newSelected = new Set(selectedSpells);
		const newLevels = new Map(spellLevels);

		if (newSelected.has(spell.id)) {
			// Deselect
			newSelected.delete(spell.id);
			newLevels.delete(spell.id);
		} else {
			// Check if we can select this spell
			const isCantrip = spell.level === 0;

			// Count current selections
			const currentCantrips = Array.from(newSelected).filter(id =>
				newLevels.get(id) === 0
			).length;
			const currentSpells = Array.from(newSelected).filter(id =>
				newLevels.get(id) !== undefined && newLevels.get(id)! > 0
			).length;

			// Check limits
			if (isCantrip) {
				if (currentCantrips >= maxCantrips) {
					return; // Max cantrips reached
				}
			} else {
				if (currentSpells >= maxSpells) {
					return; // Max spells reached
				}
			}

			// Add selection
			newSelected.add(spell.id);
			newLevels.set(spell.id, spell.level);
		}

		setSpellLevels(newLevels);
		onSpellsChange(newSelected);
	};

	// Calculate current counts
	const cantripCount = Array.from(selectedSpells).filter(id =>
		spellLevels.get(id) === 0
	).length;
	const spellCount = Array.from(selectedSpells).filter(id =>
		spellLevels.get(id) !== undefined && spellLevels.get(id)! > 0
	).length;

	return (
		<Card className="mt-6">
			<CardHeader>
				<CardTitle>Spell Selection</CardTitle>
				<CardDescription>
					{classData.type === "prepared"
 						? `Choose your starting spellbook. You can prepare ${maxSpells} spells per day from your spellbook.`
						: `Choose ${maxSpells} spells your ${characterClass} knows. These spells are always available to cast.`
					}
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-4">
				{/* Spell Limits */}
				<div className="flex gap-4">
					<Badge variant="outline" className="text-sm">
						Cantrips: {cantripCount} / {maxCantrips}
					</Badge>
					<Badge variant="outline" className="text-sm">
						{classData.type === "prepared" ? "Spellbook" : "Known"} Spells: {spellCount} / {maxSpells}
					</Badge>
				</div>

				{/* Class Info */}
				<Alert>
					<Info className="h-4 w-4" />
					<AlertDescription>
						<strong>{characterClass.charAt(0).toUpperCase() + characterClass.slice(1)}</strong>
						{" "}uses <strong>{classData.spellcastingAbility.charAt(0).toUpperCase() + classData.spellcastingAbility.slice(1)}</strong> for spellcasting
						(modifier: {abilityMod >= 0 ? '+' : ''}{abilityMod}).
						{'spellsInSpellbook' in classData && classData.spellsInSpellbook && ` You start with ${classData.spellsInSpellbook} spells in your spellbook.`}
					</AlertDescription>
				</Alert>

				{/* Spell Browser */}
				<div className="h-150">
					<SpellBrowser
						filterByClass={characterClass}
						selectedSpells={selectedSpells}
						onSpellSelect={handleSpellSelect}
					/>
				</div>
			</CardContent>
		</Card>
	);
}
