"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "@/lib/hooks/useTranslation";
import { Shield, X, Zap } from "lucide-react";
import { useState } from "react";

interface ConcentrationSpell {
	spellId: string;
	spellName: string;
	spellLevel: number;
	duration: string;
	startedAt: Date;
}

interface ConcentrationTrackerProps {
	characterId: string;
	characterName?: string;
	constitutionModifier: number;
	onConcentrationBroken?: () => void;
}

export function ConcentrationTracker({
	characterId,
	characterName,
	constitutionModifier,
	onConcentrationBroken,
}: ConcentrationTrackerProps) {
	const { t } = useTranslation();
	const [activeConcentration, setActiveConcentration] = useState<ConcentrationSpell | null>(null);
	const [showSavePrompt, setShowSavePrompt] = useState(false);
	const [damageTaken, setDamageTaken] = useState(0);

	const startConcentration = (spell: ConcentrationSpell) => {
		if (activeConcentration) {
			// Breaking existing concentration
			setActiveConcentration(spell);
		} else {
			setActiveConcentration(spell);
		}
	};

	const endConcentration = () => {
		setActiveConcentration(null);
		setShowSavePrompt(false);
		setDamageTaken(0);
		onConcentrationBroken?.();
	};

	const takeDamage = (damage: number) => {
		setDamageTaken(damage);
		setShowSavePrompt(true);
	};

	const calculateConcentrationDC = (damage: number): number => {
		return Math.max(10, Math.floor(damage / 2));
	};

	const rollConcentrationSave = () => {
		const roll = Math.floor(Math.random() * 20) + 1;
		const total = roll + constitutionModifier;
		const dc = calculateConcentrationDC(damageTaken);

		if (total >= dc) {
			return { success: true, roll, total, dc };
		} else {
			endConcentration();
			return { success: false, roll, total, dc };
		}
	};

	if (!activeConcentration) {
		return null;
	}

	const elapsedTime = Math.floor((Date.now() - activeConcentration.startedAt.getTime()) / 1000);
	const minutes = Math.floor(elapsedTime / 60);
	const seconds = elapsedTime % 60;

	return (
		<Card className="border-amber-500">
			<CardHeader className="pb-3">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						<Zap className="h-4 w-4 text-amber-500" />
						<CardTitle className="text-sm">{t('concentrationTracker.concentrating')}</CardTitle>
					</div>
					<Button
						variant="ghost"
						size="sm"
						onClick={endConcentration}
						className="h-6 w-6 p-0"
					>
						<X className="h-4 w-4" />
					</Button>
				</div>
			</CardHeader>
			<CardContent className="space-y-3">
				<div>
					<div className="flex items-center gap-2 mb-1">
						<span className="font-semibold">{activeConcentration.spellName}</span>
						<Badge variant="outline" className="text-xs">
							{t('common.level')} {activeConcentration.spellLevel}
						</Badge>
					</div>
					<p className="text-xs text-muted-foreground">
						{t('concentrationTracker.duration')} {activeConcentration.duration}
					</p>
					<p className="text-xs text-muted-foreground">
						{t('concentrationTracker.elapsed')} {minutes}m {seconds}s
					</p>
				</div>

				{showSavePrompt && (
					<Alert>
						<Shield className="h-4 w-4" />
						<AlertDescription>
							<p className="font-semibold mb-2">{t('concentrationTracker.saveRequired')}</p>
							<p className="text-xs mb-2">
								{`Took ${damageTaken} damage. DC ${calculateConcentrationDC(damageTaken)} Constitution save required.`}
							</p>
							<div className="flex gap-2">
								<Button
									size="sm"
									onClick={() => {
										const result = rollConcentrationSave();
										alert(
											result.success
												? `Success! Rolled ${result.roll} + ${constitutionModifier} = ${result.total} (DC ${result.dc})`
												: `Failed! Rolled ${result.roll} + ${constitutionModifier} = ${result.total} (DC ${result.dc}). Concentration broken!`
										);
										setShowSavePrompt(false);
									}}
								>
									{t('concentrationTracker.rollSave')}
								</Button>
								<Button
									size="sm"
									variant="outline"
									onClick={() => setShowSavePrompt(false)}
								>
									{t('common.cancel')}
								</Button>
							</div>
						</AlertDescription>
					</Alert>
				)}

				<Alert>
					<AlertDescription className="text-xs">
						{t('concentrationTracker.concentrationInfo')}
					</AlertDescription>
				</Alert>
			</CardContent>
		</Card>
	);
}

// Export helper to use in spell casting
export function useConcentration() {
	const [concentrating, setConcentrating] = useState<ConcentrationSpell | null>(null);

	const startConcentration = (spell: ConcentrationSpell) => {
		setConcentrating(spell);
	};

	const breakConcentration = () => {
		setConcentrating(null);
	};

	return {
		concentrating,
		startConcentration,
		breakConcentration,
	};
}
