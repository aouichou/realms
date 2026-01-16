'use client';

import { BackgroundSelection } from '@/components/character/BackgroundSelection';
import { MotivationSelection } from '@/components/character/MotivationSelection';
import PersonalitySelection from '@/components/character/PersonalitySelection';
import SkillProficiencySelection from '@/components/character/SkillProficiencySelection';
import { SpellSelectionStep } from '@/components/SpellSelectionStep';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/components/ui/toast';
import { apiClient } from '@/lib/api-client';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

// D&D 5e Classes and Races from backend API
const DND_CLASSES = [
	{ id: 'barbarian', name: 'Barbarian', hitDie: 12 },
	{ id: 'bard', name: 'Bard', hitDie: 8 },
	{ id: 'cleric', name: 'Cleric', hitDie: 8 },
	{ id: 'druid', name: 'Druid', hitDie: 8 },
	{ id: 'fighter', name: 'Fighter', hitDie: 10 },
	{ id: 'monk', name: 'Monk', hitDie: 8 },
	{ id: 'paladin', name: 'Paladin', hitDie: 10 },
	{ id: 'ranger', name: 'Ranger', hitDie: 10 },
	{ id: 'rogue', name: 'Rogue', hitDie: 8 },
	{ id: 'sorcerer', name: 'Sorcerer', hitDie: 6 },
	{ id: 'warlock', name: 'Warlock', hitDie: 8 },
	{ id: 'wizard', name: 'Wizard', hitDie: 6 },
];

const DND_RACES = [
	'Dragonborn', 'Dwarf', 'Elf', 'Gnome', 'Half-Elf', 'Halfling',
	'Half-Orc', 'Human', 'Tiefling'
];

interface AbilityScores {
	strength: number;
	dexterity: number;
	constitution: number;
	intelligence: number;
	wisdom: number;
	charisma: number;
}

// D&D 5e Point Buy System
// Score 8 = 0 points, 9 = 1, 10 = 2, 11 = 3, 12 = 4, 13 = 5, 14 = 7, 15 = 9
const POINT_BUY_COSTS: Record<number, number> = {
	8: 0,
	9: 1,
	10: 2,
	11: 3,
	12: 4,
	13: 5,
	14: 7,
	15: 9,
};

const POINT_BUY_MAX = 27; // Standard D&D 5e point buy

