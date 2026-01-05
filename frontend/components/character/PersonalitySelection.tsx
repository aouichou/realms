'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select';
import { getBackgroundPersonality } from '@/lib/personalities';
import { ArrowLeft, ArrowRight, Scroll } from 'lucide-react';
import { useEffect, useState } from 'react';

interface PersonalitySelectionProps {
	backgroundName: string;
	onComplete: (personality: {
		personality_trait: string;
		ideal: string;
		bond: string;
		flaw: string;
	}) => void;
	onBack: () => void;
}

export default function PersonalitySelection({
	backgroundName,
	onComplete,
	onBack,
}: PersonalitySelectionProps) {
	const [personalityTrait, setPersonalityTrait] = useState('');
	const [ideal, setIdeal] = useState('');
	const [bond, setBond] = useState('');
	const [flaw, setFlaw] = useState('');

	const [customTrait, setCustomTrait] = useState('');
	const [customIdeal, setCustomIdeal] = useState('');
	const [customBond, setCustomBond] = useState('');
	const [customFlaw, setCustomFlaw] = useState('');

	const [showCustomTrait, setShowCustomTrait] = useState(false);
	const [showCustomIdeal, setShowCustomIdeal] = useState(false);
	const [showCustomBond, setShowCustomBond] = useState(false);
	const [showCustomFlaw, setShowCustomFlaw] = useState(false);

	const backgroundPersonality = getBackgroundPersonality(backgroundName);

	// Reset custom inputs when switching away from custom
	useEffect(() => {
		if (personalityTrait !== 'custom') {
			setShowCustomTrait(false);
			setCustomTrait('');
		} else {
			setShowCustomTrait(true);
		}
	}, [personalityTrait]);

	useEffect(() => {
		if (ideal !== 'custom') {
			setShowCustomIdeal(false);
			setCustomIdeal('');
		} else {
			setShowCustomIdeal(true);
		}
	}, [ideal]);

	useEffect(() => {
		if (bond !== 'custom') {
			setShowCustomBond(false);
			setCustomBond('');
		} else {
			setShowCustomBond(true);
		}
	}, [bond]);

	useEffect(() => {
		if (flaw !== 'custom') {
			setShowCustomFlaw(false);
			setCustomFlaw('');
		} else {
			setShowCustomFlaw(true);
		}
	}, [flaw]);

	if (!backgroundPersonality) {
		return (
			<Card className="p-6">
				<p className="text-red-500">
					Personality data not found for background: {backgroundName}
				</p>
				<Button onClick={onBack} className="mt-4">
					Go Back
				</Button>
			</Card>
		);
	}

	const isValid = () => {
		const hasPersonalityTrait =
			personalityTrait && (personalityTrait !== 'custom' || customTrait.trim());
		const hasIdeal = ideal && (ideal !== 'custom' || customIdeal.trim());
		const hasBond = bond && (bond !== 'custom' || customBond.trim());
		const hasFlaw = flaw && (flaw !== 'custom' || customFlaw.trim());

		return hasPersonalityTrait && hasIdeal && hasBond && hasFlaw;
	};

	const handleNext = () => {
		const finalPersonality = {
			personality_trait:
				personalityTrait === 'custom' ? customTrait.trim() : personalityTrait,
			ideal: ideal === 'custom' ? customIdeal.trim() : ideal,
			bond: bond === 'custom' ? customBond.trim() : bond,
			flaw: flaw === 'custom' ? customFlaw.trim() : flaw,
		};

		onComplete(finalPersonality);
	};

	return (
		<div className="space-y-6">
			<Card className="p-6">
				<div className="flex items-center gap-2 mb-6">
					<Scroll className="h-6 w-6 text-primary" />
					<h2 className="text-2xl font-bold">Personality</h2>
				</div>

				<p className="text-muted-foreground mb-6">
					Choose or create your character's personality traits based on your{' '}
					<span className="font-semibold">{backgroundPersonality.name}</span>{' '}
					background. These define who your character is beyond their abilities.
				</p>

				<div className="space-y-6">
					{/* Personality Trait */}
					<div className="space-y-2">
						<Label htmlFor="personality-trait" className="text-base font-semibold">
							Personality Trait
						</Label>
						<p className="text-sm text-muted-foreground">
							A distinctive behavior or quirk that makes your character unique.
						</p>
						<Select value={personalityTrait} onValueChange={setPersonalityTrait}>
							<SelectTrigger id="personality-trait">
								<SelectValue placeholder="Select a personality trait..." />
							</SelectTrigger>
							<SelectContent>
								{backgroundPersonality.traits.map((trait, index) => (
									<SelectItem key={index} value={trait}>
										{trait}
									</SelectItem>
								))}
								<SelectItem value="custom">✨ Custom (write your own)</SelectItem>
							</SelectContent>
						</Select>
						{showCustomTrait && (
							<Input
								placeholder="Enter your custom personality trait..."
								value={customTrait}
								onChange={(e) => setCustomTrait(e.target.value)}
								className="mt-2"
							/>
						)}
					</div>

					{/* Ideal */}
					<div className="space-y-2">
						<Label htmlFor="ideal" className="text-base font-semibold">
							Ideal
						</Label>
						<p className="text-sm text-muted-foreground">
							A principle or belief that drives your character's decisions and actions.
						</p>
						<Select value={ideal} onValueChange={setIdeal}>
							<SelectTrigger id="ideal">
								<SelectValue placeholder="Select an ideal..." />
							</SelectTrigger>
							<SelectContent>
								{backgroundPersonality.ideals.map((idealOption, index) => (
									<SelectItem key={index} value={idealOption.text}>
										<span className="flex items-center gap-2">
											<span className="text-xs font-semibold text-primary px-1.5 py-0.5 rounded bg-primary/10">
												{idealOption.category}
											</span>
											{idealOption.text}
										</span>
									</SelectItem>
								))}
								<SelectItem value="custom">✨ Custom (write your own)</SelectItem>
							</SelectContent>
						</Select>
						{showCustomIdeal && (
							<Input
								placeholder="Enter your custom ideal..."
								value={customIdeal}
								onChange={(e) => setCustomIdeal(e.target.value)}
								className="mt-2"
							/>
						)}
					</div>

					{/* Bond */}
					<div className="space-y-2">
						<Label htmlFor="bond" className="text-base font-semibold">
							Bond
						</Label>
						<p className="text-sm text-muted-foreground">
							A connection to a person, place, or event that matters deeply to your
							character.
						</p>
						<Select value={bond} onValueChange={setBond}>
							<SelectTrigger id="bond">
								<SelectValue placeholder="Select a bond..." />
							</SelectTrigger>
							<SelectContent>
								{backgroundPersonality.bonds.map((bondOption, index) => (
									<SelectItem key={index} value={bondOption}>
										{bondOption}
									</SelectItem>
								))}
								<SelectItem value="custom">✨ Custom (write your own)</SelectItem>
							</SelectContent>
						</Select>
						{showCustomBond && (
							<Input
								placeholder="Enter your custom bond..."
								value={customBond}
								onChange={(e) => setCustomBond(e.target.value)}
								className="mt-2"
							/>
						)}
					</div>

					{/* Flaw */}
					<div className="space-y-2">
						<Label htmlFor="flaw" className="text-base font-semibold">
							Flaw
						</Label>
						<p className="text-sm text-muted-foreground">
							A weakness, fear, or vice that can be used against your character.
						</p>
						<Select value={flaw} onValueChange={setFlaw}>
							<SelectTrigger id="flaw">
								<SelectValue placeholder="Select a flaw..." />
							</SelectTrigger>
							<SelectContent>
								{backgroundPersonality.flaws.map((flawOption, index) => (
									<SelectItem key={index} value={flawOption}>
										{flawOption}
									</SelectItem>
								))}
								<SelectItem value="custom">✨ Custom (write your own)</SelectItem>
							</SelectContent>
						</Select>
						{showCustomFlaw && (
							<Input
								placeholder="Enter your custom flaw..."
								value={customFlaw}
								onChange={(e) => setCustomFlaw(e.target.value)}
								className="mt-2"
							/>
						)}
					</div>
				</div>
			</Card>

			{/* Navigation */}
			<div className="flex justify-between">
				<Button variant="outline" onClick={onBack}>
					<ArrowLeft className="h-4 w-4 mr-2" />
					Back
				</Button>
				<Button onClick={handleNext} disabled={!isValid()}>
					Next
					<ArrowRight className="h-4 w-4 ml-2" />
				</Button>
			</div>
		</div>
	);
}
