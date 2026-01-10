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
	const { showToast } = useToast();

	const handleSave = async () => {
		if (!saveName.trim()) {
			showToast('Please enter a name for your save', 'error');
			return;
		}

		setIsSaving(true);

		try {
			const response = await apiClient.post('/api/game/save', {
				session_id: sessionId,
				save_name: saveName,
			});

			if (!response.ok) {
				const errorText = await response.text();
				console.error('Save failed:', errorText);
				throw new Error('Failed to save game');
			}

			const data = await response.json();

			showToast(`Game saved as "${data.save_data?.save_name || saveName}"`, 'success');

			setSaveName('');
			onClose();
		} catch (error) {
			console.error('Save error:', error);
			showToast('Could not save your game. Please try again.', 'error');
		} finally {
			setIsSaving(false);
		}
	};

	return (
		<Dialog open={isOpen} onOpenChange={onClose}>
			<DialogContent className="sm:max-w-[425px]">
				<DialogHeader>
					<DialogTitle>Save Game</DialogTitle>
					<DialogDescription>
						Enter a name for your save. You can load it later from the main menu.
					</DialogDescription>
				</DialogHeader>

				<div className="grid gap-4 py-4">
					<div className="grid gap-2">
						<Label htmlFor="saveName">Save Name</Label>
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
					<Button variant="outline" onClick={onClose} disabled={isSaving}>
						Cancel
					</Button>
					<Button onClick={handleSave} disabled={isSaving}>
						{isSaving ? (
							<>
								<Loader2 className="mr-2 h-4 w-4 animate-spin" />
								Saving...
							</>
						) : (
							<>
								<Save className="mr-2 h-4 w-4" />
								Save
							</>
						)}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
