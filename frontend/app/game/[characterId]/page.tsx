'use client';

import { ChatMessage } from '@/components/ChatMessage';
import { SpellWarningContainer } from '@/components/SpellWarningContainer';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api-client';
import { useTranslation } from '@/lib/hooks/useTranslation';
import Image from 'next/image';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { lazy, useEffect, useRef, useState } from 'react';

// Lazy load heavy components for better initial load
const AbilityCheckPanel = lazy(() => import('@/components/AbilityCheckPanel').then(mod => ({ default: mod.AbilityCheckPanel })));
const ActiveEffectsDisplay = lazy(() => import('@/components/ActiveEffectsDisplay').then(mod => ({ default: mod.ActiveEffectsDisplay })));
const CompanionListPanel = lazy(() => import('@/components/CompanionListPanel').then(mod => ({ default: mod.CompanionListPanel })));
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
	role: 'user' | 'assistant' | 'companion';
	content: string;
	timestamp: string;
	scene_image_url?: string;
	quest_complete_id?: string;
	warnings?: string[];
	companion_id?: string;
	companion_name?: string;
	companion_data?: {
		id: number;
		name: string;
		creature_name: string;
		relationship_status: string;
		loyalty: number;
		hp: number;
		max_hp: number;
		ac: number;
		avatar_url?: string;
		personality: string;
	};
	tool_calls_made?: Array<{
		name: string;
		arguments: Record<string, any>;
		result: Record<string, any>;
	}>;
	character_updates?: {
		hp?: {
			old: number;
			new: number;
			change: number;
		};
		spell_slots?: {
			level: number;
			remaining: number;
		};
	};
	roll_request?: {
		type: string;
		ability?: string;
		skill?: string;
		dc?: number;
		dice?: string;
		advantage?: boolean;
		disadvantage?: boolean;
		description?: string;
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
	gold: number;
	silver: number;
	copper: number;
	spell_slots?: Record<string, { max: number; remaining: number }>;
}

type PanelType = 'stats' | 'inventory' | 'dice' | 'spells' | 'checks' | 'companion' | 'images' | null;

const ABILITY_ABBREVIATIONS: Record<string, string> = {
	str: 'strength',
	dex: 'dexterity',
	con: 'constitution',
	int: 'intelligence',
	wis: 'wisdom',
	cha: 'charisma',
};

