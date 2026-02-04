"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useTranslation } from "@/lib/hooks/useTranslation";
import { Clock, Sparkles } from "lucide-react";
import { useState } from "react";

interface Spell {
	id: string;
	name: string;
	level: number;
	casting_time: string;
	ritual: boolean;
	school: string;
	description: string;
}

interface RitualCastingDialogProps {
	spell: Spell;
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onCastAsRitual: (spellId: string) => void;
	onCastNormally: (spellId: string) => void;
}

export function RitualCastingDialog({
spell,
open,
onOpenChange,
onCastAsRitual,
onCastNormally,
}: RitualCastingDialogProps) {
	const { t } = useTranslation();
	const [casting, setCasting] = useState(false);

	if (!spell.ritual) {
		return null;
	}

	const handleRitualCast = async () => {
		setCasting(true);
		try {
			await onCastAsRitual(spell.id);
			onOpenChange(false);
		} finally {
			setCasting(false);
		}
	};

	const handleNormalCast = async () => {
		setCasting(true);
		try {
			await onCastNormally(spell.id);
			onOpenChange(false);
		} finally {
			setCasting(false);
		}
	};

	// Calculate ritual casting time
	const getRitualCastingTime = (normalTime: string): string => {
		// If already includes ritual time, return as-is
		if (normalTime.toLowerCase().includes("ritual")) {
			return normalTime;
		}

		// Add 10 minutes to the normal casting time
		if (normalTime === "1 action") {
			return "11 minutes";
		} else if (normalTime.includes("minute")) {
			const minutes = parseInt(normalTime);
			return `${minutes + 10} minutes`;
		}

		return "10 minutes + " + normalTime;
	};

	const ritualTime = getRitualCastingTime(spell.casting_time);

	return (
<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent>
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<Sparkles className="h-5 w-5 text-accent-400" />
						Cast {spell.name} as Ritual?
					</DialogTitle>
					<DialogDescription>
						{t('ritualCasting.description')}
						<div className="space-y-4">
							<div className="space-y-2">
								<div className="flex items-center justify-between">
									<span className="text-sm font-semibold">{t('ritualCasting.normalCasting')}</span>
									<Badge variant="outline">{spell.casting_time}</Badge>
								</div>
								<div className="flex items-center justify-between">
									<span className="text-sm font-semibold">{t('ritualCasting.ritualCasting')}</span>
									<Badge variant="secondary" className="flex items-center gap-1">
										<Clock className="h-3 w-3" />
										{ritualTime}
									</Badge>
								</div>
							</div>

							<Alert>
								<Sparkles className="h-4 w-4" />
								<AlertDescription>
									<div className="space-y-2">
										<p className="font-semibold">{t('ritualCasting.benefitsTitle')}</p>
										<ul className="text-sm list-disc list-inside space-y-1">
											<li>{t('ritualCasting.benefit1')}</li>
											<li>{t('ritualCasting.benefit2')}</li>
											<li>{t('ritualCasting.benefit3')}</li>
										</ul>

										<p className="font-semibold mt-3">{t('ritualCasting.drawbacksTitle')}</p>
										<ul className="text-sm list-disc list-inside space-y-1">
											<li>{t('ritualCasting.drawback1')}</li>
											<li>{t('ritualCasting.drawback2')}</li>
										</ul>

										<div className="bg-muted p-3 rounded-md">
											<p className="text-sm font-semibold mb-1">{spell.name}</p>
											<p className="text-xs text-muted-foreground">
												{spell.description.slice(0, 200)}...
											</p>
										</div>
									</div>
								</AlertDescription>
							</Alert>
						</div>
					</DialogDescription>
				</DialogHeader>

				<DialogFooter className="flex-col sm:flex-col gap-2">
					<Button
						onClick={handleRitualCast}
						disabled={casting}
						className="w-full"
						variant="secondary"
					>
						<Clock className="mr-2 h-4 w-4" />
						Cast as Ritual ({ritualTime})
					</Button>

					<Button
						onClick={handleNormalCast}
						disabled={casting}
						className="w-full"
					>
						{t('ritualCasting.castNormally')} ({spell.casting_time})
					</Button>

					<Button
						onClick={() => onOpenChange(false)}
						variant="outline"
						disabled={casting}
						className="w-full"
					>
						{t('common.cancel')}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}

// Component to add ritual tag to spell cards
export function RitualBadge() {
	const { t } = useTranslation();
	return (
<Badge variant="secondary" className="flex items-center gap-1">
			<Sparkles className="h-3 w-3" />
			{t('ritualCasting.ritual')}
		</Badge>
	);
}
