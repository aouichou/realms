'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useToast } from '@/components/ui/toast';
import { apiClient } from '@/lib/api-client';
import { ArrowLeft, ArrowRight, Sparkles } from 'lucide-react';
import { useState } from 'react';

interface CustomAdventureWizardProps {
	characterId: string;
	onComplete: (adventureId: string, adventure: any) => void;
	onCancel: () => void;
}

const SETTINGS = [
	{ id: 'haunted_castle', name: 'Haunted Castle', icon: '🏰', description: 'Explore a cursed fortress filled with undead and dark secrets' },
	{ id: 'ancient_ruins', name: 'Ancient Ruins', icon: '🏛️', description: 'Uncover mysteries in forgotten temples and lost civilizations' },
	{ id: 'dark_forest', name: 'Dark Forest', icon: '🌲', description: 'Navigate through twisted woods teeming with monsters' },
	{ id: 'underground_dungeon', name: 'Underground Dungeon', icon: '⛏️', description: 'Delve into dangerous caverns and hidden chambers' },
	{ id: 'pirate_port', name: 'Pirate Port', icon: '⚓', description: 'Navigate treacherous waters and lawless harbors' },
	{ id: 'desert_oasis', name: 'Desert Oasis', icon: '🏜️', description: 'Survive harsh sands and discover ancient secrets' },
	{ id: 'mountain_peak', name: 'Mountain Peak', icon: '⛰️', description: 'Climb treacherous heights to reach legendary summits' },
	{ id: 'mystical_academy', name: 'Mystical Academy', icon: '📚', description: 'Unravel magical mysteries in a school of sorcery' },
];

const GOALS = [
	{ id: 'rescue_mission', name: 'Rescue Mission', icon: '🆘', description: 'Save someone important from danger' },
	{ id: 'find_artifact', name: 'Find Artifact', icon: '💎', description: 'Locate a powerful magical item' },
	{ id: 'defeat_villain', name: 'Defeat Villain', icon: '⚔️', description: 'Stop an evil force threatening the realm' },
	{ id: 'solve_mystery', name: 'Solve Mystery', icon: '🔍', description: 'Uncover the truth behind strange events' },
	{ id: 'treasure_hunt', name: 'Treasure Hunt', icon: '💰', description: 'Find legendary riches and fortune' },
	{ id: 'diplomatic_mission', name: 'Diplomatic Mission', icon: '🤝', description: 'Negotiate peace or forge alliances' },
	{ id: 'exploration', name: 'Exploration', icon: '🗺️', description: 'Discover uncharted territories' },
	{ id: 'survival', name: 'Survival', icon: '🛡️', description: 'Endure and overcome overwhelming odds' },
];

const TONES = [
	{ id: 'epic_heroic', name: 'Epic Heroic', icon: '⭐', description: 'Grand adventures with legendary heroes' },
	{ id: 'dark_gritty', name: 'Dark & Gritty', icon: '🌑', description: 'Mature themes with moral ambiguity' },
	{ id: 'lighthearted', name: 'Lighthearted', icon: '😄', description: 'Fun and humorous adventures' },
	{ id: 'horror', name: 'Horror', icon: '👻', description: 'Terrifying encounters and dread' },
	{ id: 'mystery', name: 'Mystery', icon: '🕵️', description: 'Intrigue and investigation focused' },
];

