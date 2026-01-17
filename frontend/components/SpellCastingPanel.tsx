"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { useTranslation } from "@/lib/hooks/useTranslation";
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
	const { t } = useTranslation();
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
				t('game.spellCasting.concentrationWarning')
					.replace('{spell}', concentrating.spellName)
					.replace('{newSpell}', spell.spell.name)
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

				let message = `${data.spell_name} ${t('game.spellCasting.castSuccess')}`;
				if (isRitual) {
					message += ' ' + t('game.spellCasting.asRitual');
				} else if (slotLevel > spell.spell.level) {
					message += ' ' + t('game.spellCasting.upcastAt').replace('{level}', slotLevel.toString());
				}
				if (data.total_damage) {
					message += ` ${t('game.spellCasting.dealt')} ${data.total_damage} ${t('game.spellCasting.damage')}! (${data.damage_roll})`;
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
				showToast(error.detail || t('game.spellCasting.failedToCast'), 'error');
			}
		} catch (error) {
			console.error("Failed to cast spell:", error);
			showToast(t('game.spellCasting.failedToCast'), 'error');
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
					<CardTitle>{t('game.spellCasting.title')}</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-muted-foreground">{t('game.spellCasting.loadingSpells')}</p>
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
						<strong>{castResult.spell_name}</strong> {t('game.spellCasting.castSuccess')}
						{castResult.total_damage && (
							<span className="ml-2">
								{t('game.spellCasting.dealt')} <strong>{castResult.total_damage}</strong> {t('game.spellCasting.damage')} ({castResult.damage_roll})
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
						{t('game.spellCasting.title')}
						{characterClass && <Badge variant="outline">{characterClass}</Badge>}
					</CardTitle>
				</CardHeader>
				<CardContent>
					<ScrollArea className="h-96">
						<div className="space-y-6">
							{/* Cantrips */}
							{cantrips.length > 0 && (
								<div>
									<h3 className="text-sm font-semibold mb-3">{t('game.spellCasting.cantrips')}</h3>
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
											{level === "1" ? t('game.spellCasting.level1st') :
												level === "2" ? t('game.spellCasting.level2nd') :
													level === "3" ? t('game.spellCasting.level3rd') :
														t('game.spellCasting.levelNth').replace('{level}', level)}
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
								<DialogTitle>{t('game.spellCasting.cast')} {selectedSpell.spell.name}</DialogTitle>
								<DialogDescription>
									{t('game.spellCasting.selectSlotLevel')}
								</DialogDescription>
							</DialogHeader>

							<div className="space-y-4">
								<div>
									<label className="text-sm font-medium">{t('game.spellCasting.spellSlotLevel')}</label>
									<Select value={selectedSlotLevel} onValueChange={setSelectedSlotLevel}>
										<SelectTrigger>
											<SelectValue placeholder={t('game.spellCasting.selectSlot')} />
										</SelectTrigger>
										<SelectContent>
											{Array.from({ length: 10 - selectedSpell.spell.level }, (_, i) => i + selectedSpell.spell.level).map((level) => (
												<SelectItem key={level} value={level.toString()}>
													{t('game.spellCasting.level')} {level}
													{level > selectedSpell.spell.level && ` (${t('game.spellCasting.upcasting')})`}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>

								{selectedSlotLevel && parseInt(selectedSlotLevel) > selectedSpell.spell.level && (
									<Alert>
										<AlertTriangle className="h-4 w-4" />
										<AlertDescription>
											{t('game.spellCasting.upcastingAlert')
												.replace('{from}', selectedSpell.spell.level.toString())
												.replace('{to}', selectedSlotLevel)}
											{selectedSpell.spell.damage_dice && " " + t('game.spellCasting.upcastingAlertExtra')}
										</AlertDescription>
									</Alert>
								)}
							</div>

							<DialogFooter>
								<Button
									onClick={handleConfirmCast}
									disabled={!selectedSlotLevel || casting}
								>
									{casting ? t('game.spellCasting.casting') : t('game.spellCasting.castSpell')}
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
	const { t } = useTranslation();
	return (
		<div className="flex items-start justify-between p-3 bg-muted rounded-lg">
			<div className="flex-1">
				<div className="flex items-center gap-2 mb-1">
					<span className="font-medium">{spell.spell.name}</span>
					{spell.spell.is_concentration && (
						<Badge variant="outline" className="text-xs">
							<Zap className="h-3 w-3 mr-1" />
							{t('game.spellCasting.concentration')}
						</Badge>
					)}
					{spell.spell.is_ritual && (
						<Badge variant="secondary" className="text-xs">
							<Sparkles className="h-3 w-3 mr-1" />
							{t('game.spellCasting.ritual')}
						</Badge>
					)}
					{spell.spell.upcast_damage_dice && (
						<Badge variant="default" className="text-xs">
							{t('game.spellCasting.upcast')}: {spell.spell.upcast_damage_dice}{t('game.spellCasting.perLevel')}
						</Badge>
					)}
				</div>
				<p className="text-xs text-muted-foreground">
					{spell.spell.casting_time} • {spell.spell.range}
					{spell.spell.damage_dice && ` • ${spell.spell.damage_dice} ${spell.spell.damage_type}`}
				</p>
				{spell.spell.material_cost && spell.spell.material_cost > 0 && (
					<p className="text-xs text-yellow-600 dark:text-yellow-500 mt-1">
						{t('game.spellCasting.requires')}: {spell.spell.material_cost} {t('game.spellCasting.gpWorthOfMaterials')}
						{spell.spell.material_consumed && " " + t('game.spellCasting.consumed')}
					</p>
				)}
			</div>
			<Button
				size="sm"
				onClick={onCast}
				disabled={casting}
			>
				<Swords className="h-4 w-4 mr-1" />
				{casting ? t('game.spellCasting.casting') : t('game.spellCasting.cast')}
			</Button>
		</div>
	);
}