export default function CharacterCreation() {
	const router = useRouter();
	const { showToast } = useToast();
	const [currentStep, setCurrentStep] = useState(1);
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [name, setName] = useState('');
	const [selectedClass, setSelectedClass] = useState('');
	const [selectedRace, setSelectedRace] = useState('');
	const [level, setLevel] = useState(1);
	const [nameError, setNameError] = useState('');
	const [abilities, setAbilities] = useState<AbilityScores>({
		strength: 8,
		dexterity: 8,
		constitution: 8,
		intelligence: 8,
		wisdom: 8,
		charisma: 8,
	});
	const [skillProficiencies, setSkillProficiencies] = useState<string[]>([]);
	const [backgroundName, setBackgroundName] = useState('');
	const [backgroundDescription, setBackgroundDescription] = useState('');
	const [backgroundSkills, setBackgroundSkills] = useState<string[]>([]);
	const [personalityTrait, setPersonalityTrait] = useState('');
	const [ideal, setIdeal] = useState('');
	const [bond, setBond] = useState('');
	const [flaw, setFlaw] = useState('');
	const [motivation, setMotivation] = useState('');
	const [selectedSpells, setSelectedSpells] = useState<Set<string>>(new Set());
	const [characterId, setCharacterId] = useState<string | null>(null);

	const calculatePointsSpent = (): number => {
		return Object.values(abilities).reduce((total, score) => {
			return total + (POINT_BUY_COSTS[score] || 0);
		}, 0);
	};

	const calculateModifier = (score: number): number => {
		return Math.floor((score - 10) / 2);
	};

	const calculateHP = (): number => {
		const classData = DND_CLASSES.find(c => c.id === selectedClass);
		if (!classData) return 0;

		const conModifier = calculateModifier(abilities.constitution);
		return classData.hitDie + conModifier;
	};

	const handleAbilityChange = (ability: keyof AbilityScores, value: string) => {
		const numValue = parseInt(value) || 8;
		// Point buy allows 8-15 before racial modifiers
		const clampedValue = Math.max(8, Math.min(15, numValue));

		// Check if this change would exceed point budget
		const newAbilities = { ...abilities, [ability]: clampedValue };
		const newTotal = Object.values(newAbilities).reduce((total, score) => {
			return total + (POINT_BUY_COSTS[score] || 0);
		}, 0);

		// Only allow change if within budget
		if (newTotal <= POINT_BUY_MAX) {
			setAbilities(newAbilities);
		}
	};

	const validateForm = (): boolean => {
		if (!name.trim()) {
			setNameError('Character name is required');
			showToast('Please enter a character name', 'error');
			return false;
		}
		if (name.trim().length < 2) {
			setNameError('Name must be at least 2 characters');
			showToast('Name is too short', 'error');
			return false;
		}
		if (!selectedClass) {
			showToast('Please select a class', 'error');
			return false;
		}
		if (!selectedRace) {
			showToast('Please select a race', 'error');
			return false;
		}
		setNameError('');
		return true;
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		if (!validateForm()) return;

		setIsSubmitting(true);

		// Get authentication token
		const token = localStorage.getItem('access_token');
		if (!token) {
			showToast('Not authenticated. Please log in or play as guest.', 'error');
			setIsSubmitting(false);
			router.push('/');
			return;
		}

		const characterData = {
			name: name.trim(),
			character_class: selectedClass,
			race: selectedRace,
			level,
			ability_scores: abilities,
		};

		try {
			const response = await apiClient.post('/api/v1/characters', characterData);

			if (response.ok) {
				const character = await response.json();
				setCharacterId(character.id);
				showToast(`${character.name} created successfully!`, 'success');
				// Move to skill selection step
				setCurrentStep(2);
			} else {
				const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
				const errorMsg = errorData.detail || errorData.message || 'Failed to create character';
				showToast(errorMsg, 'error');
			}
		} catch (error) {
			console.error('Error creating character:', error);
			const errorMsg = error instanceof Error && error.message.includes('fetch')
				? 'Cannot connect to server. Please check your connection.'
				: 'An error occurred while creating your character.';
			showToast(errorMsg, 'error');
		} finally {
			setIsSubmitting(false);
		}
	};

	const handleSkillsComplete = async (skills: string[]) => {
		if (!characterId) return;

		try {
			const response = await apiClient.post(`/api/v1/characters/${characterId}/skills`, skills);

			if (response.ok) {
				setSkillProficiencies(skills);
				showToast('Skills saved successfully!', 'success');
				// Move to background selection
				setCurrentStep(3);
			} else {
				showToast('Failed to save skills', 'error');
			}
		} catch (error) {
			console.error('Error saving skills:', error);
			showToast('Error saving skills', 'error');
		}
	};

	const handleBackgroundComplete = async (background: {
		name: string;
		description: string;
		skillProficiencies: string[];
	}) => {
		if (!characterId) return;

		try {
			const params = new URLSearchParams();
			params.append('background_name', background.name);
			params.append('background_description', background.description);
			background.skillProficiencies.forEach(skill => {
				params.append('background_skill_proficiencies', skill);
			});

			const response = await apiClient.post(`/api/v1/characters/${characterId}/background?${params.toString()}`);

			if (response.ok) {
				setBackgroundName(background.name);
				setBackgroundDescription(background.description);
				setBackgroundSkills(background.skillProficiencies);
				showToast('Background saved successfully!', 'success');
				// Move to personality selection
				setCurrentStep(4);
			} else {
				showToast('Failed to save background', 'error');
			}
		} catch (error) {
			console.error('Error saving background:', error);
			showToast('Error saving background', 'error');
		}
	};
	const handlePersonalityComplete = async (personality: {
		personality_trait: string;
		ideal: string;
		bond: string;
		flaw: string;
	}) => {
		if (!characterId) return;

		try {
			const params = new URLSearchParams();
			params.append('personality_trait', personality.personality_trait);
			params.append('ideal', personality.ideal);
			params.append('bond', personality.bond);
			params.append('flaw', personality.flaw);

			const response = await apiClient.post(`/api/v1/characters/${characterId}/personality?${params.toString()}`);

			if (response.ok) {
				setPersonalityTrait(personality.personality_trait);
				setIdeal(personality.ideal);
				setBond(personality.bond);
				setFlaw(personality.flaw);
				showToast('Personality saved successfully!', 'success');
				// Move to motivation selection (step 6)
				setCurrentStep(6);
			} else {
				showToast('Failed to save personality', 'error');
			}
		} catch (error) {
			console.error('Error saving personality:', error);
			showToast('Error saving personality', 'error');
		}
	};

	const handleMotivationComplete = async (selectedMotivation: string) => {
		if (!characterId) return;

		try {
			const params = new URLSearchParams();
			params.append('motivation', selectedMotivation);

			const response = await apiClient.post(`/api/v1/characters/${characterId}/motivation?${params.toString()}`);

			if (response.ok) {
				setMotivation(selectedMotivation);
				showToast('Motivation saved successfully!', 'success');
				// Move to spell selection if spellcaster, otherwise finish
				if (['bard', 'cleric', 'druid', 'sorcerer', 'warlock', 'wizard'].includes(selectedClass)) {
					setCurrentStep(5);
				} else {
					// Navigate to game
					setTimeout(() => router.push(`/game/${characterId}`), 1000);
				}
			} else {
				showToast('Failed to save motivation', 'error');
			}
		} catch (error) {
			console.error('Error saving motivation:', error);
			showToast('Error saving motivation', 'error');
		}
	};

	const handleSpellsComplete = async () => {
		if (!characterId) return;

		// Determine if this is a prepared caster or known caster
		const preparedCasters = ['wizard', 'cleric', 'druid', 'paladin'];
		const isPreparedCaster = preparedCasters.includes(selectedClass);

		// If spells were selected, add them to the character
		if (selectedSpells.size > 0) {
			try {
				await Promise.all(
					Array.from(selectedSpells).map(spellId =>
						apiClient.post(`/api/v1/spells/character/${characterId}/spells`, {
							spell_id: spellId,
							is_known: true,
							// Only prepared casters need to prepare spells
							// Known casters (bard, sorcerer, warlock, ranger) always have their spells available
							is_prepared: isPreparedCaster,
						})
					)
				);
				showToast('Spells saved successfully!', 'success');
			} catch (spellError) {
				console.error('Error adding spells:', spellError);
				showToast('Error saving spells', 'error');
			}
		}

		// Navigate to adventure selection page
		showToast('Character created! Now choose your adventure.', 'success');
		setTimeout(() => router.push(`/adventure/select/${characterId}`), 1000);
	};

	return (
		<div className="min-h-screen bg-background p-8">
			<div className="max-w-4xl mx-auto">
				<h1 className="font-display text-5xl text-primary-900 mb-2 text-center">
					Create Your Hero
				</h1>
				<p className="text-center text-muted-foreground mb-8 font-body">
					Forge your legend in the Mistral Realms
				</p>

				{/* Step Indicator */}
				<div className="flex justify-center mb-8">
					<div className="flex items-center gap-4">
						<div className={`flex items-center gap-2 ${currentStep === 1 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep === 1 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								1
							</div>
							<span>Basic Info</span>
						</div>
						<div className="w-12 h-0.5 bg-muted" />
						<div className={`flex items-center gap-2 ${currentStep === 2 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep === 2 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								2
							</div>
							<span>Skills</span>
						</div>
						<div className="w-12 h-0.5 bg-muted" />
						<div className={`flex items-center gap-2 ${currentStep === 3 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep === 3 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								3
							</div>
							<span>Background</span>
						</div>
						<div className="w-12 h-0.5 bg-muted" />
						<div className={`flex items-center gap-2 ${currentStep === 4 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep === 4 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								4
							</div>
							<span>Personality</span>
						</div>
						<div className="w-12 h-0.5 bg-muted" />
						<div className={`flex items-center gap-2 ${currentStep === 6 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep === 6 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								5
							</div>
							<span>Motivation</span>
						</div>
						<div className="w-12 h-0.5 bg-muted" />
						<div className={`flex items-center gap-2 ${currentStep === 5 ? 'text-primary-600 font-bold' : 'text-muted-foreground'}`}>
							<div className={`w-8 h-8 rounded-full flex items-center justify-center ${currentStep === 5 ? 'bg-primary-600 text-white' : 'bg-muted'}`}>
								6
							</div>
							<span>Spells</span>
						</div>
					</div>
				</div>

				{/* Step 1: Basic Character Info & Ability Scores */}
				{currentStep === 1 && (
					<form onSubmit={handleSubmit}>
						<div className="grid gap-6 md:grid-cols-2">
							{/* Basic Info */}
							<Card>
								<CardHeader>
									<CardTitle className="font-display">Character Details</CardTitle>
									<CardDescription>The essentials of your hero</CardDescription>
								</CardHeader>
								<CardContent className="space-y-4">
									<div className="space-y-2">
										<Label htmlFor="name">Character Name</Label>
										<Input
											id="name"
											value={name}
											onChange={(e) => {
												setName(e.target.value);
												if (nameError) setNameError('');
											}}
											placeholder="Enter your character's name"
											className={nameError ? 'border-red-500 focus:ring-red-500' : ''}
											required
										/>
										{nameError && (
											<p className="text-sm text-red-500">{nameError}</p>
										)}
									</div>

									<div className="space-y-2">
										<Label htmlFor="race">Race</Label>
										<Select value={selectedRace} onValueChange={setSelectedRace} required>
											<SelectTrigger id="race">
												<SelectValue placeholder="Select a race" />
											</SelectTrigger>
											<SelectContent>
												{DND_RACES.map((race) => (
													<SelectItem key={race} value={race.toLowerCase()}>
														{race}
													</SelectItem>
												))}
											</SelectContent>
										</Select>
									</div>

									<div className="space-y-2">
										<Label htmlFor="class">Class</Label>
										<Select value={selectedClass} onValueChange={setSelectedClass} required>
											<SelectTrigger id="class">
												<SelectValue placeholder="Select a class" />
											</SelectTrigger>
											<SelectContent>
												{DND_CLASSES.map((cls) => (
													<SelectItem key={cls.id} value={cls.id}>
														{cls.name} (d{cls.hitDie})
													</SelectItem>
												))}
											</SelectContent>
										</Select>
									</div>

									<div className="space-y-2">
										<Label htmlFor="level">Level</Label>
										<Input
											id="level"
											type="number"
											value={level}
											onChange={(e) => setLevel(parseInt(e.target.value) || 1)}
											min="1"
											max="20"
										/>
									</div>
								</CardContent>
							</Card>

							{/* Ability Scores */}
							<Card>
								<CardHeader>
									<CardTitle className="font-display">Ability Scores (Point Buy)</CardTitle>
									<CardDescription>
										{POINT_BUY_MAX - calculatePointsSpent()} of {POINT_BUY_MAX} points remaining
										<span className="block text-xs mt-1">Scores range from 8 to 15 (before racial modifiers)</span>
									</CardDescription>
								</CardHeader>
								<CardContent>
									<div className="grid grid-cols-2 gap-4">
										{Object.entries(abilities).map(([ability, score]) => (
											<div key={ability} className="space-y-2">
												<Label htmlFor={ability} className="capitalize">
													{ability}
												</Label>
												<div className="flex gap-2 items-center">
													<Input
														id={ability}
														type="number"
														value={score}
														onChange={(e) => handleAbilityChange(ability as keyof AbilityScores, e.target.value)}
														min="8"
														max="15"
														className="w-16"
													/>
													<span className="text-sm text-muted-foreground font-mono w-12">
														{calculateModifier(score) >= 0 ? '+' : ''}{calculateModifier(score)}
													</span>
												</div>
											</div>
										))}
									</div>
								</CardContent>
							</Card>
						</div>

						{/* Character Preview */}
						<Card className="mt-6">
							<CardHeader>
								<CardTitle className="font-display">Character Preview</CardTitle>
							</CardHeader>
							<CardContent>
								<div className="flex items-center justify-between">
									<div>
										<p className="text-lg font-body">
											<span className="font-semibold">{name || 'Unnamed Hero'}</span>
											{selectedRace && selectedClass && (
												<span className="text-muted-foreground">
													{' '}- Level {level} {selectedRace.charAt(0).toUpperCase() + selectedRace.slice(1)} {DND_CLASSES.find(c => c.id === selectedClass)?.name}
												</span>
											)}
										</p>
										{selectedClass && (
											<p className="text-sm text-muted-foreground mt-1">
												Hit Points: <span className="font-bold text-success-500">{calculateHP()}</span>
											</p>
										)}
									</div>
									<Button
										type="submit"
										size="lg"
										disabled={!name || !selectedClass || !selectedRace || isSubmitting}
										className="font-body min-w-45 transition-all hover:scale-105 disabled:scale-100"
									>
										{isSubmitting ? (
											<span className="flex items-center gap-2">
												<LoadingSpinner size="sm" />
												Creating...
											</span>
										) : (
											'Next: Select Skills'
										)}
									</Button>
								</div>
							</CardContent>
						</Card>
					</form>
				)}

				{/* Step 2: Skill Selection */}
				{currentStep === 2 && (
					<SkillProficiencySelection
						characterClass={selectedClass}
						race={selectedRace}
						onComplete={handleSkillsComplete}
						onBack={() => setCurrentStep(1)}
					/>
				)}

				{/* Step 3: Background Selection */}
				{currentStep === 3 && (
					<BackgroundSelection
						onComplete={handleBackgroundComplete}
						onBack={() => setCurrentStep(2)}
					/>
				)}

				{/* Step 4: Personality Selection */}
				{currentStep === 4 && (
					<PersonalitySelection
						backgroundName={backgroundName}
						onComplete={handlePersonalityComplete}
						onBack={() => setCurrentStep(3)}
					/>
				)}

				{/* Step 6: Motivation Selection */}
				{currentStep === 6 && (
					<MotivationSelection
						onComplete={handleMotivationComplete}
						onBack={() => setCurrentStep(4)}
					/>
				)}

				{/* Step 5: Spell Selection (for spellcasting classes) */}
				{currentStep === 5 && selectedClass && (
					<div>
						<SpellSelectionStep
							characterClass={selectedClass}
							level={level}
							abilityScores={{
								intelligence: abilities.intelligence,
								wisdom: abilities.wisdom,
								charisma: abilities.charisma,
							}}
							selectedSpells={selectedSpells}
							onSpellsChange={setSelectedSpells}
						/>
						<div className="flex justify-between mt-6">
							<Button onClick={() => setCurrentStep(6)} variant="outline">
								Back
							</Button>
							<Button onClick={handleSpellsComplete}>
								Complete Character Creation
							</Button>
						</div>
					</div>
				)}
			</div>
		</div>
	);
}