export function CustomAdventureWizard({ characterId, onComplete, onCancel }: CustomAdventureWizardProps) {
	const [currentStep, setCurrentStep] = useState(1);
	const [selectedSetting, setSelectedSetting] = useState<string>('');
	const [selectedGoal, setSelectedGoal] = useState<string>('');
	const [selectedTone, setSelectedTone] = useState<string>('');
	const [isGenerating, setIsGenerating] = useState(false);
	const { showToast } = useToast();

	const canProceed = () => {
		if (currentStep === 1) return !!selectedSetting;
		if (currentStep === 2) return !!selectedGoal;
		if (currentStep === 3) return !!selectedTone;
		return false;
	};

	const handleNext = () => {
		if (currentStep < 3) {
			setCurrentStep(currentStep + 1);
		} else {
			handleGenerate();
		}
	};

	const handleBack = () => {
		if (currentStep > 1) {
			setCurrentStep(currentStep - 1);
		} else {
			onCancel();
		}
	};

	const handleGenerate = async () => {
		setIsGenerating(true);
		try {
			const response = await apiClient.post('/api/adventures/generate', {
				character_id: characterId,
				setting: selectedSetting,
				goal: selectedGoal,
				tone: selectedTone,
			});

			if (response.ok) {
				const data = await response.json();
				showToast('Adventure generated successfully!', 'success');
				onComplete(data.id, data);
			} else {
				const error = await response.json();
				showToast(error.detail || 'Failed to generate adventure', 'error');
			}
		} catch (error) {
			console.error('Error generating adventure:', error);
			showToast('Error generating adventure', 'error');
		} finally {
			setIsGenerating(false);
		}
	};

	return (
		<div className="min-h-screen bg-background p-8">
			<div className="max-w-4xl mx-auto">
				<div className="flex items-center justify-center gap-3 mb-8">
					<Sparkles className="w-8 h-8 text-accent-600" />
					<h1 className="font-display text-4xl text-primary-900">
						Create Custom Adventure
					</h1>
				</div>

				{/* Step Indicator */}
				<div className="flex justify-center mb-8">
					<div className="flex items-center gap-4">
						<div className={`flex items-center gap-2 ${currentStep === 1 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-10 h-10 rounded-full flex items-center justify-center ${currentStep === 1 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								1
							</div>
							<span>Setting</span>
						</div>
						<div className="w-16 h-0.5 bg-muted" />
						<div className={`flex items-center gap-2 ${currentStep === 2 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-10 h-10 rounded-full flex items-center justify-center ${currentStep === 2 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								2
							</div>
							<span>Goal</span>
						</div>
						<div className="w-16 h-0.5 bg-muted" />
						<div className={`flex items-center gap-2 ${currentStep === 3 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-10 h-10 rounded-full flex items-center justify-center ${currentStep === 3 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								3
							</div>
							<span>Tone</span>
						</div>
					</div>
				</div>

				<Card>
					<CardHeader>
						<CardTitle className="font-display">
							{currentStep === 1 && 'Choose Your Setting'}
							{currentStep === 2 && 'Choose Your Goal'}
							{currentStep === 3 && 'Choose Your Tone'}
						</CardTitle>
						<CardDescription>
							{currentStep === 1 && 'Where will your adventure take place?'}
							{currentStep === 2 && 'What is the main objective of your quest?'}
							{currentStep === 3 && 'What mood do you prefer for your adventure?'}
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6">
						{/* Step 1: Setting */}
						{currentStep === 1 && (
							<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
								{SETTINGS.map((setting) => (
									<div
										key={setting.id}
										className={`p-4 rounded-lg border-2 cursor-pointer transition-all hover:bg-muted/50 ${selectedSetting === setting.id
											? 'border-primary-600 bg-primary-50'
											: 'border-muted hover:border-primary-300'
											}`}
										onClick={() => setSelectedSetting(setting.id)}
									>
										<div className="flex items-start gap-3">
											<span className="text-4xl">{setting.icon}</span>
											<div className="flex-1">
												<h3 className="font-semibold text-base mb-1">{setting.name}</h3>
												<p className="text-sm text-muted-foreground font-body">
													{setting.description}
												</p>
											</div>
										</div>
									</div>
								))}
							</div>
						)}

						{/* Step 2: Goal */}
						{currentStep === 2 && (
							<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
								{GOALS.map((goal) => (
									<div
										key={goal.id}
										className={`p-4 rounded-lg border-2 cursor-pointer transition-all hover:bg-muted/50 ${selectedGoal === goal.id
											? 'border-primary-600 bg-primary-50'
											: 'border-muted hover:border-primary-300'
											}`}
										onClick={() => setSelectedGoal(goal.id)}
									>
										<div className="flex items-start gap-3">
											<span className="text-4xl">{goal.icon}</span>
											<div className="flex-1">
												<h3 className="font-semibold text-base mb-1">{goal.name}</h3>
												<p className="text-sm text-muted-foreground font-body">
													{goal.description}
												</p>
											</div>
										</div>
									</div>
								))}
							</div>
						)}

						{/* Step 3: Tone */}
						{currentStep === 3 && (
							<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
								{TONES.map((tone) => (
									<div
										key={tone.id}
										className={`p-4 rounded-lg border-2 cursor-pointer transition-all hover:bg-muted/50 ${selectedTone === tone.id
											? 'border-primary-600 bg-primary-50'
											: 'border-muted hover:border-primary-300'
											}`}
										onClick={() => setSelectedTone(tone.id)}
									>
										<div className="flex items-start gap-3">
											<span className="text-4xl">{tone.icon}</span>
											<div className="flex-1">
												<h3 className="font-semibold text-base mb-1">{tone.name}</h3>
												<p className="text-sm text-muted-foreground font-body">
													{tone.description}
												</p>
											</div>
										</div>
									</div>
								))}
							</div>
						)}

						{/* Selection Summary */}
						{(selectedSetting || selectedGoal || selectedTone) && (
							<Card className="bg-primary-50 border-primary-200">
								<CardContent className="pt-6">
									<h3 className="font-display text-lg text-primary-900 mb-3">
										Your Adventure
									</h3>
									<div className="space-y-2 text-sm">
										{selectedSetting && (
											<p className="font-body">
												<span className="font-semibold">Setting:</span>{' '}
												{SETTINGS.find(s => s.id === selectedSetting)?.name}
											</p>
										)}
										{selectedGoal && (
											<p className="font-body">
												<span className="font-semibold">Goal:</span>{' '}
												{GOALS.find(g => g.id === selectedGoal)?.name}
											</p>
										)}
										{selectedTone && (
											<p className="font-body">
												<span className="font-semibold">Tone:</span>{' '}
												{TONES.find(t => t.id === selectedTone)?.name}
											</p>
										)}
									</div>
								</CardContent>
							</Card>
						)}

						{/* Navigation Buttons */}
						<div className="flex justify-between pt-4">
							<Button onClick={handleBack} variant="outline" className="gap-2">
								<ArrowLeft className="w-4 h-4" />
								{currentStep === 1 ? 'Cancel' : 'Back'}
							</Button>
							<Button
								onClick={handleNext}
								disabled={!canProceed() || isGenerating}
								className="gap-2 min-w-40"
							>
								{isGenerating ? (
									<>
										<LoadingSpinner size="sm" />
										Generating...
									</>
								) : currentStep === 3 ? (
									<>
										<Sparkles className="w-4 h-4" />
										Generate Adventure
									</>
								) : (
									<>
										Next
										<ArrowRight className="w-4 h-4" />
									</>
								)}
							</Button>
						</div>
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
