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
import { Loader2, Play, Save } from 'lucide-react';
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
	const { showToast } = useToast();
	const router = useRouter();

	useEffect(() => {
		if (isOpen) {
			loadSaves();
		}
	}, [isOpen]);

	const loadSaves = async () => {
		setIsLoading(true);
		try {
			const response = await fetch('/api/game/saves', {
				credentials: 'include',
			});

			if (!response.ok) {
				throw new Error('Failed to load saves');
			}

			const data = await response.json();
			setSaves(data);
		} catch (error) {
			console.error('Load saves error:', error);
			showToast('Could not load save files', 'error');
		} finally {
			setIsLoading(false);
		}
	};

	const handleLoad = async (sessionId: string, saveName: string) => {
		setLoadingSessionId(sessionId);

		try {
			const response = await fetch(`/api/game/load/${sessionId}`, {
				method: 'POST',
				credentials: 'include',
			});

			if (!response.ok) {
				throw new Error('Failed to load game');
			}

			showToast(`Loading "${saveName}"...`, 'info');

			// Navigate to game page
			router.push(`/game?session_id=${sessionId}`);
			onClose();
		} catch (error) {
			console.error('Load error:', error);
			showToast('Could not load saved game', 'error');
			setLoadingSessionId(null);
		}
	};

	const formatDate = (timestamp: string) => {
		const date = new Date(timestamp);
		return date.toLocaleString();
	};

	return (
		<Dialog open={isOpen} onOpenChange={onClose}>
			<DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
				<DialogHeader>
					<DialogTitle>Load Game</DialogTitle>
					<DialogDescription>
						Select a save to continue your adventure
					</DialogDescription>
				</DialogHeader>

				{isLoading ? (
					<div className="flex items-center justify-center py-12">
						<Loader2 className="w-8 h-8 animate-spin text-primary" />
					</div>
				) : saves.length === 0 ? (
					<div className="text-center py-12">
						<Save className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
						<p className="text-muted-foreground">No saved games found</p>
						<p className="text-sm text-muted-foreground mt-2">
							Start a new adventure to create your first save
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
										<Button
											size="sm"
											onClick={() => handleLoad(save.session_id, save.save_name)}
											disabled={loadingSessionId !== null}
										>
											{loadingSessionId === save.session_id ? (
												<>
													<Loader2 className="mr-2 h-4 w-4 animate-spin" />
													Loading...
												</>
											) : (
												<>
													<Play className="mr-2 h-4 w-4" />
													Load
												</>
											)}
										</Button>
									</div>
								</CardHeader>
								{save.game_data?.location && (
									<CardContent className="pt-0">
										<p className="text-sm text-muted-foreground">
											Location: {save.game_data.location}
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
