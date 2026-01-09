'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api-client';
import Image from 'next/image';
import { useParams, useSearchParams } from 'next/navigation';
import { lazy, useEffect, useRef, useState } from 'react';

// Lazy load heavy components for better initial load
const AbilityCheckPanel = lazy(() => import('@/components/AbilityCheckPanel').then(mod => ({ default: mod.AbilityCheckPanel })));
const ActiveEffectsDisplay = lazy(() => import('@/components/ActiveEffectsDisplay').then(mod => ({ default: mod.ActiveEffectsDisplay })));
const CombatTracker = lazy(() => import('@/components/CombatTracker').then(mod => ({ default: mod.CombatTracker })));
const CompanionPanel = lazy(() => import('@/components/CompanionPanel').then(mod => ({ default: mod.CompanionPanel })));
const EnhancedCharacterSheet = lazy(() => import('@/components/EnhancedCharacterSheet').then(mod => ({ default: mod.EnhancedCharacterSheet })));
const ImageGalleryPanel = lazy(() => import('@/components/ImageGalleryPanel').then(mod => ({ default: mod.ImageGalleryPanel })));
const InventoryPanel = lazy(() => import('@/components/InventoryPanel').then(mod => ({ default: mod.InventoryPanel })));
const QuestCompleteModal = lazy(() => import('@/components/QuestCompleteModal').then(mod => ({ default: mod.QuestCompleteModal })));
const SceneImage = lazy(() => import('@/components/SceneImage').then(mod => ({ default: mod.SceneImage })));
const SpellsPanel = lazy(() => import('@/components/SpellsPanel').then(mod => ({ default: mod.SpellsPanel })));
const SpellSlotsDisplay = lazy(() => import('@/components/SpellSlotsDisplay').then(mod => ({ default: mod.SpellSlotsDisplay })));
const SaveGameButton = lazy(() => import('@/components/SaveGameButton').then(mod => ({ default: mod.SaveGameButton })));
const SaveSlotsModal = lazy(() => import('@/components/SaveSlotsModal').then(mod => ({ default: mod.SaveSlotsModal })));

interface Message {
	id: number;
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
	scene_image_url?: string;
	quest_complete_id?: string;
	roll_request?: {
		type: string;
		ability?: string;
		skill?: string;
		dc?: number;
		dice?: string;
		target?: string;
		reason?: string;
	};
}

interface Character {
	id: number;
	name: string;
	character_class: string;
	race: string;
	level: number;
	hp_current: number;
	hp_max: number;
	strength: number;
	dexterity: number;
	constitution: number;
	intelligence: number;
	wisdom: number;
	charisma: number;
}

type PanelType = 'stats' | 'inventory' | 'dice' | 'combat' | 'spells' | 'checks' | 'companion' | 'images' | null;