const formatSkillLabel = (skill?: string) => {
	if (!skill) return undefined;
	return skill.replace(/[_-]/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
};

export default function GamePage() {
	const params = useParams();
	const router = useRouter();
	const { t } = useTranslation();
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
	const [companionCount, setCompanionCount] = useState<number>(0);
	/**
	 * Current roll request being processed by the player.
	 * When null, no roll is pending.
	 */
	const [pendingRollRequest, setPendingRollRequest] = useState<Message['roll_request'] | null>(null);

	/**
	 * Queue of roll requests from the DM that need to be processed sequentially.
	 * The DM can request multiple rolls in one response (e.g., "Make a Stealth check and a Perception check").
	 * This queue ensures rolls are processed one at a time:
	 * 1. First roll is shown to player for input
	 * 2. After player submits result, queue advances to next roll
	 * 3. Queue clears when all rolls are complete
	 *
	 * Example flow:
	 * - DM: "Roll Stealth (DC 15) and Perception (DC 12)"
	 * - Queue: [stealth_roll, perception_roll]
	 * - Player rolls stealth → queue: [perception_roll]
	 * - Player rolls perception → queue: []
	 */
	const [pendingRollQueue, setPendingRollQueue] = useState<Message['roll_request'][]>([]);
	const [questCompleteData, setQuestCompleteData] = useState<{ questId: string; title: string; rewards: any } | null>(null);
	const [showQuestCompleteModal, setShowQuestCompleteModal] = useState(false);
	const [isStartingSession, setIsStartingSession] = useState(false);
	const [spellWarnings, setSpellWarnings] = useState<Array<{ id: string; message: string; type: 'warning' | 'suggestion' | 'error' }>>([]);

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
				await apiClient.post('/api/v1/game/save', {
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
			const response = await apiClient.get(`/api/v1/characters/${characterId}`);
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
			const response = await apiClient.post('/api/v1/sessions', {
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
			const response = await apiClient.get(`/api/v1/conversations/${sessionId}`);
			if (response.ok) {
				const data = await response.json();
				// Map messages to ensure proper field types and timestamp conversion
				const loadedMessages = (data.messages || []).map((msg: any) => ({
					...msg,
					timestamp: msg.created_at || msg.timestamp,
				}));
				setMessages(loadedMessages);
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
			const response = await apiClient.post('/api/v1/conversations/action', {
				character_id: characterId,
				session_id: sessionId,
				action: userMessage,
				roll_result: rollResult || null,
			});

			if (response.ok) {
				const data = await response.json();

				// RL-129: Handle character updates from tool calls
				if (data.character_updates) {
					setCharacter((prev) => {
						if (!prev) return prev;
						const updated = { ...prev };

						// Update HP if changed
						if (data.character_updates.hp) {
							updated.hp_current = data.character_updates.hp.new;
						}

						// Update spell slots if changed
						if (data.character_updates.spell_slots) {
							const { level, remaining } = data.character_updates.spell_slots;
							if (updated.spell_slots) {
								updated.spell_slots[`level_${level}`] = {
									...updated.spell_slots[`level_${level}`],
									remaining,
								};
							}
						}

						return updated;
					});
				}

				// Handle spell warnings
				if (data.warnings && data.warnings.length > 0) {
					const newWarnings = data.warnings.map((msg: string) => {
						const type = msg.includes('Did you mean') ? 'suggestion' :
							msg.includes('⚠️') ? 'warning' :
								msg.includes("don't know") ? 'error' : 'warning';
						return {
							id: `${Date.now()}-${Math.random()}`,
							message: msg,
							type,
						};
					});
					setSpellWarnings(prev => [...prev, ...newWarnings]);
				}

				const dmMessage: Message = {
					id: Date.now() + 1,
					role: 'assistant',
					content: data.response,
					timestamp: new Date().toISOString(),
					scene_image_url: data.scene_image_url,
					roll_request: data.roll_request,
					quest_complete_id: data.quest_complete_id,
					warnings: data.warnings,
					tool_calls_made: data.tool_calls_made,
					character_updates: data.character_updates,
				};
				setMessages(prev => [...prev, dmMessage]);

				// RL-131: Add companion responses after DM message
				if (data.companion_responses && data.companion_responses.length > 0) {
					const companionMessages: Message[] = data.companion_responses.map((comp: any, idx: number) => ({
						id: Date.now() + 2 + idx,
						role: 'companion' as const,
						content: comp.message,
						timestamp: new Date().toISOString(),
						companion_id: comp.companion_id,
						companion_name: comp.companion_name,
						companion_data: {
							id: typeof comp.companion_id === 'string' ? parseInt(comp.companion_id) : comp.companion_id,
							name: comp.companion_name,
							creature_name: comp.creature_name || 'Companion',
							relationship_status: comp.relationship_status,
							loyalty: comp.loyalty,
							hp: comp.hp || 0,
							max_hp: comp.max_hp || 0,
							ac: comp.ac || 10,
							avatar_url: comp.avatar_url,
							personality: comp.personality || 'Loyal companion',
						},
					}));
					setMessages(prev => [...prev, ...companionMessages]);
				}

				// Handle roll requests: clear any pending, then set new ones if requested
				if (data.roll_requests && data.roll_requests.length > 0) {
					setPendingRollQueue(data.roll_requests);
					setPendingRollRequest(data.roll_requests[0]);
				} else if (data.roll_request) {
					setPendingRollQueue([]);
					setPendingRollRequest(data.roll_request);
				} else {
					// No roll request in response, clear any pending
					setPendingRollQueue([]);
					setPendingRollRequest(null);
				}

				// Handle quest completion
				if (data.quest_complete_id) {
					// Fetch quest details
					try {
						const questResponse = await apiClient.get(`/api/v1/quests/${data.quest_complete_id}`);
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

	const buildDiceRollResult = (rollType: string, result: any) => {
		const rolls = Array.isArray(result.individual_rolls)
			? result.individual_rolls.filter((r: any) => !r.dropped).map((r: any) => r.roll)
			: [];
		const rollTotal = rolls.reduce((sum: number, value: number) => sum + value, 0);

		return {
			type: rollType,
			total: result.total,
			roll: rolls.length > 0 ? rollTotal : result.total - (result.modifier || 0),
			modifier: result.modifier || 0,
			rolls,
		};
	};

	const executeSaveRoll = async () => {
		if (!pendingRollRequest?.ability) return;

		const abilityKey = pendingRollRequest.ability.toLowerCase();
		const ability = ABILITY_ABBREVIATIONS[abilityKey] || abilityKey;

		try {
			const response = await apiClient.post('/api/v1/dice/check', {
				character_id: characterId,
				ability,
				skill: null,
				dc: pendingRollRequest.dc || null,
				advantage: pendingRollRequest.advantage || false,
				disadvantage: pendingRollRequest.disadvantage || false,
				reason: pendingRollRequest.description || null,
			});

			if (response.ok) {
				const data = await response.json();
				await handleRollComplete({
					type: 'save',
					ability,
					total: data.total,
					roll: data.roll,
					modifier: data.ability_modifier,
					success: data.success,
					dc: data.dc,
				});
			}
		} catch (error) {
			console.error('Error rolling save:', error);
		}
	};

	const handleRollComplete = async (rollResult: any) => {
		if (!pendingRollRequest) return;

		// Auto-send roll result to DM
		const rollTarget = rollResult.skill || rollResult.ability || pendingRollRequest.description || pendingRollRequest.type;
		// Only show success/failure if DC was provided and success is explicitly true or false (not null)
		const successText = rollResult.success !== null && rollResult.success !== undefined
			? ` and ${rollResult.success ? 'succeeded' : 'failed'}`
			: '';
		const rollMessage = `I rolled a ${rollResult.total} (${rollResult.roll} + ${rollResult.modifier}) for ${rollTarget}${successText}`;

		setInputValue(rollMessage);
		setIsLoading(true);

		// Clear the roll request card immediately after rolling
		if (pendingRollQueue.length > 1) {
			const [, ...remaining] = pendingRollQueue;
			setPendingRollQueue(remaining);
			setPendingRollRequest(remaining[0] || null);
		} else {
			setPendingRollQueue([]);
			setPendingRollRequest(null);
		}

		// Add user message immediately
		const tempUserMsg: Message = {
			id: Date.now(),
			role: 'user',
			content: rollMessage,
			timestamp: new Date().toISOString(),
		};
		setMessages(prev => [...prev, tempUserMsg]);

		try {
			const response = await apiClient.post('/api/v1/conversations/action', {
				character_id: characterId,
				session_id: sessionId,
				action: rollMessage,
				roll_result: rollResult,
			});

			if (response.ok) {
				const data = await response.json();

				// Handle spell warnings
				if (data.warnings && data.warnings.length > 0) {
					const newWarnings = data.warnings.map((msg: string) => {
						const type = msg.includes('Did you mean') ? 'suggestion' :
							msg.includes('⚠️') ? 'warning' :
								msg.includes("don't know") ? 'error' : 'warning';
						return {
							id: `${Date.now()}-${Math.random()}`,
							message: msg,
							type,
						};
					});
					setSpellWarnings(prev => [...prev, ...newWarnings]);
				}

				const dmMessage: Message = {
					id: Date.now() + 1,
					role: 'assistant',
					content: data.response,
					timestamp: new Date().toISOString(),
					scene_image_url: data.scene_image_url,
					roll_request: data.roll_request,
					warnings: data.warnings,
				};
				setMessages(prev => [...prev, dmMessage]);

				setInputValue('');

				// Always clear the previous roll request first
				setPendingRollRequest(null);
				setPendingRollQueue([]);

				// Store new roll request(s) if DM asks for another
				if (data.roll_requests && data.roll_requests.length > 0) {
					setPendingRollQueue(data.roll_requests);
					setPendingRollRequest(data.roll_requests[0]);
				} else if (data.roll_request) {
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
			const notation = pendingRollRequest?.dice || diceNotation;
			const rollType = pendingRollRequest?.advantage
				? 'advantage'
				: pendingRollRequest?.disadvantage
					? 'disadvantage'
					: 'normal';

			const response = await apiClient.post('/api/v1/dice/roll', {
				dice: notation,
				roll_type: rollType,
				reason: pendingRollRequest?.description || null,
			});

			if (response.ok) {
				const result = await response.json();
				setLastDiceResult(result);

				if (pendingRollRequest) {
					await handleRollComplete(buildDiceRollResult(pendingRollRequest.type, result));
				}
			}
		} catch (error) {
			console.error('Error rolling dice:', error);
		}
	};

	const claimQuestRewards = async () => {
		if (!questCompleteData) return;

		try {
			const response = await apiClient.post(
				`/api/v1/quests/${questCompleteData.questId}/complete`,
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
				const response = await apiClient.post('/api/v1/conversations/start', {
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
				const response = await apiClient.post('/api/v1/conversations/action', {
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
			{/* Spell Warnings Overlay */}
			<SpellWarningContainer
				warnings={spellWarnings}
				onWarningDismissed={(id: string) => {
					setSpellWarnings(prev => prev.filter(w => w.id !== id));
				}}
			/>

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
						{t('game.panels.stats')}
					</button>

					{/* Inventory Button */}
					<button
						onClick={() => togglePanel('inventory')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						{t('game.panels.inventory')}
					</button>

					{/* Dice Button */}
					<button
						onClick={() => togglePanel('dice')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						{t('game.panels.dice')}
					</button>

					{/* Spells Button */}
					<button
						onClick={() => togglePanel('spells')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						{t('game.panels.spells')}
					</button>

					{/* Checks Button */}
					<button
						onClick={() => togglePanel('checks')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						{t('game.panels.checks')}
					</button>

					{/* Companion Button - Only show if companions exist */}
					{companionCount > 0 && (
						<button
							onClick={() => togglePanel('companion')}
							className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
						>
							{t('game.panels.companion')}
						</button>
					)}

					{/* Image Gallery Button */}
					<button
						onClick={() => togglePanel('images')}
						className="w-full p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/20
                     hover:bg-white/20 transition-all text-white font-body text-sm"
					>
						{t('game.panels.images')}
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
						<div className="mb-4 pb-4 border-b border-white/10 flex items-center justify-between">
							<div className="flex-1">
								<h1 className="font-display text-xl md:text-2xl text-white">
									{character.name}
								</h1>
								<p className="text-xs md:text-sm text-white/80 font-body">
									Level {character.level} {character.race} {character.character_class}
								</p>
								<div className="flex gap-3 mt-2 text-xs text-white/70">
									<span className="flex items-center gap-1">
										<span className="text-yellow-400">🪙</span>
										{character.gold || 0}gp
									</span>
									<span className="flex items-center gap-1">
										<span className="text-gray-300">⚪</span>
										{character.silver || 0}sp
									</span>
									<span className="flex items-center gap-1">
										<span className="text-orange-400">🟤</span>
										{character.copper || 0}cp
									</span>
								</div>
							</div>
						</div>
					)}

					{/* Messages or Start Screen */}
					{messages.length === 0 ? (
						<div className="flex-1 flex items-center justify-center">
							<div className="text-center max-w-md">
								<div className="text-6xl mb-4">🎲</div>
								<h2 className="text-2xl font-display text-white mb-2">
									{t('game.startScreen.title')}
								</h2>
								<p className="text-white/70 font-body mb-6">
									{t('game.startScreen.description')}
								</p>
								<Button
									onClick={startSession}
									disabled={isStartingSession}
									size="lg"
									className="bg-accent-400 hover:bg-accent-500 text-primary-900 font-display text-lg px-8 py-6"
								>
									{isStartingSession ? t('game.startScreen.starting') : t('game.startScreen.startButton')}
								</Button>
							</div>
						</div>
					) : (
						<div className="flex-1 overflow-y-auto space-y-3 mb-4">
							{messages.map((message) => (
								<ChatMessage key={message.id} message={message} enableTypewriter={true} />
							))}
							{/* Show "DM is thinking..." message while loading */}
							{isLoading && (
								<div className="p-3 md:p-4 rounded-lg backdrop-blur-md bg-white/10 border border-white/20 mr-6 md:mr-12">
									<div className="flex items-center gap-2 mb-2">
										<span className="font-display text-sm text-white">Dungeon Master</span>
										<span className="text-xs font-body font-bold tracking-wide bg-accent-400 text-primary-900 px-2 py-0.5 rounded">
											AI
										</span>
									</div>
									<div className="text-narrative text-white/80 font-body leading-relaxed flex items-center gap-2">
										<span className="italic">
											{t('game.dmThinking')}
										</span>
										<span className="inline-flex gap-1">
											<span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
											<span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
											<span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
										</span>
									</div>
								</div>
							)}
							<div ref={messagesEndRef} />
						</div>
					)}

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
										{(pendingRollRequest.type === 'check' || pendingRollRequest.type === 'ability') && (
											<>
												{pendingRollRequest.ability}
												{formatSkillLabel(pendingRollRequest.skill) && ` (${formatSkillLabel(pendingRollRequest.skill)})`}
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
											<>Attack roll {pendingRollRequest.dice || 'd20'}</>
										)}
										{pendingRollRequest.type === 'initiative' && (
											<>Initiative roll</>
										)}
										{pendingRollRequest.type === 'custom' && (
											<>{pendingRollRequest.dice} {pendingRollRequest.reason && `- ${pendingRollRequest.reason}`}</>
										)}
									</p>
									{pendingRollRequest.description && (
										<p className="text-xs font-body text-white/70 mt-1">
											{pendingRollRequest.description}
										</p>
									)}
								</div>
								<Button
									variant="outline"
									size="sm"
									onClick={() => {
										if (pendingRollRequest.type === 'check' || pendingRollRequest.type === 'ability') {
											setOpenPanel('checks');
											return;
										}

										if (pendingRollRequest.type === 'save') {
											void executeSaveRoll();
											return;
										}

										if (pendingRollRequest.dice) {
											setDiceNotation(pendingRollRequest.dice);
										}
										setOpenPanel('dice');
									}}
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
				{
					openPanel && (
						<div className={`p-6 bg-white/10 backdrop-blur-xl border-l border-white/20 overflow-y-auto ${openPanel === 'stats' || openPanel === 'inventory' || openPanel === 'spells' || openPanel === 'checks' || openPanel === 'companion' ? 'w-200' : 'w-96'
							}`}>
							<div className="flex items-center justify-between mb-6">
								<h2 className="font-display text-xl text-white">
									{openPanel === 'stats' && '⚔️ Character Stats'}
									{openPanel === 'inventory' && '🎒 Inventory'}
									{openPanel === 'dice' && '🎲 Dice Roller'}
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
								</div>
							)}

							{/* Inventory Panel */}
							{openPanel === 'inventory' && (
								<div className="bg-neutral-900 rounded-lg">
									<InventoryPanel characterId={characterId} />
								</div>
							)}

							{/* Spells Panel */}
							{openPanel === 'spells' && (
								<div className="space-y-4 bg-neutral-900 rounded-lg p-4">
									<SpellsPanel characterId={characterId} />
								</div>
							)}

							{/* Ability Checks Panel */}
							{openPanel === 'checks' && (
								<div className="bg-neutral-900 rounded-lg">
									<AbilityCheckPanel
										characterId={characterId}
										onRollComplete={handleRollComplete}
										requestedDc={pendingRollRequest?.dc}
										requestedSkill={pendingRollRequest?.skill}
										requestedAbility={pendingRollRequest?.ability}
									/>
								</div>
							)}

							{/* Companion Panel */}
							{openPanel === 'companion' && character && (
								<div className="bg-neutral-900 rounded-lg">
									<CompanionListPanel
										characterId={characterId}
										onCompanionToggle={(companionId, isActive) => {
											console.log(`Companion ${companionId} ${isActive ? 'activated' : 'deactivated'}`);
										}}
										onCompanionCountChange={setCompanionCount}
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
								<div className="space-y-6">
									<div className="space-y-3">
										<label className="text-sm text-accent-200 font-body font-semibold">{t('game.diceRoller.notation')}</label>
										<Input
											value={diceNotation}
											onChange={(e) => setDiceNotation(e.target.value)}
											placeholder={t('game.diceRoller.placeholder')}
											className="bg-accent-200/10 border-accent-600/30 text-accent-200 font-mono placeholder:text-accent-200/40 focus:border-accent-600"
										/>
									</div>

									<div className="space-y-2">
										<p className="text-xs text-accent-200/70 font-body">Quick Roll:</p>
										<div className="grid grid-cols-3 gap-2">
											{['1d4', '1d6', '1d8', '1d10', '1d12', '1d20'].map((notation) => (
												<Button
													key={notation}
													variant="outline"
													onClick={() => {
														setDiceNotation(notation);
														setLastDiceResult(null);
													}}
													className="font-mono font-bold border-accent-600/30 bg-accent-200/5 text-accent-200 hover:bg-accent-600/20 hover:border-accent-600 hover:text-accent-200 transition-all"
												>
													🎲 {notation}
												</Button>
											))}
										</div>
									</div>

									<Button
										onClick={rollDice}
										className="w-full font-body bg-accent-600 hover:bg-accent-400 text-primary-900 font-semibold shadow-lg"
										size="lg"
									>
										🎲 {t('game.diceRoller.rollDice')}
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
															{t('game.diceRoller.rolls')} {lastDiceResult.individual_rolls.map((r: any) => r.roll).join(', ')}
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
		</div>
	);
}
