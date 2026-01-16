"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { AlertTriangle, BookOpen, Sparkles, Swords, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { ConcentrationTracker, useConcentration } from "./ConcentrationTracker";
import { RitualCastingDialog } from "./RitualCastingDialog";
import { SpellSlotsDisplay } from "./SpellSlotsDisplay";

interface Spell {
	id: string;
	name: string;
	level: number;
	school: string;
	casting_time: string;
	range: string;
	duration: string;
	description: string;
	is_concentration: boolean;
	is_ritual: boolean;
	ritual: boolean;
	damage_dice: string | null;
	damage_type: string | null;
	upcast_damage_dice?: string | null;
	material_cost?: number | null;
	material_consumed?: boolean;
}

interface CharacterSpell {
	id: string;
	spell_id: string;
	is_known: boolean;
	is_prepared: boolean;
	spell: Spell;
}

interface SpellCastingPanelProps {
	characterId: string;
	characterName?: string;
	characterClass?: string;
	constitutionModifier?: number;
}

export function SpellCastingPanel({
	characterId,
	characterName,
	characterClass,
	constitutionModifier = 0
}: SpellCastingPanelProps) {
	const [spells, setSpells] = useState<CharacterSpell[]>([]);
	const [loading, setLoading] = useState(true);
	const [castDialogOpen, setCastDialogOpen] = useState(false);
	const [ritualDialogOpen, setRitualDialogOpen] = useState(false);
	const [selectedSpell, setSelectedSpell] = useState<CharacterSpell | null>(null);
	const [selectedSlotLevel, setSelectedSlotLevel] = useState<string>("");
	const [casting, setCasting] = useState(false);
	const [castResult, setCastResult] = useState<any>(null);
	const { showToast } = useToast();
	const { concentrating, startConcentration, breakConcentration } = useConcentration();

	useEffect(() => {
		fetchSpells();
	}, [characterId]);

	const fetchSpells = async () => {
		try {
			const response = await fetch(
				`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/spells/character/${characterId}/spells`
			);

			if (response.ok) {
				const data = await response.json();
				setSpells(data);
			}
		} catch (error) {
			console.error("Failed to fetch spells:", error);
		} finally {
			setLoading(false);
		}
	};

	const handleCastClick = (spell: CharacterSpell) => {
		setSelectedSpell(spell);

		// Check if spell requires concentration while already concentrating
		if (spell.spell.is_concentration && concentrating) {
			const breakCurrent = confirm(
				`You are already concentrating on ${concentrating.spellName}. Casting ${spell.spell.name} will break that concentration. Continue?`
			);
			if (!breakCurrent) {
				return;
			}
			breakConcentration();
		}

		// Check for ritual casting option
		if (spell.spell.is_ritual && spell.spell.level > 0) {
			setRitualDialogOpen(true);
			return;
		}

		// For cantrips, cast immediately
		if (spell.spell.level === 0) {
			castSpell(spell, 0, false);
		} else {
			// For leveled spells, open slot selection dialog
			setSelectedSlotLevel(spell.spell.level.toString());
			setCastDialogOpen(true);
		}
	};

	const castSpell = async (spell: CharacterSpell, slotLevel: number, isRitual: boolean = false) => {
		setCasting(true);
		try {
			const endpoint = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/spells/character/${characterId}/cast`;

			const response = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					spell_id: spell.spell_id,
					spell_level: spell.spell.level,
					slot_level: isRitual ? undefined : (slotLevel || spell.spell.level),
					is_ritual_cast: isRitual,
				}),
			});

			if (response.ok) {
				const data = await response.json();
				setCastResult(data);

				// Start concentration tracking if needed
				if (spell.spell.is_concentration && !isRitual) {
					startConcentration({
						spellId: spell.spell_id,
						spellName: spell.spell.name,
						spellLevel: spell.spell.level,
						duration: spell.spell.duration,
						startedAt: new Date(),
					});
				}

				let message = `Cast ${data.spell_name}!`;
				if (isRitual) {
					message += ' (as ritual, +10 minutes)';
				} else if (slotLevel > spell.spell.level) {
					message += ` (upcast at level ${slotLevel})`;
				}
				if (data.total_damage) {
					message += ` Dealt ${data.total_damage} damage! (${data.damage_roll})`;
				}
				showToast(message, 'success');

				setCastDialogOpen(false);
				setRitualDialogOpen(false);

				// Refresh spell slots after a small delay
				setTimeout(() => {
					setCastResult(null);
				}, 5000);
			} else {
				const error = await response.json();
				showToast(error.detail || 'Failed to cast spell', 'error');
			}
		} catch (error) {
			console.error("Failed to cast spell:", error);
			showToast('Failed to cast spell', 'error');
		} finally {
			setCasting(false);
		}
	};

	const handleConfirmCast = () => {
		if (selectedSpell && selectedSlotLevel) {
			castSpell(selectedSpell, parseInt(selectedSlotLevel), false);
		}
	};

	const handleRitualCast = async (spellId: string) => {
		if (selectedSpell) {
			await castSpell(selectedSpell, 0, true);
		}
	};

	const handleNormalCast = async (spellId: string) => {
		if (selectedSpell) {
			setSelectedSlotLevel(selectedSpell.spell.level.toString());
			setCastDialogOpen(true);
			setRitualDialogOpen(false);
		}
	};

	const preparedSpells = spells.filter(cs => cs.is_prepared || cs.spell.level === 0);
	const cantrips = preparedSpells.filter(cs => cs.spell.level === 0);
	const leveledSpells = preparedSpells.filter(cs => cs.spell.level > 0);

	// Group spells by level
	const spellsByLevel = leveledSpells.reduce((acc, cs) => {
		const level = cs.spell.level;
		if (!acc[level]) acc[level] = [];
		acc[level].push(cs);
		return acc;
	}, {} as Record<number, CharacterSpell[]>);

	if (loading) {
		return (
			<Card>
				<CardHeader>
					<CardTitle>Spellcasting</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-muted-foreground">Loading spells...</p>
				</CardContent>
			</Card>
		);
	}

	return (
		<div className="space-y-4">
			{/* Concentration Tracker */}
			{concentrating && (
				<ConcentrationTracker
					characterId={characterId}
					characterName={characterName}
					constitutionModifier={constitutionModifier}
					onConcentrationBroken={breakConcentration}
				/>
			)}

			{/* Spell Slots Display */}
			<SpellSlotsDisplay
				characterId={characterId}
				characterName={characterName}
				onRest={fetchSpells}
			/>

			{/* Cast Result Alert */}
			{castResult && (
				<Alert>
					<Sparkles className="h-4 w-4" />
					<AlertDescription>
						<strong>{castResult.spell_name}</strong> cast successfully!
						{castResult.total_damage && (
							<span className="ml-2">
								Dealt <strong>{castResult.total_damage}</strong> damage ({castResult.damage_roll})
							</span>
						)}
					</AlertDescription>
				</Alert>
			)}

			{/* Spell List */}
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<BookOpen className="h-5 w-5" />
						Spellcasting
						{characterClass && <Badge variant="outline">{characterClass}</Badge>}
					</CardTitle>
				</CardHeader>
				<CardContent>
					<ScrollArea className="h-96">
						<div className="space-y-6">
							{/* Cantrips */}
							{cantrips.length > 0 && (
								<div>
									<h3 className="text-sm font-semibold mb-3">Cantrips</h3>
									<div className="space-y-2">
										{cantrips.map((cs) => (
											<SpellItem
												key={cs.id}
												spell={cs}
												onCast={() => handleCastClick(cs)}
												casting={casting && selectedSpell?.id === cs.id}
											/>
										))}
									</div>
								</div>
							)}

							{/* Leveled Spells */}
							{Object.keys(spellsByLevel)
								.sort((a, b) => parseInt(a) - parseInt(b))
								.map((level) => (
									<div key={level}>
										<h3 className="text-sm font-semibold mb-3">
											{level === "1" ? "1st" : level === "2" ? "2nd" : level === "3" ? "3rd" : `${level}th`} Level
										</h3>
										<div className="space-y-2">
											{spellsByLevel[parseInt(level)].map((cs) => (
												<SpellItem
													key={cs.id}
													spell={cs}
													onCast={() => handleCastClick(cs)}
													casting={casting && selectedSpell?.id === cs.id}
												/>
											))}
										</div>
									</div>
								))}
						</div>
					</ScrollArea>
				</CardContent>
			</Card>

			{/* Cast Dialog */}
			{selectedSpell && (
				<>
					<Dialog open={castDialogOpen} onOpenChange={setCastDialogOpen}>
						<DialogContent>
							<DialogHeader>
								<DialogTitle>Cast {selectedSpell.spell.name}</DialogTitle>
								<DialogDescription>
									Select the spell slot level to use for casting.
								</DialogDescription>
							</DialogHeader>

							<div className="space-y-4">
								<div>
									<label className="text-sm font-medium">Spell Slot Level</label>
									<Select value={selectedSlotLevel} onValueChange={setSelectedSlotLevel}>
										<SelectTrigger>
											<SelectValue placeholder="Select slot level" />
										</SelectTrigger>
										<SelectContent>
											{Array.from({ length: 10 - selectedSpell.spell.level }, (_, i) => i + selectedSpell.spell.level).map((level) => (
												<SelectItem key={level} value={level.toString()}>
													Level {level}
													{level > selectedSpell.spell.level && " (Upcasting)"}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>

								{selectedSlotLevel && parseInt(selectedSlotLevel) > selectedSpell.spell.level && (
									<Alert>
										<AlertTriangle className="h-4 w-4" />
										<AlertDescription>
											You are upcasting this spell from level {selectedSpell.spell.level} to level {selectedSlotLevel}.
											{selectedSpell.spell.damage_dice && " This may increase damage or other effects."}
										</AlertDescription>
									</Alert>
								)}
							</div>

							<DialogFooter>
								<Button
									onClick={handleConfirmCast}
									disabled={!selectedSlotLevel || casting}
								>
									{casting ? "Casting..." : "Cast Spell"}
								</Button>
							</DialogFooter>
						</DialogContent>
					</Dialog>

					{/* Ritual Casting Dialog */}
					<RitualCastingDialog
						spell={selectedSpell.spell}
						open={ritualDialogOpen}
						onOpenChange={setRitualDialogOpen}
						onCastAsRitual={handleRitualCast}
						onCastNormally={handleNormalCast}
					/>
				</>
			)}
		</div>
	);
}

// Spell Item Component
interface SpellItemProps {
	spell: CharacterSpell;
	onCast: () => void;
	casting: boolean;
}

function SpellItem({ spell, onCast, casting }: SpellItemProps) {
	return (
		<div className="flex items-start justify-between p-3 bg-muted rounded-lg">
			<div className="flex-1">
				<div className="flex items-center gap-2 mb-1">
					<span className="font-medium">{spell.spell.name}</span>
					{spell.spell.is_concentration && (
						<Badge variant="outline" className="text-xs">
							<Zap className="h-3 w-3 mr-1" />
							Concentration
						</Badge>
					)}
					{spell.spell.is_ritual && (
						<Badge variant="secondary" className="text-xs">
							<Sparkles className="h-3 w-3 mr-1" />
							Ritual
						</Badge>
					)}
					{spell.spell.upcast_damage_dice && (
						<Badge variant="default" className="text-xs">
							Upcast: {spell.spell.upcast_damage_dice}/level
						</Badge>
					)}
				</div>
				<p className="text-xs text-muted-foreground">
					{spell.spell.casting_time} • {spell.spell.range}
					{spell.spell.damage_dice && ` • ${spell.spell.damage_dice} ${spell.spell.damage_type}`}
				</p>
				{spell.spell.material_cost && spell.spell.material_cost > 0 && (
					<p className="text-xs text-yellow-600 dark:text-yellow-500 mt-1">
						Requires: {spell.spell.material_cost} gp worth of materials
						{spell.spell.material_consumed && " (consumed)"}
					</p>
				)}
			</div>
			<Button
				size="sm"
				onClick={onCast}
				disabled={casting}
			>
				<Swords className="h-4 w-4 mr-1" />
				{casting ? "Casting..." : "Cast"}
			</Button>
		</div>
	);
}
