// SaveGameModal.tsx
'use client';

import { Button } from '@/components/ui/button';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/toast';
import { apiClient } from '@/lib/api-client';
import { useTranslation } from '@/lib/hooks/useTranslation';
import { Loader2, Save } from 'lucide-react';
import { useState } from 'react';

interface SaveGameModalProps {
	isOpen: boolean;
	onClose: () => void;
	sessionId: string;
	characterName: string;
}

export function SaveGameModal({
	isOpen,
	onClose,
	sessionId,
	characterName,
}: SaveGameModalProps) {
	const [saveName, setSaveName] = useState('');
	const [isSaving, setIsSaving] = useState(false);
	const [showOverwriteConfirm, setShowOverwriteConfirm] = useState(false);
	const { showToast } = useToast();
	const { t } = useTranslation();

	const performSave = async (overwrite: boolean = false) => {
		setIsSaving(true);

		try {
			const response = await apiClient.post('/api/v1/game/save', {
				session_id: sessionId,
				save_name: saveName,
				overwrite,
			});

			if (!response.ok) {
				// Handle 409 Conflict (duplicate name)
				if (response.status === 409 && !overwrite) {
					setShowOverwriteConfirm(true);
					return;
				}

				const errorText = await response.text();
				console.error('Save failed:', errorText);

				// Parse error
				let errorData;
				try {
					errorData = JSON.parse(errorText);
				} catch (e) {
					errorData = { detail: errorText };
				}

				if (errorData.detail && typeof errorData.detail === 'string') {
					showToast(errorData.detail, 'error');
				} else {
					showToast(t('game.save.errorFailedToSave'), 'error');
				}
				return;
			}

			const data = await response.json();

			showToast(
				t('game.save.successSaved').replace(
					'{saveName}',
					data.save_data?.save_name || saveName
				),
				'success'
			);

			setSaveName('');
			setShowOverwriteConfirm(false);
			onClose();
		} catch (error) {
			console.error('Save error:', error);
			showToast(t('game.save.errorGeneric'), 'error');
		} finally {
			setIsSaving(false);
		}
	};

	const handleSave = async () => {
		if (!saveName.trim()) {
			showToast(t('game.save.errorEmptyName'), 'error');
			return;
		}

		await performSave(false);
	};

	const handleOverwrite = async () => {
		await performSave(true);
	};

	const handleClose = () => {
		setShowOverwriteConfirm(false);
		setSaveName('');
		onClose();
	};

	return (
		<Dialog open={isOpen} onOpenChange={handleClose}>
			<DialogContent className="sm:max-w-106.25">
				<DialogHeader>
					<DialogTitle>{t('game.save.title')}</DialogTitle>
					<DialogDescription>
						{showOverwriteConfirm
							? t('game.save.overwriteConfirm').replace('{saveName}', saveName)
							: t('game.save.description')}
					</DialogDescription>
				</DialogHeader>

				{!showOverwriteConfirm ? (
					<>
						<div className="grid gap-4 py-4">
							<div className="grid gap-2">
								<Label htmlFor="saveName">{t('game.save.saveName')}</Label>
								<Input
									id="saveName"
									placeholder={`${characterName} - ${new Date().toLocaleDateString()}`}
									value={saveName}
									onChange={(e) => setSaveName(e.target.value)}
									onKeyDown={(e) => {
										if (e.key === 'Enter' && !isSaving) {
											handleSave();
										}
									}}
									disabled={isSaving}
								/>
							</div>
						</div>

						<DialogFooter>
							<Button variant="outline" onClick={handleClose} disabled={isSaving}>
								{t('game.save.cancel')}
							</Button>
							<Button onClick={handleSave} disabled={isSaving}>
								{isSaving ? (
									<>
										<Loader2 className="mr-2 h-4 w-4 animate-spin" />
										{t('game.save.saving')}
									</>
								) : (
									<>
										<Save className="mr-2 h-4 w-4" />
										{t('game.save.save')}
									</>
								)}
							</Button>
						</DialogFooter>
					</>
				) : (
					<>
						<div className="py-4">
							<p className="text-sm text-muted-foreground">
								{t('game.save.overwriteWarning')}
							</p>
						</div>

						<DialogFooter>
							<Button variant="outline" onClick={() => setShowOverwriteConfirm(false)} disabled={isSaving}>
								{t('game.save.cancel')}
							</Button>
							<Button variant="destructive" onClick={handleOverwrite} disabled={isSaving}>
								{isSaving ? (
									<>
										<Loader2 className="mr-2 h-4 w-4 animate-spin" />
										{t('game.save.saving')}
									</>
								) : (
									<>
										<Save className="mr-2 h-4 w-4" />
										{t('game.save.overwrite')}
									</>
								)}
							</Button>
						</DialogFooter>
					</>
				)}
			</DialogContent>
		</Dialog>
	);
}
