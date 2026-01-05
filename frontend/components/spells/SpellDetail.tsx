"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import {
	BookOpen,
	Check,
	Clock,
	Shield,
	Sparkles,
	Swords,
	Target,
	Timer,
	Zap
} from "lucide-react";
import { Spell } from "./SpellBrowser";

interface SpellDetailProps {
	spell: Spell;
	open: boolean;
	onClose: () => void;
	onSelect?: () => void;
	isSelected?: boolean;
}

const SCHOOL_COLORS: Record<string, string> = {
	Abjuration: "text-blue-600",
	Conjuration: "text-purple-600",
	Divination: "text-cyan-600",
	Enchantment: "text-pink-600",
	Evocation: "text-red-600",
	Illusion: "text-indigo-600",
	Necromancy: "text-gray-700",
	Transmutation: "text-green-600",
};

export function SpellDetail({ spell, open, onClose, onSelect, isSelected }: SpellDetailProps) {
	const schoolColor = SCHOOL_COLORS[spell.school] || "text-gray-600";

	const formatLevel = (level: number) => {
		if (level === 0) return "Cantrip";
		const suffix = level === 1 ? "st" : level === 2 ? "nd" : level === 3 ? "rd" : "th";
		return `${level}${suffix}-level`;
	};

	const components = [];
	if (spell.verbal) components.push("V");
	if (spell.somatic) components.push("S");
	if (spell.material) components.push(`M (${spell.material})`);

	const availableClasses = Object.keys(spell.available_to_classes || {})
		.filter(cls => spell.available_to_classes[cls])
		.map(cls => cls.charAt(0).toUpperCase() + cls.slice(1))
		.join(", ");

	return (
		<Dialog open={open} onOpenChange={onClose}>
			<DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
				<DialogHeader>
					<div className="flex items-start justify-between gap-4">
						<div className="flex-1">
							<DialogTitle className="text-2xl">{spell.name}</DialogTitle>
							<DialogDescription>
								<span className={schoolColor}>{formatLevel(spell.level)} {spell.school}</span>
							</DialogDescription>
						</div>
						{onSelect && (
							<Button
								type="button"
								variant={isSelected ? "default" : "outline"}
								onClick={onSelect}
								className="shrink-0"
							>
								{isSelected && <Check className="h-4 w-4 mr-2" />}
								{isSelected ? "Selected" : "Select Spell"}
							</Button>
						)}
					</div>
				</DialogHeader>

				<div className="space-y-4">
					{/* Spell Properties Grid */}
					<div className="grid grid-cols-2 gap-4">
						<div className="flex items-start gap-2">
							<Clock className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
							<div>
								<div className="text-sm font-medium">Casting Time</div>
								<div className="text-sm text-muted-foreground">{spell.casting_time}</div>
							</div>
						</div>

						<div className="flex items-start gap-2">
							<Target className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
							<div>
								<div className="text-sm font-medium">Range</div>
								<div className="text-sm text-muted-foreground">{spell.range}</div>
							</div>
						</div>

						<div className="flex items-start gap-2">
							<Sparkles className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
							<div>
								<div className="text-sm font-medium">Components</div>
								<div className="text-sm text-muted-foreground">{components.join(", ")}</div>
							</div>
						</div>

						<div className="flex items-start gap-2">
							<Timer className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
							<div>
								<div className="text-sm font-medium">Duration</div>
								<div className="text-sm text-muted-foreground">{spell.duration}</div>
							</div>
						</div>
					</div>

					{/* Tags */}
					<div className="flex items-center gap-2 flex-wrap">
						{spell.is_concentration && (
							<Badge variant="outline">
								<Zap className="h-3 w-3 mr-1" />
								Concentration
							</Badge>
						)}
						{spell.is_ritual && (
							<Badge variant="outline">
								<BookOpen className="h-3 w-3 mr-1" />
								Ritual
							</Badge>
						)}
						{spell.damage_dice && (
							<Badge variant="outline">
								<Swords className="h-3 w-3 mr-1" />
								{spell.damage_dice} {spell.damage_type}
							</Badge>
						)}
						{spell.save_ability && (
							<Badge variant="outline">
								<Shield className="h-3 w-3 mr-1" />
								{spell.save_ability.charAt(0).toUpperCase() + spell.save_ability.slice(1)} Save
							</Badge>
						)}
					</div>

					<Separator />

					{/* Description */}
					<div>
						<h3 className="text-sm font-medium mb-2">Description</h3>
						<p className="text-sm text-muted-foreground whitespace-pre-wrap">
							{spell.description}
						</p>
					</div>

					{/* Available Classes */}
					{availableClasses && (
						<>
							<Separator />
							<div>
								<h3 className="text-sm font-medium mb-2">Available To</h3>
								<p className="text-sm text-muted-foreground">{availableClasses}</p>
							</div>
						</>
					)}
				</div>

				<DialogFooter>
					<Button type="button" variant="outline" onClick={onClose}>
						Close
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
