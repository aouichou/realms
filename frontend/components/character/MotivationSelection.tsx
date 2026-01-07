'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft } from 'lucide-react';
import { useState } from 'react';

interface MotivationSelectionProps {
	onComplete: (motivation: string) => void;
	onBack: () => void;
}

const MOTIVATIONS = [
	{
		id: 'wealth',
		name: 'Wealth & Riches',
		icon: '💰',
		description: 'Driven by the promise of gold, treasures, and material prosperity.',
	},
	{
		id: 'glory',
		name: 'Glory & Fame',
		icon: '⭐',
		description: 'Seeks recognition, honor, and to become a legendary hero.',
	},
	{
		id: 'knowledge',
		name: 'Knowledge & Discovery',
		icon: '📚',
		description: 'Pursues ancient secrets, magical lore, and forbidden wisdom.',
	},
	{
		id: 'redemption',
		name: 'Redemption',
		icon: '🕊️',
		description: 'Atones for past mistakes and seeks to right old wrongs.',
	},
	{
		id: 'revenge',
		name: 'Revenge',
		icon: '⚔️',
		description: 'Hunts those who wronged them or their loved ones.',
	},
	{
		id: 'duty',
		name: 'Duty & Honor',
		icon: '🛡️',
		description: 'Bound by oath, loyalty, or obligation to a cause or person.',
	},
	{
		id: 'power',
		name: 'Power & Control',
		icon: '👑',
		description: 'Craves influence, authority, and the ability to shape the world.',
	},
	{
		id: 'justice',
		name: 'Justice & Protection',
		icon: '⚖️',
		description: 'Defends the innocent and fights against tyranny and evil.',
	},
	{
		id: 'wanderlust',
		name: 'Adventure & Wanderlust',
		icon: '🗺️',
		description: 'Explores the unknown, driven by curiosity and love of adventure.',
	},
	{
		id: 'survival',
		name: 'Survival',
		icon: '💪',
		description: 'Fights to stay alive, escape danger, or protect their own.',
	},
];

export function MotivationSelection({ onComplete, onBack }: MotivationSelectionProps) {
	const [selectedMotivation, setSelectedMotivation] = useState<string>('');

	const handleSubmit = () => {
		if (selectedMotivation) {
			onComplete(selectedMotivation);
		}
	};

	const selectedMotivationData = MOTIVATIONS.find(m => m.id === selectedMotivation);

	return (
		<Card>
			<CardHeader>
				<CardTitle className="font-display">Character Motivation</CardTitle>
				<CardDescription>
					What drives your character to embark on dangerous adventures?
					This will influence how the AI Dungeon Master responds to your actions.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-6">
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					{MOTIVATIONS.map((motivation) => (
						<div
							key={motivation.id}
							className={`p-4 rounded-lg border-2 cursor-pointer transition-all hover:bg-muted/50 ${selectedMotivation === motivation.id
									? 'border-primary-600 bg-primary-50'
									: 'border-muted hover:border-primary-300'
								}`}
							onClick={() => setSelectedMotivation(motivation.id)}
						>
							<div className="flex items-start gap-3">
								<span className="text-3xl">{motivation.icon}</span>
								<div className="flex-1">
									<h3 className="font-semibold text-base mb-1">{motivation.name}</h3>
									<p className="text-sm text-muted-foreground font-body">
										{motivation.description}
									</p>
								</div>
							</div>
						</div>
					))}
				</div>

				{selectedMotivationData && (
					<Card className="bg-primary-50 border-primary-200">
						<CardContent className="pt-6">
							<div className="flex items-start gap-3">
								<span className="text-4xl">{selectedMotivationData.icon}</span>
								<div>
									<h3 className="font-display text-lg text-primary-900 mb-1">
										{selectedMotivationData.name}
									</h3>
									<p className="text-sm text-primary-700 font-body">
										Your character is primarily motivated by{' '}
										<strong>{selectedMotivationData.name.toLowerCase()}</strong>.
										The DM will weave opportunities and challenges related to this into your adventure.
									</p>
								</div>
							</div>
						</CardContent>
					</Card>
				)}

				<div className="flex justify-between pt-4">
					<Button onClick={onBack} variant="outline" className="gap-2">
						<ArrowLeft className="w-4 h-4" />
						Back
					</Button>
					<Button
						onClick={handleSubmit}
						disabled={!selectedMotivation}
						size="lg"
						className="min-w-40"
					>
						Complete Character
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}
