"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, Check, Clock, Sparkles, Target, Zap } from "lucide-react";
import { Spell } from "./SpellBrowser";

interface SpellCardProps {
	spell: Spell;
	onClick?: () => void;
	onSelect?: () => void;
	isSelected?: boolean;
}

const SCHOOL_COLORS: Record<string, string> = {
	Abjuration: "bg-blue-500 hover:bg-blue-600",
	Conjuration: "bg-purple-500 hover:bg-purple-600",
	Divination: "bg-cyan-500 hover:bg-cyan-600",
	Enchantment: "bg-pink-500 hover:bg-pink-600",
	Evocation: "bg-red-500 hover:bg-red-600",
	Illusion: "bg-indigo-500 hover:bg-indigo-600",
	Necromancy: "bg-gray-700 hover:bg-gray-800",
	Transmutation: "bg-green-500 hover:bg-green-600",
};

const SCHOOL_TEXT_COLORS: Record<string, string> = {
	Abjuration: "text-blue-600",
	Conjuration: "text-purple-600",
	Divination: "text-cyan-600",
	Enchantment: "text-pink-600",
	Evocation: "text-red-600",
	Illusion: "text-indigo-600",
	Necromancy: "text-gray-700",
	Transmutation: "text-green-600",
};

export function SpellCard({ spell, onClick, onSelect, isSelected }: SpellCardProps) {
	const schoolColor = SCHOOL_COLORS[spell.school] || "bg-gray-500";
	const schoolTextColor = SCHOOL_TEXT_COLORS[spell.school] || "text-gray-600";

	const formatLevel = (level: number) => {
		if (level === 0) return "Cantrip";
		const suffix = level === 1 ? "st" : level === 2 ? "nd" : level === 3 ? "rd" : "th";
		return `${level}${suffix} level`;
	};

	const components = [];
	if (spell.verbal) components.push("V");
	if (spell.somatic) components.push("S");
	if (spell.material) components.push("M");

	return (
		<Card
			className={`cursor-pointer transition-all hover:shadow-lg ${isSelected ? 'ring-2 ring-primary' : ''}`}
			onClick={onClick}
		>
			<CardHeader className="pb-3">
				<div className="flex items-start justify-between gap-2">
					<CardTitle className="text-lg">{spell.name}</CardTitle>
					{onSelect && (
						<Button
							type="button"
							size="sm"
							variant={isSelected ? "default" : "outline"}
							onClick={(e) => {
								e.stopPropagation();
								onSelect();
							}}
							className="shrink-0"
						>
							{isSelected && <Check className="h-4 w-4 mr-1" />}
							{isSelected ? "Selected" : "Select"}
						</Button>
					)}
				</div>
				<div className="flex items-center gap-2 flex-wrap">
					<Badge variant="outline" className={schoolTextColor}>
						{spell.school}
					</Badge>
					<Badge variant="secondary">{formatLevel(spell.level)}</Badge>
				</div>
			</CardHeader>

			<CardContent className="space-y-2">
				{/* Spell Properties */}
				<div className="grid grid-cols-2 gap-2 text-sm">
					<div className="flex items-center gap-1">
						<Clock className="h-3 w-3 text-muted-foreground" />
						<span className="text-muted-foreground truncate">{spell.casting_time}</span>
					</div>
					<div className="flex items-center gap-1">
						<Target className="h-3 w-3 text-muted-foreground" />
						<span className="text-muted-foreground truncate">{spell.range}</span>
					</div>
				</div>

				{/* Components */}
				<div className="flex items-center gap-1 text-xs">
					<Sparkles className="h-3 w-3 text-muted-foreground" />
					<span className="text-muted-foreground">
						{components.join(", ")}
					</span>
				</div>

				{/* Description Preview */}
				<p className="text-sm text-muted-foreground line-clamp-3">
					{spell.description}
				</p>

				{/* Tags */}
				<div className="flex items-center gap-2 flex-wrap">
					{spell.is_concentration && (
						<Badge variant="outline" className="text-xs">
							<Zap className="h-3 w-3 mr-1" />
							Concentration
						</Badge>
					)}
					{spell.is_ritual && (
						<Badge variant="outline" className="text-xs">
							<BookOpen className="h-3 w-3 mr-1" />
							Ritual
						</Badge>
					)}
					{spell.damage_dice && (
						<Badge variant="outline" className="text-xs">
							{spell.damage_dice} {spell.damage_type}
						</Badge>
					)}
				</div>
			</CardContent>
		</Card>
	);
}
