'use client';

import { SaveSlotsModal } from '@/components/SaveSlotsModal';
import { useTranslation } from '@/lib/hooks/useTranslation';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

interface Character {
	id: string;
	name: string;
	character_class: string;
	race: string;
	level: number;
	hp_current: number;
	hp_max: number;
}

export default function CharacterSelectPage() {
	const router = useRouter();
	const { t } = useTranslation();
	const [characters, setCharacters] = useState<Character[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [showLoadModal, setShowLoadModal] = useState(false);
	const [deletingId, setDeletingId] = useState<string | null>(null);

	useEffect(() => {
		fetchCharacters();
	}, []);

	const fetchCharacters = async () => {
		try {
			const token = localStorage.getItem('access_token');
			if (!token) {
				router.push('/auth/login');
				return;
			}

			const response = await fetch('http://localhost:8000/api/v1/characters', {
				headers: {
					'Authorization': `Bearer ${token}`,
				},
			});

			if (response.status === 401) {
				router.push('/auth/login');
				return;
			}

			if (!response.ok) {
				throw new Error('Failed to fetch characters');
			}

			const data = await response.json();
			setCharacters(data.characters || []);
		} catch (err) {
			setError(err instanceof Error ? err.message : 'An error occurred');
		} finally {
			setLoading(false);
		}
	};

	const selectCharacter = (characterId: string) => {
		localStorage.setItem('selected_character_id', characterId);
		router.push('/adventure');
	};

	const deleteCharacter = async (characterId: string, characterName: string) => {
		const confirmMessage = t('character.select.confirmDelete').replace('{name}', characterName);
		if (!window.confirm(confirmMessage)) {
			return;
		}

		try {
			setDeletingId(characterId);
			const token = localStorage.getItem('access_token');
			if (!token) {
				router.push('/auth/login');
				return;
			}

			const response = await fetch(`http://localhost:8000/api/v1/characters/${characterId}`, {
				method: 'DELETE',
				headers: {
					'Authorization': `Bearer ${token}`,
				},
			});

			if (response.status === 401) {
				router.push('/auth/login');
				return;
			}

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(errorText || 'Failed to delete character');
			}

			setCharacters(prev => prev.filter(character => character.id !== characterId));
		} catch (err) {
			setError(err instanceof Error ? err.message : 'Failed to delete character');
		} finally {
			setDeletingId(null);
		}
	};

	if (loading) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-linear-to-br from-primary-900 via-secondary-600 to-primary-900">
				<div className="text-center">
					<div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-accent-400 mx-auto mb-4"></div>
					<p className="text-accent-200">{t('character.select.loading')}</p>
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-linear-to-br from-primary-900 via-secondary-600 to-primary-900">
				<div className="text-center max-w-md">
					<p className="text-error-500 mb-4">{error}</p>
					<button
						onClick={() => fetchCharacters()}
						className="px-6 py-2 bg-accent-600 text-primary-900 rounded-lg hover:bg-accent-400 font-body font-semibold"
					>
						{t('character.select.retry')}
					</button>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen bg-linear-to-br from-primary-900 via-secondary-600 to-primary-900 p-4 md:p-8">
			<div className="max-w-6xl mx-auto">
				<div className="mb-8 flex items-center justify-between">
					<div>
						<h1 className="text-4xl font-display text-primary-900 mb-2">{t('character.select.title')}</h1>
						<p className="text-neutral-500 font-body">{t('character.select.subtitle')}</p>
					</div>
					<button
						onClick={() => setShowLoadModal(true)}
						className="inline-flex items-center gap-2 px-6 py-3 border-2 border-accent-600 bg-accent-600/10 text-accent-200 rounded-lg hover:bg-accent-600 hover:text-primary-900 transition-all font-body font-semibold"
					>
						<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
						</svg>
						<span>{t('character.select.loadGame')}</span>
					</button>
				</div>

				{characters.length === 0 ? (
					<div className="text-center py-16">
						<p className="text-accent-200/70 mb-6 font-body">{t('character.select.noCharacters')}</p>
						<Link
							href="/character/create"
							className="inline-flex items-center gap-2 px-8 py-4 bg-accent-600 text-primary-900 rounded-lg hover:bg-accent-400 transition-all hover:scale-105 font-body font-semibold"
						>
							<span>{t('character.select.createFirst')}</span>
							<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
							</svg>
						</Link>
					</div>
				) : (
					<>
						<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
							{characters.map((character) => (
								<div
									key={character.id}
									onClick={() => selectCharacter(character.id)}
									className="bg-accent-200/10 backdrop-blur-sm border-2 border-accent-600/30 rounded-lg p-6 cursor-pointer transition-all hover:border-accent-600 hover:bg-accent-200/20 hover:shadow-lg hover:scale-105"
								>
									<div className="flex items-center justify-between mb-4">
										<div>
											<h3 className="text-2xl font-display text-accent-200">{character.name}</h3>
										</div>
										<div className="flex items-center gap-2">
											<span className="text-sm font-body text-accent-400 bg-accent-600/20 px-3 py-1 rounded-full font-semibold">
												{t('character.select.level')} {character.level}
											</span>
											<button
												onClick={(event) => {
													event.stopPropagation();
													void deleteCharacter(character.id, character.name);
												}}
												className="inline-flex items-center justify-center w-8 h-8 rounded-full border border-red-200 text-red-600 hover:bg-red-50"
												disabled={deletingId === character.id}
												title={t('character.select.delete') || 'Delete character'}
											>
												{deletingId === character.id ? (
													<span className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-red-600"></span>
												) : (
													<span>🗑️</span>
												)}
											</button>
										</div>
									</div>
									<div className="space-y-2 font-body text-sm">
										<p className="text-neutral-700">
											<span className="font-semibold">{t('character.select.race')}:</span> {character.race}
										</p>
										<p className="text-neutral-700">
											<span className="font-semibold">{t('character.select.class')}:</span> {character.character_class}
										</p>
										<div className="flex items-center gap-2 text-neutral-700">
											<span className="font-semibold">{t('character.select.hp')}:</span>										<div className="flex-1 bg-neutral-200 rounded-full h-2">
												<div
													className="bg-red-500 h-2 rounded-full transition-all"
													style={{ width: `${(character.hp_current / character.hp_max) * 100}%` }} />
											</div>
											<span className="text-xs">
												{character.hp_current}/{character.hp_max}
											</span>
										</div>
									</div>
								</div>
							))}
						</div>

						<div className="text-center">
							<Link
								href="/character/create"
								className="inline-flex items-center gap-2 px-6 py-3 border-2 border-primary-900 text-primary-900 rounded-lg hover:bg-primary-900 hover:text-white transition-all font-body font-semibold"
							>
								<span>{t('character.select.createNew')}</span>
								<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
								</svg>
							</Link>
						</div>
					</>
				)}

				<SaveSlotsModal
					isOpen={showLoadModal}
					onClose={() => setShowLoadModal(false)}
				/>
			</div>
		</div>
	);
}