export default function GamePage() {
	const params = useParams();
	const searchParams = useSearchParams();
	const characterId = params.characterId as string;
	const sessionIdFromUrl = searchParams.get('session');

	const [messages, setMessages] = useState<Message[]>([]);
	const [character, setCharacter] = useState<Character | null>(null);
	const [sessionId, setSessionId] = useState<string | null>(null);
	const [inputValue, setInputValue] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const [openPanel, setOpenPanel] = useState<PanelType>(null);
	const [diceNotation, setDiceNotation] = useState('1d20');
	const [lastDiceResult, setLastDiceResult] = useState<any>(null);
	const [pendingRollRequest, setPendingRollRequest] = useState<Message['roll_request'] | null>(null);
	const [questCompleteData, setQuestCompleteData] = useState<{ questId: string; title: string; rewards: any } | null>(null);
	const [showQuestCompleteModal, setShowQuestCompleteModal] = useState(false);
	const [isStartingSession, setIsStartingSession] = useState(false);

	const messagesEndRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		loadCharacter();
	}, [characterId]);

	useEffect(() => {
		// If session ID is provided in URL, use it directly
		if (sessionIdFromUrl) {
			setSessionId(sessionIdFromUrl);
		} else if (character && !sessionId) {
			// Otherwise create a new session
			getOrCreateSession();
		}
	}, [character, sessionIdFromUrl]);

	useEffect(() => {
		if (sessionId) {
			loadConversationHistory();
		}
	}, [sessionId]);

	useEffect(() => {
		scrollToBottom();
	}, [messages]);

	// Auto-save every 5 minutes
	useEffect(() => {
		if (!sessionId) return;

		const autoSaveInterval = setInterval(async () => {
			try {
				await apiClient.post('/api/game/save', {
					session_id: sessionId,
					save_name: `Auto-save ${new Date().toLocaleTimeString()}`,
				});
				console.log('Auto-saved game');
			} catch (error) {
				console.error('Auto-save failed:', error);
			}
		}, 5 * 60 * 1000); // 5 minutes

		return () => clearInterval(autoSaveInterval);
	}, [sessionId]);

	const scrollToBottom = () => {
		messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
	};

	const loadCharacter = async () => {
		try {
			const response = await apiClient.get(`/api/characters/${characterId}`);
			if (response.ok) {
				const data = await response.json();
				setCharacter(data);
			}
		} catch (error) {
			console.error('Error loading character:', error);
		}
	};

	const getOrCreateSession = async () => {
		try {
			// For now, create a new session every time
			// TODO: Implement logic to get active session or create new one
			const response = await apiClient.post('/api/sessions', {
				character_id: characterId,
				companion_id: null,
				current_location: 'Starting Village',
			});

			if (response.ok) {
				const data = await response.json();
				setSessionId(data.id);
			} else {
				console.error('Error creating session:', await response.text());
			}
		} catch (error) {
			console.error('Error getting/creating session:', error);
		}
	};

	const loadConversationHistory = async () => {
		if (!sessionId) return;

		try {
			const response = await apiClient.get(`/api/conversations/${sessionId}`);
			if (response.ok) {
				const data = await response.json();
				setMessages(data.messages || []);
			}
		} catch (error) {
			console.error('Error loading conversation history:', error);
		}
	};

	const sendMessage = async (e: React.FormEvent, rollResult?: any) => {
		e.preventDefault();
		if (!inputValue.trim() || isLoading) return;

		const userMessage = inputValue.trim();
		setInputValue('');
		setIsLoading(true);

		// Add user message immediately
		const tempUserMsg: Message = {
			id: Date.now(),
			role: 'user',
			content: userMessage,
			timestamp: new Date().toISOString(),
		};
		setMessages(prev => [...prev, tempUserMsg]);

		try {
			const response = await apiClient.post('/api/conversations/action', {
				character_id: characterId,
				session_id: sessionId,
				action: userMessage,
				roll_result: rollResult || null,
			});

			if (response.ok) {
				const data = await response.json();
				const dmMessage: Message = {
					id: Date.now() + 1,
					role: 'assistant',
					content: data.response,
					timestamp: new Date().toISOString(),
					scene_image_url: data.scene_image_url,
					roll_request: data.roll_request,
					quest_complete_id: data.quest_complete_id,
				};
				setMessages(prev => [...prev, dmMessage]);

				// Store pending roll request if DM asks for a roll
				if (data.roll_request) {
					setPendingRollRequest(data.roll_request);
				} else if (rollResult) {
					// Clear pending request after sending result
					setPendingRollRequest(null);
				}

				// Handle quest completion
				if (data.quest_complete_id) {
					// Fetch quest details
					try {
						const questResponse = await apiClient.get(`/api/quests/${data.quest_complete_id}`);
						if (questResponse.ok) {
							const questData = await questResponse.json();
							setQuestCompleteData({
								questId: data.quest_complete_id,
								title: questData.title,
								rewards: questData.rewards,
							});
							setShowQuestCompleteModal(true);
						}
					} catch (error) {
						console.error('Error fetching quest details:', error);
					}
				}
			}
		} catch (error) {
			console.error('Error sending message:', error);
		} finally {
			setIsLoading(false);
		}
	};

	const handleRollComplete = async (rollResult: any) => {
		if (!pendingRollRequest) return;

		// Auto-send roll result to DM
		const rollMessage = `I rolled a ${rollResult.total} (${rollResult.roll} + ${rollResult.modifier}) for ${rollResult.skill || rollResult.ability}${rollResult.success !== undefined ? ` and ${rollResult.success ? 'succeeded' : 'failed'}` : ''}`;

		setInputValue(rollMessage);
		setIsLoading(true);

		// Add user message immediately
		const tempUserMsg: Message = {
			id: Date.now(),
			role: 'user',
			content: rollMessage,
			timestamp: new Date().toISOString(),
		};
		setMessages(prev => [...prev, tempUserMsg]);

		try {
			const response = await apiClient.post('/api/conversations/action', {
				character_id: characterId,
				session_id: sessionId,
				action: rollMessage,
				roll_result: rollResult,
			});

			if (response.ok) {
				const data = await response.json();
				const dmMessage: Message = {
					id: Date.now() + 1,
					role: 'assistant',
					content: data.response,
					timestamp: new Date().toISOString(),
					scene_image_url: data.scene_image_url,
					roll_request: data.roll_request,
				};
				setMessages(prev => [...prev, dmMessage]);

				// Clear pending request after result sent
				setPendingRollRequest(null);
				setInputValue('');

				// Store new roll request if DM asks for another
				if (data.roll_request) {
					setPendingRollRequest(data.roll_request);
				}
			}
		} catch (error) {
			console.error('Error sending roll result:', error);
		} finally {
			setIsLoading(false);
		}
	};

	const rollDice = async () => {
		try {
			const response = await apiClient.post('/api/dice/roll', { dice: diceNotation });

			if (response.ok) {
				const result = await response.json();
				setLastDiceResult(result);
			}
		} catch (error) {
			console.error('Error rolling dice:', error);
		}
	};

	const claimQuestRewards = async () => {
		if (!questCompleteData) return;

		try {
			const response = await apiClient.post(
				`/api/quests/${questCompleteData.questId}/complete`,
				{
					character_id: parseInt(characterId),
				}
			);

			if (response.ok) {
				// Reload character to update XP, gold, etc.
				await loadCharacter();
			}
		} catch (error) {
			console.error('Error claiming quest rewards:', error);
			throw error;
		}
	};

	const handleAdventureStarted = (data: { session_id: string; quest_id: string; opening_narration: string }) => {
		// Update session
		setSessionId(data.session_id);

		// Add DM message with opening narration
		const dmMessage: Message = {
			id: Date.now(),
			role: 'assistant',
			content: data.opening_narration,
			timestamp: new Date().toISOString(),
		};
		setMessages([dmMessage]);

		// Reload character and conversation history
		loadCharacter();
		loadConversationHistory();
	};

	const startSession = async () => {
		if (!sessionId || isStartingSession) return;

		setIsStartingSession(true);
		try {
			// Check if this is a new session (no messages yet)
			if (messages.length === 0) {
				// This is the first time - trigger the initial DM message
				const response = await apiClient.post('/api/conversations/start', {
					session_id: sessionId,
				});

				if (response.ok) {
					const data = await response.json();
					const dmMessage: Message = {
						id: Date.now(),
						role: 'assistant',
						content: data.opening_narration || data.response,
						timestamp: new Date().toISOString(),
					};
					setMessages([dmMessage]);
				}
			} else {
				// Continuing an existing session - ask DM for summary
				const response = await apiClient.post('/api/conversations/action', {
					character_id: characterId,
					session_id: sessionId,
					action: 'Please give me a brief summary of what happened so far and ask if I want to continue.',
				});

				if (response.ok) {
					const data = await response.json();
					const dmMessage: Message = {
						id: Date.now(),
						role: 'assistant',
						content: data.response,
						timestamp: new Date().toISOString(),
					};
					setMessages(prev => [...prev, dmMessage]);
				}
			}
		} catch (error) {
			console.error('Error starting session:', error);
		} finally {
			setIsStartingSession(false);
		}
	};

	const calculateModifier = (score: number): number => {
		return Math.floor((score - 10) / 2);
	};

	const togglePanel = (panel: PanelType) => {
		setOpenPanel(openPanel === panel ? null : panel);
	};

	const latestSceneImage = [...messages].reverse().find(m => m.scene_image_url)?.scene_image_url;

	return (
		<div className="relative h-screen w-screen overflow-hidden bg-neutral-900">
			{/* Scene Background Image */}
			{latestSceneImage && (
				<div className="absolute inset-0 z-0">
					<Image
						src={latestSceneImage}
						alt="Current scene"
						fill
						className="object-cover opacity-60"
						priority
					/>
				</div>
			)}

			{/* Main Layout */}
			<div className="relative z-10 h-full flex flex-col md:flex-row">
				{/* Mobile Menu Button */}
				<button
					onClick={() => setOpenPanel(openPanel ? null : 'stats')}
					className="md:hidden fixed top-4 left-4 z-50 p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20 hover:bg-white/20 transition-all text-white"
					aria-label="Toggle menu"
				>
					<svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
					</svg>
				</button>

				{/* Left Sidebar - Collapsible Panels */}
				<div className={`
          fixed md:relative inset-y-0 left-0 z-40
          w-64 p-4 space-y-3 bg-neutral-900 md:bg-transparent
          transform transition-transform duration-300 ease-in-out
          ${openPanel ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          overflow-y-auto
        `}>
					{/* Stats Button */}
					<button
						onClick={() => togglePanel('stats')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						⚔️ Character Stats
					</button>

					{/* Inventory Button */}
					<button
						onClick={() => togglePanel('inventory')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						🎒 Inventory
					</button>

					{/* Dice Button */}
					<button
						onClick={() => togglePanel('dice')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						🎲 Dice Roller
					</button>

					{/* Combat Button */}
					<button
						onClick={() => togglePanel('combat')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						⚔️ Combat
					</button>

					<button
						onClick={() => togglePanel('spells')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						✨ Spells
					</button>

					<button
						onClick={() => togglePanel('checks')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						🎲 Checks
					</button>

					{/* Companion Button */}
					<button
						onClick={() => togglePanel('companion')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						🤖 AI Companion
					</button>

					{/* Image Gallery Button */}
					<button
						onClick={() => togglePanel('images')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						🖼️ Scene Gallery
					</button>

					{/* Save Game Button */}
					{sessionId && character && (
						<div className="pt-2 border-t border-white/10">
							<SaveGameButton
								sessionId={sessionId}
								characterName={character.name}
							/>
						</div>
					)}
				</div>

				{/* Center - Messages Area */}
				<div className="flex-1 flex flex-col p-4 md:p-6 overflow-hidden">
					{/* Character Header */}
					{character && (
						<div className="mb-4 pb-4 border-b border-white/10">
							<h1 className="font-display text-xl md:text-2xl text-white">
								{character.name}
							</h1>
							<p className="text-xs md:text-sm text-white/80 font-body">
								Level {character.level} {character.race} {character.character_class}
							</p>
						</div>
					)}

					{/* Messages */}
					<div className="flex-1 overflow-y-auto space-y-3 md:space-y-4 mb-3 md:mb-4">
						{messages.length === 0 && sessionId && (
							<div className="flex items-center justify-center h-full">
								<div className="text-center space-y-4">
									<div className="text-6xl mb-4">🎲</div>
									<h2 className="text-2xl font-display text-white mb-2">
										Ready to Begin?
									</h2>
									<p className="text-white/70 font-body mb-6 max-w-md">
										Your adventure awaits! Click the button below to start your journey with the AI Dungeon Master.
									</p>
									<Button
										onClick={startSession}
										disabled={isStartingSession}
										size="lg"
										className="bg-accent-400 hover:bg-accent-500 text-primary-900 font-display text-lg px-8 py-6"
									>
										{isStartingSession ? 'Starting...' : 'Start Session'}
									</Button>
								</div>
							</div>
						)}
						{messages.map((message) => (
							<div
								key={message.id}
								className={`p-3 md:p-4 rounded-lg backdrop-blur-md ${message.role === 'user'
									? 'bg-accent-400/20 border border-accent-400/30 ml-6 md:ml-12'
									: 'bg-white/10 border border-white/20 mr-6 md:mr-12'
									}`}
							>
								<div className="flex items-center gap-2 mb-2">
									<span className="font-display text-sm text-white">
										{message.role === 'user' ? 'You' : 'Dungeon Master'}
									</span>
									{message.role === 'assistant' && (
										<span className="text-xs font-body font-bold uppercase tracking-wide
                                   bg-accent-400 text-primary-900 px-2 py-0.5 rounded">
											AI
										</span>
									)}
								</div>

								{/* Scene Image (if present) */}
								{message.scene_image_url && message.role === 'assistant' && (
									<SceneImage imageUrl={message.scene_image_url} alt="Scene illustration" />
								)}

								<p className="text-narrative text-white font-body leading-relaxed whitespace-pre-line">
									{message.content}
								</p>
							</div>
						))}
						<div ref={messagesEndRef} />
					</div>

					{/* Input */}
					{pendingRollRequest && (
						<div className="mb-3 p-3 bg-accent-400/20 border border-accent-400/30 rounded-lg backdrop-blur-md">
							<div className="flex items-start gap-2">
								<span className="text-xl">🎲</span>
								<div className="flex-1">
									<p className="text-sm font-body text-white font-semibold mb-1">
										The DM requests a roll:
									</p>
									<p className="text-sm font-body text-white/90">
										{pendingRollRequest.type === 'ability' && (
											<>
												{pendingRollRequest.ability}
												{pendingRollRequest.skill && ` (${pendingRollRequest.skill})`}
												{pendingRollRequest.dc && ` check (DC ${pendingRollRequest.dc})`}
											</>
										)}
										{pendingRollRequest.type === 'save' && (
											<>
												{pendingRollRequest.ability} saving throw
												{pendingRollRequest.dc && ` (DC ${pendingRollRequest.dc})`}
											</>
										)}
										{pendingRollRequest.type === 'attack' && (
											<>Attack roll {pendingRollRequest.target && `against ${pendingRollRequest.target}`}</>
										)}
										{pendingRollRequest.type === 'custom' && (
											<>{pendingRollRequest.dice} {pendingRollRequest.reason && `- ${pendingRollRequest.reason}`}</>
										)}
									</p>
									{pendingRollRequest.reason && pendingRollRequest.type !== 'custom' && (
										<p className="text-xs font-body text-white/70 mt-1">
											{pendingRollRequest.reason}
										</p>
									)}
								</div>
								<Button
									variant="outline"
									size="sm"
									onClick={() => setOpenPanel(pendingRollRequest.type === 'ability' || pendingRollRequest.type === 'save' ? 'checks' : 'dice')}
									className="border-accent-400/30 text-accent-400 hover:bg-accent-400/20 font-body"
								>
									Roll Now
								</Button>
							</div>
						</div>
					)}
					<form onSubmit={sendMessage} className="flex gap-2">
						<Input
							value={inputValue}
							onChange={(e) => setInputValue(e.target.value)}
							placeholder="Describe your action..."
							disabled={isLoading}
							className="flex-1 bg-white/10 backdrop-blur-md border-white/20 text-white
                       placeholder:text-white/50 font-body"
						/>
						<Button
							type="submit"
							disabled={isLoading}
							className="font-body"
						>
							{isLoading ? 'Sending...' : 'Send'}
						</Button>
					</form>
				</div>

				{/* Right Panel - Expanded Content */}
				{openPanel && (
					<div className={`p-6 bg-white/10 backdrop-blur-xl border-l border-white/20 overflow-y-auto ${openPanel === 'stats' || openPanel === 'inventory' || openPanel === 'combat' || openPanel === 'spells' || openPanel === 'checks' || openPanel === 'companion' ? 'w-200' : 'w-96'
						}`}>
						<div className="flex items-center justify-between mb-6">
							<h2 className="font-display text-xl text-white">
								{openPanel === 'stats' && '⚔️ Character Stats'}
								{openPanel === 'inventory' && '🎒 Inventory'}
								{openPanel === 'dice' && '🎲 Dice Roller'}
								{openPanel === 'combat' && '⚔️ Combat'}
								{openPanel === 'spells' && '✨ Spells'}
								{openPanel === 'checks' && '🎲 Ability Checks'}
								{openPanel === 'companion' && '🤖 AI Companion'}
								{openPanel === 'images' && '🖼️ Scene Gallery'}
							</h2>
							<button
								onClick={() => setOpenPanel(null)}
								className="text-white/60 hover:text-white text-2xl"
							>
								×
							</button>
						</div>

						{/* Stats Panel */}
						{openPanel === 'stats' && character && (
							<div className="space-y-4 bg-neutral-900 rounded-lg p-4">
								<EnhancedCharacterSheet
									characterId={characterId}
									characterName={character.name}
									characterClass={character.character_class}
									level={character.level}
								/>

								{/* Spell Slots Display */}
								<SpellSlotsDisplay
									characterId={characterId}
									characterName={character.name}
								/>

								{/* Active Effects Display */}
								{sessionId && (
									<ActiveEffectsDisplay
										characterId={characterId}
										sessionId={sessionId}
									/>
								)}

								{/* Inventory Panel */}
								{openPanel === 'inventory' && (
									<div className="bg-neutral-900 rounded-lg">
										<InventoryPanel characterId={characterId} />
									</div>
								)}

								{/* Combat Panel */}
								{openPanel === 'combat' && sessionId && (
									<div className="bg-neutral-900 rounded-lg">
										<CombatTracker
											sessionId={sessionId}
											characterId={characterId}
											onCombatEnd={() => {
												// Refresh character stats after combat
												loadCharacter();
											}}
										/>
									</div>
								)}

								{/* Spells Panel */}
								{openPanel === 'spells' && (
									<div className="space-y-4 bg-neutral-900 rounded-lg p-4">
										<SpellsPanel characterId={characterId} />

										{/* Spell Slots Display */}
										<SpellSlotsDisplay
											characterId={characterId}
											characterName={character?.name}
										/>

										{/* Ability Checks Panel */}
										{openPanel === 'checks' && (
											<div className="bg-neutral-900 rounded-lg">
												<AbilityCheckPanel
													characterId={characterId}
													onRollComplete={handleRollComplete}
												/>
											</div>
										)}
										{/* Companion Panel */}
										{openPanel === 'companion' && character && (
											<div className="bg-neutral-900 rounded-lg h-150">
												<CompanionPanel
													characterId={characterId}
													gameContext={{
														player_hp: character.hp_current,
														player_max_hp: character.hp_max,
														in_combat: false,
														location: sessionId ? 'Adventure' : 'Village',
														situation: messages.length > 0 ? messages[messages.length - 1].content : 'Ready for adventure',
													}}
													onSpeechGenerated={(speech) => {
														console.log('Companion says:', speech);
													}}
												/>
											</div>
										)}

										{/* Image Gallery Panel */}
										{openPanel === 'images' && (
											<div className="bg-neutral-900 rounded-lg h-full">
												<ImageGalleryPanel
													images={messages
														.filter(m => m.scene_image_url)
														.map(m => ({
															url: m.scene_image_url!,
															timestamp: m.timestamp,
															caption: m.content.substring(0, 100),
														}))
													}
												/>
											</div>
										)}

										{/* Dice Panel */}
										{openPanel === 'dice' && (
											<div className="space-y-4">
												<div className="space-y-2">
													<label className="text-sm text-white/80 font-body">Dice Notation</label>
													<Input
														value={diceNotation}
														onChange={(e) => setDiceNotation(e.target.value)}
														placeholder="e.g., 1d20, 2d6+3"
														className="bg-white/5 border-white/10 text-white font-mono"
													/>
												</div>

												<div className="grid grid-cols-3 gap-2">
													{['1d4', '1d6', '1d8', '1d10', '1d12', '1d20'].map((notation) => (
														<Button
															key={notation}
															variant="outline"
															onClick={() => {
																setDiceNotation(notation);
																setLastDiceResult(null);
															}}
															className="font-mono border-white/20 text-neutral-900 hover:bg-white/10 hover:text-white"
														>
															{notation}
														</Button>
													))}
												</div>

												<Button
													onClick={rollDice}
													className="w-full font-body"
													size="lg"
												>
													Roll Dice
												</Button>

												{lastDiceResult && (
													<Card className="bg-accent-400/20 border-accent-400/30">
														<CardContent className="p-4">
															<div className="text-center">
																<p className="text-sm text-white/80 font-body mb-2">
																	{lastDiceResult.notation}
																</p>
																<p className="text-4xl font-bold text-accent-400 font-display mb-2">
																	{lastDiceResult.total}
																</p>
																{lastDiceResult.individual_rolls && (
																	<p className="text-xs text-white/60 font-mono">
																		Rolls: {lastDiceResult.individual_rolls.map((r: any) => r.roll).join(', ')}
																		{lastDiceResult.modifier !== 0 && ` (${lastDiceResult.modifier >= 0 ? '+' : ''}${lastDiceResult.modifier})`}
																	</p>
																)}
															</div>
														</CardContent>
													</Card>
												)}
											</div>
										)}
									</div>
								)}
							</div>

			{/* Quest Complete Modal */}
						{questCompleteData && (
							<QuestCompleteModal
								isOpen={showQuestCompleteModal}
								questTitle={questCompleteData.title}
								rewards={questCompleteData.rewards}
								onClose={() => setShowQuestCompleteModal(false)}
								onClaimRewards={claimQuestRewards}
							/>
						)}
					</div>
				);
}
