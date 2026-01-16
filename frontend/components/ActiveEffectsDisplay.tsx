"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Clock, Sparkles, Zap } from "lucide-react";
import { useEffect, useState } from "react";

interface ActiveEffect {
	id: string;
	name: string;
	effect_type: string;
	description: string;
	duration_type: string;
	duration_value?: number;
	rounds_remaining?: number;
	expires_at?: string;
	requires_concentration: boolean;
	bonus_value?: number;
	dice_bonus?: string;
	advantage: boolean;
	disadvantage: boolean;
}

interface ActiveEffectsDisplayProps {
	characterId: string;
	sessionId: string;
}

export function ActiveEffectsDisplay({ characterId, sessionId }: ActiveEffectsDisplayProps) {
	const [effects, setEffects] = useState<ActiveEffect[]>([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		fetchEffects();
		// Poll for updates every 10 seconds
		const interval = setInterval(fetchEffects, 10000);
		return () => clearInterval(interval);
	}, [characterId, sessionId]);

	const fetchEffects = async () => {
		try {
			const response = await fetch(
				`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/effects/character/${characterId}?session_id=${sessionId}`
			);

			if (response.ok) {
				const data = await response.json();
				setEffects(data.effects || []);
			}
		} catch (error) {
			console.error("Failed to fetch active effects:", error);
		} finally {
			setLoading(false);
		}
	};

	const getEffectIcon = (effectType: string) => {
		switch (effectType) {
			case 'buff':
				return <Sparkles className="h-4 w-4 text-green-500" />;
			case 'debuff':
				return <AlertCircle className="h-4 w-4 text-red-500" />;
			case 'condition':
				return <AlertCircle className="h-4 w-4 text-orange-500" />;
			case 'concentration':
				return <Zap className="h-4 w-4 text-blue-500" />;
			default:
				return <Sparkles className="h-4 w-4 text-purple-500" />;
		}
	};

	const getEffectBadgeColor = (effectType: string) => {
		switch (effectType) {
			case 'buff':
				return 'bg-green-500/10 text-green-500 border-green-500/20';
			case 'debuff':
				return 'bg-red-500/10 text-red-500 border-red-500/20';
			case 'condition':
				return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
			case 'concentration':
				return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
			default:
				return 'bg-purple-500/10 text-purple-500 border-purple-500/20';
		}
	};

	const getDurationText = (effect: ActiveEffect): string => {
		if (effect.duration_type === 'permanent') return 'Permanent';
		if (effect.duration_type === 'until_long_rest') return 'Until Long Rest';
		if (effect.duration_type === 'until_short_rest') return 'Until Short Rest';
		if (effect.duration_type === 'concentration') return 'Concentration';

		if (effect.rounds_remaining !== undefined && effect.rounds_remaining !== null) {
			const rounds = effect.rounds_remaining;
			return rounds === 1 ? '1 round' : `${rounds} rounds`;
		}

		if (effect.expires_at) {
			const now = new Date();
			const expiresAt = new Date(effect.expires_at);
			const diffMs = expiresAt.getTime() - now.getTime();
			const diffMins = Math.ceil(diffMs / 60000);

			if (diffMins < 1) return 'Expiring soon';
			if (diffMins === 1) return '1 minute';
			if (diffMins < 60) return `${diffMins} minutes`;

			const diffHours = Math.ceil(diffMins / 60);
			return diffHours === 1 ? '1 hour' : `${diffHours} hours`;
		}

		return 'Active';
	};

	const getEffectBonus = (effect: ActiveEffect): string | null => {
		if (effect.bonus_value) {
			return effect.bonus_value > 0 ? `+${effect.bonus_value}` : `${effect.bonus_value}`;
		}
		if (effect.dice_bonus) {
			return effect.dice_bonus;
		}
		if (effect.advantage) {
			return 'Advantage';
		}
		if (effect.disadvantage) {
			return 'Disadvantage';
		}
		return null;
	};

	if (loading) {
		return (
			<Card>
				<CardHeader>
					<CardTitle>Active Effects</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-muted-foreground">Loading...</p>
				</CardContent>
			</Card>
		);
	}

	if (effects.length === 0) {
		return (
			<Card>
				<CardHeader>
					<CardTitle>Active Effects</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="text-sm text-muted-foreground">No active effects</p>
				</CardContent>
			</Card>
		);
	}

	return (
		<Card>
			<CardHeader>
				<CardTitle className="flex items-center gap-2">
					Active Effects
					<Badge variant="secondary" className="ml-auto">
						{effects.length}
					</Badge>
				</CardTitle>
			</CardHeader>
			<CardContent>
				<div className="space-y-3">
					{effects.map((effect) => {
						const bonus = getEffectBonus(effect);
						const duration = getDurationText(effect);

						return (
							<div
								key={effect.id}
								className="rounded-lg border border-border bg-card p-3 space-y-2"
							>
								<div className="flex items-start gap-2">
									{getEffectIcon(effect.effect_type)}
									<div className="flex-1 space-y-1">
										<div className="flex items-center gap-2">
											<span className="font-medium text-sm">{effect.name}</span>
											{effect.requires_concentration && (
												<Badge variant="outline" className="text-xs h-5">
													<Zap className="h-3 w-3 mr-1" />
													Concentration
												</Badge>
											)}
										</div>

										<p className="text-xs text-muted-foreground">
											{effect.description}
										</p>

										<div className="flex items-center gap-2 flex-wrap">
											<Badge
												variant="outline"
												className={`text-xs ${getEffectBadgeColor(effect.effect_type)}`}
											>
												{effect.effect_type.toUpperCase()}
											</Badge>

											{bonus && (
												<Badge variant="outline" className="text-xs">
													{bonus}
												</Badge>
											)}

											<div className="flex items-center gap-1 text-xs text-muted-foreground">
												<Clock className="h-3 w-3" />
												{duration}
											</div>
										</div>
									</div>
								</div>
							</div>
						);
					})}
				</div>
			</CardContent>
		</Card>
	);
}
