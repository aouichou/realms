import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { BACKGROUNDS, type Background } from '@/lib/backgrounds';
import { SKILLS } from '@/lib/skills';
import { BookOpen, Sparkles, User } from 'lucide-react';
import { useState } from 'react';

interface BackgroundSelectionProps {
	onComplete: (background: {
		name: string;
		description: string;
		skillProficiencies: string[];
	}) => void;
	onBack: () => void;
}

export function BackgroundSelection({
	onComplete,
	onBack,
}: BackgroundSelectionProps) {
	const [selectedBackground, setSelectedBackground] = useState<Background | null>(null);
	const [isCustom, setIsCustom] = useState(false);

	// Custom background state
	const [customName, setCustomName] = useState('');
	const [customDescription, setCustomDescription] = useState('');
	const [customSkills, setCustomSkills] = useState<string[]>([]);

	const handlePresetSelect = (background: Background) => {
		setSelectedBackground(background);
		setIsCustom(false);
	};

	const handleCustom = () => {
		setIsCustom(true);
		setSelectedBackground(null);
	};

	const handleCustomSkillToggle = (skillName: string) => {
		setCustomSkills(prev => {
			if (prev.includes(skillName)) {
				return prev.filter(s => s !== skillName);
			} else if (prev.length < 2) {
				return [...prev, skillName];
			}
			return prev;
		});
	};

	const handleComplete = () => {
		if (isCustom) {
			if (!customName.trim() || !customDescription.trim() || customSkills.length !== 2) {
				return;
			}
			onComplete({
				name: customName.trim(),
				description: customDescription.trim(),
				skillProficiencies: customSkills,
			});
		} else if (selectedBackground) {
			onComplete({
				name: selectedBackground.name,
				description: selectedBackground.description,
				skillProficiencies: selectedBackground.skillProficiencies,
			});
		}
	};

	const canComplete = isCustom
		? customName.trim() && customDescription.trim() && customSkills.length === 2
		: selectedBackground !== null;

	return (
		<div className="space-y-6">
			<Card>
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<BookOpen className="h-5 w-5" />
						Choose Your Background
					</CardTitle>
					<CardDescription>
						Select a preset background or create your own
					</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="space-y-4">
						{/* Custom Background Option */}
						<Card
							className={`cursor-pointer transition-all ${isCustom
								? 'border-primary-500 ring-2 ring-primary-500'
								: 'hover:border-primary-300'
								}`}
							onClick={handleCustom}
						>
							<CardHeader>
								<CardTitle className="text-lg flex items-center gap-2">
									<Sparkles className="h-4 w-4" />
									Custom Background
								</CardTitle>
								<CardDescription>
									Create your own unique background story
								</CardDescription>
							</CardHeader>
						</Card>

						{/* Preset Backgrounds Grid */}
						<div className="mt-4">
							<h3 className="text-sm font-semibold mb-3 text-muted-foreground">
								Preset Backgrounds
							</h3>
							<ScrollArea className="h-96">
								<div className="grid grid-cols-1 md:grid-cols-2 gap-3 pr-4">
									{BACKGROUNDS.map((bg) => (
										<Card
											key={bg.name}
											className={`cursor-pointer transition-all ${selectedBackground?.name === bg.name && !isCustom
												? 'border-primary-500 ring-2 ring-primary-500'
												: 'hover:border-primary-300'
												}`}
											onClick={() => handlePresetSelect(bg)}
										>
											<CardHeader className="p-4">
												<CardTitle className="text-base flex items-center gap-2">
													<User className="h-4 w-4" />
													{bg.name}
												</CardTitle>
												<CardDescription className="text-xs line-clamp-2">
													{bg.description}
												</CardDescription>
												<div className="flex gap-1 mt-2">
													{bg.skillProficiencies.map((skill) => (
														<Badge key={skill} variant="secondary" className="text-xs">
															{skill}
														</Badge>
													))}
												</div>
											</CardHeader>
										</Card>
									))}
								</div>
							</ScrollArea>
						</div>
					</div>
				</CardContent>
			</Card>

			{/* Custom Background Form */}
			{isCustom && (
				<Card>
					<CardHeader>
						<CardTitle>Create Custom Background</CardTitle>
						<CardDescription>
							Design your character's unique history
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-4">
						<div className="space-y-2">
							<Label htmlFor="custom-name">Background Name</Label>
							<Input
								id="custom-name"
								value={customName}
								onChange={(e) => setCustomName(e.target.value)}
								placeholder="e.g., Street Performer, Wandering Merchant"
								maxLength={50}
							/>
						</div>

						<div className="space-y-2">
							<Label htmlFor="custom-description">Description</Label>
							<Textarea
								id="custom-description"
								value={customDescription}
								onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCustomDescription(e.target.value)}
								placeholder="Describe your character's background, upbringing, and what led them to adventure..."
								rows={4}
								maxLength={500}
							/>
							<p className="text-xs text-muted-foreground">
								{customDescription.length}/500 characters
							</p>
						</div>

						<div className="space-y-2">
							<Label>Skill Proficiencies (Choose 2)</Label>
							<p className="text-sm text-muted-foreground mb-3">
								{customSkills.length} / 2 selected
							</p>
							<ScrollArea className="h-64 border rounded-md p-4">
								<div className="grid grid-cols-2 gap-3">
									{SKILLS.map((skill) => (
										<div
											key={skill.name}
											className="flex items-center space-x-2"
										>
											<Checkbox
												id={`custom-skill-${skill.name}`}
												checked={customSkills.includes(skill.name)}
												onCheckedChange={() => handleCustomSkillToggle(skill.name)}
												disabled={
													!customSkills.includes(skill.name) &&
													customSkills.length >= 2
												}
											/>
											<label
												htmlFor={`custom-skill-${skill.name}`}
												className="text-sm cursor-pointer flex items-center gap-2"
											>
												{skill.name}
												<Badge variant="outline" className="text-xs">
													{skill.ability}
												</Badge>
											</label>
										</div>
									))}
								</div>
							</ScrollArea>
						</div>
					</CardContent>
				</Card>
			)}

			{/* Selected Background Details */}
			{selectedBackground && !isCustom && (
				<Card>
					<CardHeader>
						<CardTitle>{selectedBackground.name}</CardTitle>
						<CardDescription>Background Details</CardDescription>
					</CardHeader>
					<CardContent className="space-y-4">
						<div>
							<h4 className="text-sm font-semibold mb-2">Description</h4>
							<p className="text-sm text-muted-foreground">
								{selectedBackground.description}
							</p>
						</div>
						<div>
							<h4 className="text-sm font-semibold mb-2">Skill Proficiencies</h4>
							<div className="flex gap-2">
								{selectedBackground.skillProficiencies.map((skill) => (
									<Badge key={skill} variant="secondary">
										{skill}
									</Badge>
								))}
							</div>
						</div>
						<div>
							<h4 className="text-sm font-semibold mb-2">Feature: {selectedBackground.feature}</h4>
							<p className="text-sm text-muted-foreground">
								{selectedBackground.featureDescription}
							</p>
						</div>
					</CardContent>
				</Card>
			)}

			{/* Navigation Buttons */}
			<div className="flex justify-between">
				<Button onClick={onBack} variant="outline">
					Back
				</Button>
				<Button
					onClick={handleComplete}
					disabled={!canComplete}
				>
					{isCustom ? 'Complete Background' : 'Continue'}
				</Button>
			</div>
		</div>
	);
}
