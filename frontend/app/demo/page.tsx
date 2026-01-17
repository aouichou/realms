"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useToast } from "@/components/ui/toast";
import { apiClient } from "@/lib/api-client";
import { authService } from "@/lib/auth";
import { useTranslation } from "@/lib/hooks/useTranslation";
import { Sparkles, User, Zap } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

/**
 * Demo Mode Landing Page
 *
 * Fast-track for recruiters/demo users:
 * - Instant gameplay with pre-built character
 * - Direct to Goblin Ambush adventure
 * - Option to customize after trying demo
 */
export default function DemoPage() {
	const router = useRouter();
	const { showToast } = useToast();
	const { t } = useTranslation();
	const [isStarting, setIsStarting] = useState(false);

	const startInstantDemo = async () => {
		setIsStarting(true);
		try {
			// 1. Create guest account
			const { user } = await authService.createGuest();

			// 2. Create demo character (pre-configured)
			const characterResponse = await apiClient.post('/api/v1/characters', {
				name: "Demo Hero",
				character_class: "fighter",
				race: "human",
				level: 2,
				hp_max: 20,
				hp_current: 20,
				ability_scores: {
					strength: 16,
					dexterity: 14,
					constitution: 15,
					intelligence: 10,
					wisdom: 12,
					charisma: 11,
				},
				background: "soldier",
				personality_traits: "I'm brave and ready for adventure!",
				motivation: "Protect the innocent from danger",
			});

			if (!characterResponse.ok) {
				throw new Error("Failed to create demo character");
			}

			const character = await characterResponse.json();

			// 3. Start Goblin Ambush adventure automatically
			const adventureResponse = await apiClient.post('/api/v1/adventures/start-preset', {
				character_id: character.id,
				adventure_id: "goblin_ambush",
			});

			if (!adventureResponse.ok) {
				throw new Error("Failed to start adventure");
			}

			const adventureData = await adventureResponse.json();

			// 4. Redirect to game with adventure started
			showToast("Welcome to Mistral Realms! Your adventure begins...", "success");
			router.push(`/game/${character.id}?session=${adventureData.session_id}&demo=true`);
		} catch (error) {
			console.error("Error starting demo:", error);
			showToast("Failed to start demo. Please try again.", "error");
			setIsStarting(false);
		}
	};

	const createCustomCharacter = async () => {
		setIsStarting(true);
		try {
			// Create guest account and go to character creation
			await authService.createGuest();
			showToast(t("demo.welcomeCreate"), "success");
			router.push('/character/create');
		} catch (error) {
			console.error("Error creating guest:", error);
			showToast("Failed to start. Please try again.", "error");
			setIsStarting(false);
		}
	};

	return (
		<div className="min-h-screen bg-linear-to-b from-neutral-900 via-neutral-800 to-neutral-900 flex items-center justify-center p-4">
			<div className="max-w-4xl w-full">
				{/* Header */}
				<div className="text-center mb-12">
					<h1 className="font-display text-6xl text-primary-100 mb-4 animate-fadeIn">
					{t("demo.title")}
				</h1>
				<p className="text-xl text-neutral-300 font-body animate-fadeIn animation-delay-200">
					{t("demo.subtitle")}
					</p>
					<p className="text-neutral-400 mt-2 animate-fadeIn animation-delay-300">
						No signup required • Start playing immediately
					</p>
				</div>

				{/* Demo Options */}
				<div className="grid md:grid-cols-2 gap-6">
					{/* Instant Demo Card */}
					<Card className="border-2 border-primary-500 bg-linear-to-br from-primary-950 to-neutral-900 shadow-2xl hover:shadow-primary-500/20 transition-all hover:scale-105">
						<CardHeader>
							<CardTitle className="flex items-center gap-2 text-2xl text-primary-100">
								<Zap className="h-6 w-6 text-amber-400" />
								Instant Demo
							</CardTitle>
							<CardDescription className="text-neutral-300 text-base">
								Jump right into the action!
							</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="bg-neutral-800/50 p-4 rounded-lg border border-neutral-700">
								<h3 className="font-semibold text-primary-200 mb-2">What you'll get:</h3>
								<ul className="space-y-2 text-sm text-neutral-300">
									<li className="flex items-start gap-2">
										<span className="text-green-400 mt-0.5">✓</span>
									<span>{t("demo.quickStart.prebuiltCharacter")}</span>
									</li>
									<li className="flex items-start gap-2">
										<span className="text-green-400 mt-0.5">✓</span>
										<span>Goblin Ambush adventure (15-20 min)</span>
									</li>
									<li className="flex items-start gap-2">
										<span className="text-green-400 mt-0.5">✓</span>
										<span>Full AI Dungeon Master experience</span>
									</li>
									<li className="flex items-start gap-2">
										<span className="text-green-400 mt-0.5">✓</span>
										<span>Combat, dice rolls, inventory</span>
									</li>
									<li className="flex items-start gap-2">
										<span className="text-green-400 mt-0.5">✓</span>
										<span>Can save progress anytime</span>
									</li>
								</ul>
							</div>

							<Button
								size="lg"
								className="w-full bg-linear-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-bold shadow-lg"
								onClick={startInstantDemo}
								disabled={isStarting}
							>
								{isStarting ? (
									<LoadingSpinner />
								) : (
									<>
										<Zap className="mr-2 h-5 w-5" />
										Start Playing Now (30 seconds)
									</>
								)}
							</Button>

							<p className="text-xs text-center text-neutral-400">
								Perfect for recruiters • No commitment
							</p>
						</CardContent>
					</Card>

					{/* Custom Character Card */}
					<Card className="bg-linear-to-br from-neutral-800 to-neutral-900 shadow-xl hover:shadow-neutral-700/20 transition-all hover:scale-105">
						<CardHeader>
							<CardTitle className="flex items-center gap-2 text-2xl text-neutral-100">
								<User className="h-6 w-6 text-blue-400" />
								Create Your Hero
							</CardTitle>
							<CardDescription className="text-neutral-400 text-base">
								Build your own character
							</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="bg-neutral-800/50 p-4 rounded-lg border border-neutral-700">
								<h3 className="font-semibold text-neutral-200 mb-2">What you'll do:</h3>
								<ul className="space-y-2 text-sm text-neutral-300">
									<li className="flex items-start gap-2">
										<span className="text-blue-400 mt-0.5">→</span>
										<span>Choose race & class (6 steps)</span>
									</li>
									<li className="flex items-start gap-2">
										<span className="text-blue-400 mt-0.5">→</span>
										<span>Customize abilities & skills</span>
									</li>
									<li className="flex items-start gap-2">
										<span className="text-blue-400 mt-0.5">→</span>
										<span>Pick background & personality</span>
									</li>
									<li className="flex items-start gap-2">
										<span className="text-blue-400 mt-0.5">→</span>
										<span>Select spells (if spellcaster)</span>
									</li>
									<li className="flex items-start gap-2">
										<span className="text-blue-400 mt-0.5">→</span>
										<span>Choose preset OR custom adventure</span>
									</li>
								</ul>
							</div>

							<Button
								size="lg"
								variant="outline"
								className="w-full border-2 border-neutral-600 hover:border-blue-400 hover:bg-blue-950"
								onClick={createCustomCharacter}
								disabled={isStarting}
							>
								{isStarting ? (
									<LoadingSpinner />
								) : (
									<>
										<User className="mr-2 h-5 w-5" />
										Create Character (5 min)
									</>
								)}
							</Button>

							<p className="text-xs text-center text-neutral-400">
								Full customization • Still no signup
							</p>
						</CardContent>
					</Card>
				</div>

				{/* AI Feature Highlight */}
				<Card className="mt-8 bg-linear-to-r from-purple-950 to-indigo-950 border-purple-500/30">
					<CardContent className="flex items-center gap-4 p-6">
						<Sparkles className="h-12 w-12 text-purple-400 shrink-0" />
						<div>
							<h3 className="font-semibold text-lg text-purple-100 mb-1">
								✨ Try AI-Generated Custom Adventures
							</h3>
							<p className="text-sm text-purple-200">
								After playing the demo, create your own character and use our <strong>AI Adventure Wizard</strong> to
								generate unique custom stories. Answer 3 questions and get a complete adventure with NPCs,
								encounters, and loot tailored to your choices!
							</p>
						</div>
					</CardContent>
				</Card>

				{/* Footer */}
				<div className="text-center mt-8 text-neutral-500 text-sm">
					<p>
						All progress is saved automatically.{" "}
						<span className="text-neutral-400">You can claim your account with email later.</span>
					</p>
					<p className="mt-2">
						Already have an account?{" "}
						<button
							onClick={() => router.push('/auth/login')}
							className="text-primary-400 hover:text-primary-300 underline"
						>
							Login here
						</button>
					</p>
				</div>
			</div>
		</div>
	);
}
