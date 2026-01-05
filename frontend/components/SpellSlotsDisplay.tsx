"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { Circle, CircleDot, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

interface SpellSlots {
	[level: string]: {
		total: number;
		used: number;
	};
}

interface SpellSlotsDisplayProps {
	characterId: string;
	characterName?: string;
	onRest?: () => void;
}

export function SpellSlotsDisplay({ characterId, characterName, onRest }: SpellSlotsDisplayProps) {
	const [spellSlots, setSpellSlots] = useState<SpellSlots>({});
	const [loading, setLoading] = useState(true);
	const [resting, setResting] = useState(false);
	const { showToast } = useToast();

	useEffect(() => {
		fetchSpellSlots();
	}, [characterId]);

	const fetchSpellSlots = async () => {
		try {
			const response = await fetch(
				`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/spells/character/${characterId}/slots`
			);

			if (response.ok) {
				const data = await response.json();
				setSpellSlots(data.spell_slots || {});
			}
		} catch (error) {
			console.error("Failed to fetch spell slots:", error);
		} finally {
			setLoading(false);
		}
	};

	const handleRest = async () => {
		setResting(true);
		try {
			const response = await fetch(
				`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/spells/character/${characterId}/rest`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
				}
			);

			if (response.ok) {
				const data = await response.json();
				setSpellSlots(data.spell_slots || {});
				showToast(`${characterName || 'Character'} has completed a long rest. All spell slots restored!`, 'success');
				onRest?.();
			} else {
				showToast('Failed to complete rest', 'error');
			}
		} catch (error) {
			console.error("Failed to rest:", error);
			showToast('Failed to complete rest', 'error');
		} finally {
			setResting(false);
		}
	};

	const getLevelLabel = (level: string): string => {
		const num = parseInt(level);
		const suffix = num === 1 ? 'st' : num === 2 ? 'nd' : num === 3 ? 'rd' : 'th';
		return `${num}${suffix} Level`;
	};

	const hasSpellSlots = Object.keys(spellSlots).length > 0;
	const hasUsedSlots = Object.values(spellSlots).some(slot => slot.used > 0);

	if (loading) {
		return (
			<Card>
				<CardHeader>
					<CardTitle>Spell Slots</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-muted-foreground">Loading...</p>
				</CardContent>
			</Card>
		);
	}

	if (!hasSpellSlots) {
		return null; // Character doesn't have spell slots
	}

	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
				<CardTitle>Spell Slots</CardTitle>
				{hasUsedSlots && (
					<Button
						variant="outline"
						size="sm"
						onClick={handleRest}
						disabled={resting}
						className="h-8"
					>
						<RefreshCw className={`h-4 w-4 mr-1 ${resting ? 'animate-spin' : ''}`} />
						Long Rest
					</Button>
				)}
			</CardHeader>
			<CardContent>
				<div className="space-y-4">
					{Object.entries(spellSlots)
						.sort(([a], [b]) => parseInt(a) - parseInt(b))
						.map(([level, slots]) => {
							const available = slots.total - slots.used;
							const percentUsed = (slots.used / slots.total) * 100;

							return (
								<div key={level} className="space-y-2">
									<div className="flex items-center justify-between">
										<div className="flex items-center gap-2">
											<Badge variant="outline" className="font-mono">
												{getLevelLabel(level)}
											</Badge>
											<span className="text-sm text-muted-foreground">
												{available} / {slots.total} available
											</span>
										</div>
									</div>

									{/* Visual slot indicators */}
									<div className="flex gap-1">
										{Array.from({ length: slots.total }, (_, i) => {
											const isUsed = i < slots.used;
											return (
												<div
													key={i}
													className={`transition-colors ${isUsed ? 'text-muted-foreground' : 'text-primary'
														}`}
													title={isUsed ? 'Used' : 'Available'}
												>
													{isUsed ? (
														<Circle className="h-4 w-4" />
													) : (
														<CircleDot className="h-4 w-4" />
													)}
												</div>
											);
										})}
									</div>

									{/* Progress bar */}
									<div className="h-1 bg-muted rounded-full overflow-hidden">
										<div
											className="h-full bg-primary transition-all duration-300"
											style={{ width: `${100 - percentUsed}%` }}
										/>
									</div>
								</div>
							);
						})}
				</div>
			</CardContent>
		</Card>
	);
}
