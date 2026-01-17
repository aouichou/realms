'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { apiClient } from '@/lib/api-client';
import { useTranslation } from '@/lib/hooks/useTranslation';
import { CheckCircle2, Scroll, Sword } from 'lucide-react';
import { useEffect, useState } from 'react';

interface PresetAdventure {
	id: string;
	title: string;
	description: string;
	recommended_level: number;
	setting: string;
}

interface StartAdventureModalProps {
	characterId: string;
	characterLevel: number;
	onAdventureStarted: (data: {
		session_id: string;
		quest_id: string;
		opening_narration: string;
	}) => void;
}

export function StartAdventureModal({
	characterId,
	characterLevel,
	onAdventureStarted,
}: StartAdventureModalProps) {
	const [adventures, setAdventures] = useState<PresetAdventure[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [isOpen, setIsOpen] = useState(false);
	const [selectedAdventure, setSelectedAdventure] = useState<string | null>(null);
	const { t } = useTranslation();

	useEffect(() => {
		if (isOpen) {
			loadAdventures();
		}
	}, [isOpen]);

	const loadAdventures = async () => {
		try {
			const response = await apiClient.get('/api/v1/adventures/list');
			if (response.ok) {
				const data = await response.json();
				setAdventures(data);
			}
		} catch (error) {
			console.error('Error loading adventures:', error);
		}
	};

	const startAdventure = async (adventureId: string) => {
		setIsLoading(true);
		try {
			const response = await apiClient.post('/api/v1/adventures/start-preset', {
				character_id: characterId,
				adventure_id: adventureId,
			});

			if (response.ok) {
				const data = await response.json();
				onAdventureStarted(data);
				setIsOpen(false);
			} else {
				console.error('Failed to start adventure');
			}
		} catch (error) {
			console.error('Error starting adventure:', error);
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<>
			<button
				onClick={() => setIsOpen(true)}
				className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
				     hover:bg-white/20 transition-all text-white font-body text-sm flex items-center justify-center gap-2"
			>
				<Scroll className="h-4 w-4" />
				📜 {t('game.adventure.startButton')}
			</button>

			<Dialog open={isOpen} onOpenChange={setIsOpen}>
				<DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
					<DialogHeader>
						<DialogTitle className="text-2xl">{t('game.adventure.title')}</DialogTitle>
						<DialogDescription>
							{t('game.adventure.description')}
						</DialogDescription>
					</DialogHeader>

					<div className="space-y-4 mt-4">
						{adventures.map((adventure) => (
							<Card
								key={adventure.id}
								className={`cursor-pointer transition-all relative ${selectedAdventure === adventure.id
										? 'border-primary border-2 bg-primary/5 shadow-md'
										: 'border-muted hover:border-primary/50 hover:shadow-sm'
									}`}
								onClick={() => setSelectedAdventure(adventure.id)}
							>
								{selectedAdventure === adventure.id && (
									<CheckCircle2 className="absolute top-2 right-2 h-6 w-6 text-primary" />
								)}
								<CardHeader>
									<div className="flex items-start justify-between">
										<div className="space-y-1">
											<CardTitle className="flex items-center gap-2">
												<Sword className="h-5 w-5 text-red-500" />
												{adventure.title}
											</CardTitle>
											<CardDescription className="text-sm">
												{adventure.setting}
											</CardDescription>
										</div>
										<div
											className={`px-3 py-1 rounded-full text-xs font-semibold ${adventure.recommended_level <= characterLevel
												? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100'
												: adventure.recommended_level === characterLevel + 1
													? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100'
													: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100'
												}`}
										>
											{t('game.adventure.level')} {adventure.recommended_level}
										</div>
									</div>
								</CardHeader>
								<CardContent>
									<p className="text-sm text-muted-foreground">{adventure.description}</p>
								</CardContent>
							</Card>
						))}
					</div>

					<div className="flex justify-end gap-3 mt-6">
						<Button variant="outline" onClick={() => setIsOpen(false)} disabled={isLoading}>
							{t('game.adventure.cancel')}
						</Button>
						<Button
							onClick={() => selectedAdventure && startAdventure(selectedAdventure)}
							disabled={!selectedAdventure || isLoading}
						>
							{isLoading ? t('game.adventure.starting') : t('game.adventure.beginAdventure')}
						</Button>
					</div>
				</DialogContent>
			</Dialog>
		</>
	);
}
