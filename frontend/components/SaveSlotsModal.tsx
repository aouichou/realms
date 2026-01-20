// SaveSlotsModal.tsx
'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from '@/components/ui/dialog';
import { useToast } from '@/components/ui/toast';
import { apiFetch } from '@/lib/api-client';
import { useTranslation } from '@/lib/hooks/useTranslation';
import { Loader2, Play, Save, Trash2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

interface SaveData {
	save_name: string;
	session_id: string;
	character_id: string;
	character_name: string;
	timestamp: string;
	game_data: {
		location: string;
		story_progress: Record<string, any>;
	};
}

interface SaveSlotsModalProps {
	isOpen: boolean;
	onClose: () => void;
}

export function SaveSlotsModal({ isOpen, onClose }: SaveSlotsModalProps) {
	const [saves, setSaves] = useState<SaveData[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
	const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
	const { showToast } = useToast();
	const router = useRouter();
	const { t } = useTranslation();

	useEffect(() => {
		if (isOpen) {
			loadSaves();
		}
	}, [isOpen]);

	const loadSaves = async () => {
		setIsLoading(true);
		try {
			const response = await apiFetch('/api/v1/game/saves');

			if (!response.ok) {
				throw new Error('Failed to load saves');
			}

			const data = await response.json();
			setSaves(data);
		} catch (error) {
			console.error('Load saves error:', error);
			showToast(t('game.load.errorLoadSaves'), 'error');
		} finally {
			setIsLoading(false);
		}
	};

	const handleLoad = async (sessionId: string, saveName: string, characterId: string) => {
		setLoadingSessionId(sessionId);

		try {
			const response = await apiFetch(`/api/v1/game/load/${sessionId}`);

			if (!response.ok) {
				throw new Error('Failed to load game');
			}

			showToast(t('game.load.loadingMessage').replace('{saveName}', saveName), 'info');

			// Navigate to game page
			router.push(`/game/${characterId}?session=${sessionId}`);
			onClose();
		} catch (error) {
			console.error('Load error:', error);
			showToast(t('game.load.errorLoadGame'), 'error');
			setLoadingSessionId(null);
		}
	};

	const handleDelete = async (sessionId: string, saveName: string) => {
		if (!confirm(`Are you sure you want to delete "${saveName}"? This action cannot be undone.`)) {
			return;
		}

		setDeletingSessionId(sessionId);

		try {
			const response = await apiFetch(`/api/v1/game/save/${sessionId}`, {
				method: 'DELETE',
			});

			if (!response.ok) {
				throw new Error('Failed to delete save');
			}

			showToast('Save deleted successfully', 'success');
			// Reload saves list
			await loadSaves();
		} catch (error) {
			console.error('Delete error:', error);
			showToast('Failed to delete save', 'error');
		} finally {
			setDeletingSessionId(null);
		}
	};

	const formatDate = (timestamp: string) => {
		const date = new Date(timestamp);
		return date.toLocaleString();
	};

	return (
		<Dialog open={isOpen} onOpenChange={onClose}>
			<DialogContent className="sm:max-w-175 max-h-[80vh] overflow-y-auto">
				<DialogHeader>
					<DialogTitle>{t('game.load.title')}</DialogTitle>
					<DialogDescription>
						{t('game.load.description')}
					</DialogDescription>
				</DialogHeader>

				{isLoading ? (
					<div className="flex items-center justify-center py-12">
						<Loader2 className="w-8 h-8 animate-spin text-primary" />
					</div>
				) : saves.length === 0 ? (
					<div className="text-center py-12">
						<Save className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
						<p className="text-muted-foreground">{t('game.load.noSaves')}</p>
						<p className="text-sm text-muted-foreground mt-2">
							{t('game.load.noSavesHint')}
						</p>
					</div>
				) : (
					<div className="grid gap-4 py-4">
						{saves.map((save) => (
							<Card key={save.session_id} className="hover:border-primary transition-colors">
								<CardHeader className="pb-3">
									<div className="flex items-start justify-between">
										<div>
											<CardTitle className="text-lg">{save.save_name}</CardTitle>
											<CardDescription>
												{save.character_name} • {formatDate(save.timestamp)}
											</CardDescription>
										</div>
										<div className="flex gap-2">
											<Button
												variant="outline"
												size="sm"
												onClick={() => handleDelete(save.session_id, save.save_name)}
												disabled={loadingSessionId !== null || deletingSessionId !== null}
												title="Delete save"
											>
												{deletingSessionId === save.session_id ? (
													<Loader2 className="h-4 w-4 animate-spin" />
												) : (
													<Trash2 className="h-4 w-4" />
												)}
											</Button>
											<Button
												size="sm"
												onClick={() => handleLoad(save.session_id, save.save_name, save.character_id)}
												disabled={loadingSessionId !== null || deletingSessionId !== null}
											>
												{loadingSessionId === save.session_id ? (
													<>
														<Loader2 className="mr-2 h-4 w-4 animate-spin" />
														{t('game.load.loading')}
													</>
												) : (
													<>
														<Play className="mr-2 h-4 w-4" />
														{t('game.load.loadButton')}
													</>
												)}
											</Button>
										</div>
									</div>
								</CardHeader>
								{save.game_data?.location && (
									<CardContent className="pt-0">
										<p className="text-sm text-muted-foreground">
											{t('game.load.location')}: {save.game_data.location}
										</p>
									</CardContent>
								)}
							</Card>
						))}
					</div>
				)}
			</DialogContent>
		</Dialog>
	);
}
